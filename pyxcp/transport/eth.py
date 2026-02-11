#!/usr/bin/env python
import selectors
import socket
import struct
import threading
from collections import deque
from typing import Optional

from pyxcp.cpp_ext.cpp_ext import enable_ptp_timestamping, init_networking, receive_with_timestamp, check_timestamping_support
from pyxcp.transport.transport_ext import EthReceiver

from pyxcp.transport.base import (
    BaseTransport,
    ChecksumType,
    XcpFramingConfig,
    XcpTransportLayerType,
)
from pyxcp.utils import short_sleep

DEFAULT_XCP_PORT = 5555
RECV_SIZE = 8196


def socket_to_str(sock: socket.socket) -> str:
    peer = sock.getpeername()
    local = sock.getsockname()
    AF = {
        socket.AF_INET: "AF_INET",
        socket.AF_INET6: "AF_INET6",
    }
    TYPE = {
        socket.SOCK_DGRAM: "SOCK_DGRAM",
        socket.SOCK_STREAM: "SOCK_STREAM",
    }
    family = AF.get(sock.family, "OTHER")
    typ = TYPE.get(sock.type, "UNKNOWN")
    res = f"XCPonEth - Connected to: {peer[0]}:{peer[1]}  local address: {local[0]}:{local[1]} [{family}][{typ}]"
    return res


class Eth(BaseTransport):
    """"""

    MAX_DATAGRAM_SIZE = 512
    HEADER = struct.Struct("<HH")

    def __init__(self, config=None, policy=None, transport_layer_interface: Optional[socket.socket] = None) -> None:
        self.load_config(config)
        framing_config = XcpFramingConfig(
            transport_layer_type=XcpTransportLayerType.ETH,
            header_len=2,
            header_ctr=2,
            header_fill=0,
            tail_fill=False,
            tail_cs=ChecksumType.NO_CHECKSUM,
        )
        super().__init__(config, framing_config, policy, transport_layer_interface)
        self.host: str = self.config.host
        self.port: int = self.config.port
        self.protocol: int = self.config.protocol
        self.ipv6: bool = self.config.ipv6
        self.use_tcp_no_delay: bool = self.config.tcp_nodelay
        address_to_bind: str = self.config.bind_to_address
        bind_to_port: int = self.config.bind_to_port
        self._local_address = (address_to_bind, bind_to_port) if address_to_bind else None
        if self.ipv6 and not socket.has_ipv6:
            msg = "XCPonEth - IPv6 not supported by your platform."
            self.logger.critical(msg)
            raise RuntimeError(msg)
        else:
            address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET
        proto = socket.SOCK_STREAM if self.protocol == "TCP" else socket.SOCK_DGRAM
        if self.host.lower() == "localhost":
            self.host = "::1" if self.ipv6 else "localhost"

        try:
            addrinfo = socket.getaddrinfo(self.host, self.port, address_family, proto)
            (
                self.address_family,
                self.socktype,
                self.proto,
                self.canonname,
                self.sockaddr,
            ) = addrinfo[0]
        except BaseException as ex:  # noqa: B036
            msg = f"XCPonEth - Failed to resolve address {self.host}:{self.port} ({self.protocol}, ipv6={self.ipv6}): {ex.__class__.__name__}: {ex}"
            self.logger.critical(msg, extra={"transport": "eth", "host": self.host, "port": self.port, "protocol": self.protocol})
            raise Exception(msg) from ex
        self.status: int = 0
        self.sock = socket.socket(self.address_family, self.socktype, self.proto)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ)
        self.use_tcp = self.protocol == "TCP"
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        init_networking()
        self.ptp_enabled = False
        if self.config.ptp_timestamping:
            if self.use_tcp:
                self.logger.warning("PTP hardware timestamping is typically not supported for TCP. Only UDP will be attempted.")
            else:
                self._setup_ptp()

        if self.use_tcp and self.use_tcp_no_delay:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)
        if self._local_address:
            try:
                self.sock.bind(self._local_address)
            except BaseException as ex:  # noqa: B036
                msg = f"XCPonEth - Failed to bind socket to given address {self._local_address}: {ex.__class__.__name__}: {ex}"
                self.logger.critical(
                    msg, extra={"transport": "eth", "host": self.host, "port": self.port, "protocol": self.protocol}
                )
                raise Exception(msg) from ex
        self._packet_listener = threading.Thread(
            target=self._packet_listen,
            args=(),
            kwargs={},
            daemon=True,
        )
        self._packets = deque()
        self._eth_receiver = EthReceiver(self.process_response)

    def connect(self) -> None:
        if self.status == 0:
            self.sock.connect(self.sockaddr)
            self.logger.info(socket_to_str(self.sock))
            self.start_listener()
            self.status = 1  # connected

    def start_listener(self) -> None:
        super().start_listener()
        if self._packet_listener.is_alive():
            self._packet_listener.join(timeout=2.0)
        self._packet_listener = threading.Thread(target=self._packet_listen, daemon=True)
        self._packet_listener.start()

    def close(self) -> None:
        """Close the transport-layer connection and event-loop."""
        self.finish_listener()
        try:
            if self.listener.is_alive():
                self.listener.join(timeout=2.0)
        except Exception:
            pass
        try:
            if self._packet_listener.is_alive():
                self._packet_listener.join(timeout=2.0)
        except Exception:
            pass
        self.close_connection()

    def _packet_listen(self) -> None:
        use_tcp: bool = self.use_tcp
        EVENT_READ = selectors.EVENT_READ
        close_event_set = self.closeEvent.is_set
        socket_fileno = self.sock.fileno
        select = self.selector.select
        _packets = self._packets
        ptp_enabled = self.ptp_enabled

        if use_tcp:
            sock_recv = self.sock.recv
        else:
            if ptp_enabled:
                if hasattr(socket, "SO_TIMESTAMPING"):  # Linux
                    sock_recvmsg = self.sock.recvmsg
                else:
                    # Windows uses C++ helper
                    def win_recv_with_ts(size):
                        return receive_with_timestamp(socket_fileno(), size)
            else:
                sock_recv = self.sock.recvfrom

        while True:
            try:
                if close_event_set() or socket_fileno() == -1:
                    return
                sel = select(0.02)
                for _, events in sel:
                    if events & EVENT_READ:
                        if use_tcp:
                            recv_timestamp = self.timestamp.value
                            response = sock_recv(RECV_SIZE)
                            if not response:
                                self.sock.close()
                                self.status = 0
                                break
                            else:
                                _packets.append((bytes(response), recv_timestamp))
                        else:
                            if ptp_enabled:
                                if hasattr(socket, "SO_TIMESTAMPING"):  # Linux
                                    # 32 is a guess for ancdata size, might need adjustment
                                    response, ancdata, flags, address = sock_recvmsg(Eth.MAX_DATAGRAM_SIZE, 1024)
                                    recv_timestamp = self._extract_linux_timestamp(ancdata) or self.timestamp.value
                                else:  # Windows
                                    res = win_recv_with_ts(Eth.MAX_DATAGRAM_SIZE)
                                    if res:
                                        response, recv_timestamp = res
                                    else:
                                        # Fallback if helper fails
                                        response, _ = self.sock.recvfrom(Eth.MAX_DATAGRAM_SIZE)
                                        recv_timestamp = self.timestamp.value

                                if not response:
                                    self.sock.close()
                                    self.status = 0
                                    break
                                else:
                                    _packets.append((bytes(response), recv_timestamp))
                            else:
                                recv_timestamp = self.timestamp.value
                                response, _ = self.sock.recvfrom(Eth.MAX_DATAGRAM_SIZE)
                                if not response:
                                    self.sock.close()
                                    self.status = 0
                                    break
                                else:
                                    _packets.append((bytes(response), recv_timestamp))
            except BaseException:  # noqa: B036
                self.status = 0  # disconnected
                break

    def _extract_linux_timestamp(self, ancdata) -> Optional[int]:
        # SO_TIMESTAMPING returns a struct scm_timestamping
        # which contains 3 timespecs: software, transformed, hardware.
        # We want the hardware one (index 2) if available, otherwise software (index 0).
        for cmsg_level, cmsg_type, cmsg_data in ancdata:
            if cmsg_level == socket.SOL_SOCKET and cmsg_type == socket.SO_TIMESTAMPING:
                # struct timespec { long tv_sec; long tv_nsec; } x 3
                # On 64-bit Linux, long is 8 bytes.
                # Format: 3 * (qq)
                if len(cmsg_data) >= 48:
                    ts = struct.unpack("qqqqqq", cmsg_data)
                    # Try hardware first (ts[4], ts[5])
                    if ts[4] != 0:
                        return ts[4] * 1_000_000_000 + ts[5]
                    # Fallback to software (ts[0], ts[1])
                    return ts[0] * 1_000_000_000 + ts[1]
        return None

    def listen(self) -> None:
        popleft = self._packets.popleft
        close_event_set = self.closeEvent.is_set
        socket_fileno = self.sock.fileno
        _packets = self._packets
        feed_frame = self._eth_receiver.feed_frame

        while True:
            if close_event_set() or socket_fileno() == -1:
                return
            count: int = len(_packets)
            if not count:
                short_sleep()
                continue
            for _ in range(count):
                bts, timestamp = popleft()
                feed_frame(bts, timestamp)

    def send(self, frame) -> None:
        self.pre_send_timestamp = self.timestamp.value
        self.sock.send(frame)
        self.post_send_timestamp = self.timestamp.value

    def close_connection(self) -> None:
        if not self.invalidSocket:
            # Seems to be problematic /w IPv6
            # if self.status == 1:
            #     self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

    @property
    def invalidSocket(self) -> bool:
        return not hasattr(self, "sock") or self.sock.fileno() == -1

    def _setup_ptp(self) -> None:
        ts_info = check_timestamping_support(self.host)
        if ts_info.timestamping_supported:
            self.logger.info(f"Hardware timestamping is supported on interface {ts_info.interface_name!r}")
            if enable_ptp_timestamping(self.sock.fileno()):
                self.ptp_enabled = True
                self.logger.info("PTP hardware timestamping enabled")
            else:
                self.logger.error("Failed to enable PTP hardware timestamping")
        else:
            self.logger.info(f"Hardware timestamping NOT supported on interface {ts_info.interface_name!r}")

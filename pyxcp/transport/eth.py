#!/usr/bin/env python
import selectors
import socket
import struct
import threading
from collections import deque
from typing import Optional

from pyxcp.transport.base import BaseTransport
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
    HEADER_SIZE = HEADER.size

    def __init__(self, config=None, policy=None, transport_layer_interface: Optional[socket.socket] = None) -> None:
        super().__init__(config, policy, transport_layer_interface)
        self.load_config(config)
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
            msg = f"XCPonEth - Failed to resolve address {self.host}:{self.port}"
            self.logger.critical(msg)
            raise Exception(msg) from ex
        self.status: int = 0
        self.sock = socket.socket(self.address_family, self.socktype, self.proto)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ)
        self.use_tcp = self.protocol == "TCP"
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self.use_tcp and self.use_tcp_no_delay:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)
        if self._local_address:
            try:
                self.sock.bind(self._local_address)
            except BaseException as ex:  # noqa: B036
                msg = f"XCPonEth - Failed to bind socket to given address {self._local_address}"
                self.logger.critical(msg)
                raise Exception(msg) from ex
        self._packet_listener = threading.Thread(
            target=self._packet_listen,
            args=(),
            kwargs={},
        )
        self._packets = deque()

    def connect(self) -> None:
        if self.status == 0:
            self.sock.connect(self.sockaddr)
            self.logger.info(socket_to_str(self.sock))
            self.start_listener()
            self.status = 1  # connected

    def start_listener(self) -> None:
        super().start_listener()
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self._packet_listener = threading.Thread(target=self._packet_listen)
        self._packet_listener.start()

    def close(self) -> None:
        """Close the transport-layer connection and event-loop."""
        self.finish_listener()
        if self.listener.is_alive():
            self.listener.join()
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self.close_connection()

    def _packet_listen(self) -> None:
        use_tcp: bool = self.use_tcp
        EVENT_READ = selectors.EVENT_READ
        close_event_set = self.closeEvent.is_set
        socket_fileno = self.sock.fileno
        select = self.selector.select
        _packets = self._packets
        if use_tcp:
            sock_recv = self.sock.recv
        else:
            sock_recv = self.sock.recvfrom
        while True:
            try:
                if close_event_set() or socket_fileno() == -1:
                    return
                sel = select(0.02)
                for _, events in sel:
                    if events & EVENT_READ:
                        recv_timestamp = self.timestamp.value
                        if use_tcp:
                            response = sock_recv(RECV_SIZE)
                            if not response:
                                self.sock.close()
                                self.status = 0
                                break
                            else:
                                _packets.append((response, recv_timestamp))
                        else:
                            response, _ = sock_recv(Eth.MAX_DATAGRAM_SIZE)
                            if not response:
                                self.sock.close()
                                self.status = 0
                                break
                            else:
                                _packets.append((response, recv_timestamp))
            except BaseException:  # noqa: B036
                self.status = 0  # disconnected
                break

    def listen(self) -> None:
        """Process packets received from the network.

        This method runs in a separate thread and continuously processes packets
        that have been received by the _packet_listen method and added to the
        _packets deque. It extracts XCP messages from the raw data by:

        1. Unpacking the header to get the length and counter
        2. Extracting the payload based on the length
        3. Passing the payload to process_response

        The method handles partial messages that may be split across multiple
        network packets, and processes multiple messages that may be contained
        in a single network packet.
        """
        # Cache frequently used methods and attributes for better performance
        HEADER_UNPACK_FROM = self.HEADER.unpack_from
        HEADER_SIZE = self.HEADER_SIZE
        process_response = self.process_response
        popleft = self._packets.popleft
        close_event_set = self.closeEvent.is_set
        socket_fileno = self.sock.fileno
        _packets = self._packets

        # State variables for processing messages
        length: Optional[int] = None  # Length of the current message payload
        counter: int = 0  # Counter value from the current message header
        data: bytearray = bytearray(b"")  # Buffer for accumulated data
        last_sleep: int = self.timestamp.value  # Timestamp of last sleep
        FIVE_MS = 5_000_000  # Five milliseconds in nanoseconds

        while True:
            # Check if we should exit the loop
            if close_event_set() or socket_fileno() == -1:
                return

            # Periodically sleep to prevent CPU hogging
            if self.timestamp.value - last_sleep >= FIVE_MS:
                short_sleep()
                last_sleep = self.timestamp.value

            # Check if there are packets to process
            count: int = len(_packets)
            if not count:
                short_sleep()
                last_sleep = self.timestamp.value
                continue

            try:
                # Process all packets currently in the queue
                for _ in range(count):
                    bts, timestamp = popleft()
                    data += bts
                    current_size: int = len(data)
                    current_position: int = 0

                    # Process all complete messages in the current data
                    while True:
                        # If we don't have a length yet, try to extract the header
                        if length is None:
                            if current_size >= HEADER_SIZE:
                                # Extract length and counter from header
                                length, counter = HEADER_UNPACK_FROM(data, current_position)
                                current_position += HEADER_SIZE
                                current_size -= HEADER_SIZE
                            else:
                                # Not enough data for a header, keep the remaining data
                                data = data[current_position:]
                                break
                        else:
                            # We have a length, check if we have enough data for the payload
                            if current_size >= length:
                                # Extract and process the payload
                                response = data[current_position : current_position + length]
                                process_response(response, length, counter, timestamp)
                                current_size -= length
                                current_position += length
                                length = None  # Reset length for the next message
                            else:
                                # Not enough data for the payload, keep the remaining data
                                data = data[current_position:]
                                break
            except Exception as e:
                # Log any exceptions but continue processing
                self.logger.error(f"Error in listen thread: {e}")
                # Reset state to avoid getting stuck
                length = None
                data = bytearray(b"")

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

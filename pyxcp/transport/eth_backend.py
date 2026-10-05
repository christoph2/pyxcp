#!/usr/bin/env python
"""Low-level I/O backends for the :class:`pyxcp.transport.eth.Eth` transport.

``Eth`` is responsible for XCP-level concerns (framing config, address
resolution parameters, multicast, timing) while the actual byte-level
network I/O (connect / send / receive-loop) is delegated to an
:class:`EthIoBackend` implementation selected via configuration
(``Eth.experimental_backend``).

:class:`EthIoBackend` itself is the abstract C++ interface exposed by
``pyxcp.transport.transport_ext`` (``eth_io_backend.hpp``); backends can be
written in Python (subclassing it) or natively in C++. It provides the
``eth``, ``logger`` and ``sock`` attributes and ``available = True``.
Abstract methods that are not overridden raise on call.

This indirection exists so that the proven, selectors-based implementation
(:class:`LegacySocketBackend`) can keep running unchanged in production while
an experimental, higher-performance backend (e.g. an IOCP-based
implementation on Windows) can be developed and swapped in without touching
``Eth``, ``BaseTransport`` or the C++ XCP framing/dispatch logic
(``EthReceiver.feed_frame``), which is shared by every backend.
"""

import selectors
import socket
import struct
from collections import deque
from typing import TYPE_CHECKING

from pyxcp.cpp_ext.cpp_ext import check_timestamping_support, enable_ptp_timestamping, receive_with_timestamp
from pyxcp.transport.transport_ext import EthIoBackend, EthProtocol, EthConfig

if TYPE_CHECKING:
    from pyxcp.transport.eth import Eth

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


class LegacySocketBackend(EthIoBackend):
    """Proven, ``selectors``-based Ethernet I/O backend (the default).

    This is a 1:1 move of the implementation that used to live directly in
    :class:`pyxcp.transport.eth.Eth`; behavior is unchanged.
    """

    def __init__(self, eth: "Eth") -> None:
        super().__init__(eth)
        self.selector: selectors.BaseSelector | None = None
        self.ptp_enabled: bool = False
        self._status: int = 0
        self._packet_listener = None
        self._packets: deque = deque()
        self._packets_condition = None

    def setup(self, eth_config: EthConfig) -> None:
        import threading

        self.eth_config = eth_config
        eth = self.eth
        if eth_config.ipv6 and not socket.has_ipv6:
            msg = "XCPonEth - IPv6 not supported by your platform."
            self.logger.critical(msg)
            raise RuntimeError(msg)
        address_family = socket.AF_INET6 if eth_config.ipv6 else socket.AF_INET
        proto = socket.SOCK_STREAM if eth_config.protocol == EthProtocol.TCP else socket.SOCK_DGRAM
        if eth_config.host.lower() == "localhost":
            eth_config.host = "::1" if eth_config.ipv6 else "localhost"
        try:
            addrinfo = socket.getaddrinfo(eth_config.host, eth_config.port, address_family, proto)
            (
                eth.address_family,
                eth.socktype,
                eth.proto,
                eth.canonname,
                eth.sockaddr,
            ) = addrinfo[0]
        except BaseException as ex:  # noqa: B036
            msg = (
                f"XCPonEth - Failed to resolve address {eth_config.host}:{eth_config.port} "
                f"({eth_config.protocol}, ipv6={eth_config.ipv6}): {ex.__class__.__name__}: {ex}"
            )
            self.logger.critical(
                msg, extra={"transport": "eth", "host": eth_config.host, "port": eth_config.port, "protocol": eth_config.protocol}
            )
            raise Exception(msg) from ex

        self._status = 0
        self.sock = socket.socket(eth.address_family, eth.socktype, eth.proto)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ)
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.ptp_enabled = False
        if eth.config.ptp_timestamping:
            if eth_config.protocol == EthProtocol.TCP:
                self.logger.warning("PTP hardware timestamping is typically not supported for TCP. Only UDP will be attempted.")
            else:
                self._setup_ptp()
        if eth_config.protocol == EthProtocol.TCP and eth.use_tcp_no_delay:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)
        if eth_config.bind_to:
            try:
                self.sock.bind(eth_config.bind_to)
            except BaseException as ex:  # noqa: B036
                msg = f"XCPonEth - Failed to bind socket to given address {eth_config.bind_to}: {ex.__class__.__name__}: {ex}"
                self.logger.critical(
                    msg,
                    extra={"transport": "eth", "host": eth_config.host, "port": eth_config.port, "protocol": eth_config.protocol},
                )
                raise Exception(msg) from ex

        self._packet_listener = threading.Thread(
            target=self._packet_listen,
            args=(),
            kwargs={},
            daemon=True,
        )
        self._packets = deque()
        self._packets_condition = threading.Condition()

    def connect(self) -> None:
        if self._status == 0:
            self.sock.connect(self.eth.sockaddr)
            self.logger.info(socket_to_str(self.sock))
            self._status = 1  # connected

    def start_listening(self) -> None:
        import threading

        if self._packet_listener is not None and self._packet_listener.is_alive():
            self._packet_listener.join(timeout=2.0)
        self._packet_listener = threading.Thread(target=self._packet_listen, daemon=True)
        self._packet_listener.start()

    def stop_listening(self) -> None:
        try:
            if self._packet_listener is not None and self._packet_listener.is_alive():
                self._packet_listener.join(timeout=2.0)
        except (RuntimeError, AttributeError):
            # RuntimeError: thread not started yet or already stopped
            # AttributeError: _packet_listener object not initialized
            pass

    def _packet_listen(self) -> None:
        eth = self.eth
        use_tcp: bool = self.eth_config.use_tcp
        EVENT_READ = selectors.EVENT_READ
        close_event_set = eth.closeEvent.is_set
        socket_fileno = self.sock.fileno
        select = self.selector.select
        _packets = self._packets
        _packets_condition = self._packets_condition
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
                            recv_timestamp = eth.timestamp.value
                            response = sock_recv(RECV_SIZE)
                            if not response:
                                self.sock.close()
                                self._status = 0
                                break
                            else:
                                with _packets_condition:
                                    _packets.append((bytes(response), recv_timestamp))
                                    _packets_condition.notify()
                        else:
                            if ptp_enabled:
                                if hasattr(socket, "SO_TIMESTAMPING"):  # Linux
                                    # 32 is a guess for ancdata size, might need adjustment
                                    response, ancdata, flags, address = sock_recvmsg(eth.MAX_DATAGRAM_SIZE, 1024)
                                    recv_timestamp = self._extract_linux_timestamp(ancdata) or eth.timestamp.value
                                else:  # Windows
                                    res = win_recv_with_ts(eth.MAX_DATAGRAM_SIZE)
                                    if res:
                                        response, recv_timestamp = res
                                    else:
                                        # Fallback if helper fails
                                        response, _ = self.sock.recvfrom(eth.MAX_DATAGRAM_SIZE)
                                        recv_timestamp = eth.timestamp.value

                                if not response:
                                    self.sock.close()
                                    self._status = 0
                                    break
                                else:
                                    with _packets_condition:
                                        _packets.append((bytes(response), recv_timestamp))
                                        _packets_condition.notify()
                            else:
                                recv_timestamp = eth.timestamp.value
                                response, _ = self.sock.recvfrom(eth.MAX_DATAGRAM_SIZE)
                                if not response:
                                    self.sock.close()
                                    self._status = 0
                                    break
                                else:
                                    with _packets_condition:
                                        _packets.append((bytes(response), recv_timestamp))
                                        _packets_condition.notify()
            except (OSError, ValueError) as ex:
                self._status = 0  # disconnected
                if close_event_set() or socket_fileno() == -1:
                    self.logger.debug("Ethernet packet listener stopped during socket shutdown: %s", ex)
                    break
                else:
                    self.logger.exception("Ethernet packet listener socket failure")
                    continue
            except Exception:
                self._status = 0  # disconnected
                self.logger.exception("Unexpected Ethernet packet listener failure")
                break

    def _extract_linux_timestamp(self, ancdata) -> int | None:
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
        """Drain packets picked up by the raw-recv thread and feed the shared
        XCP framing/dispatch logic. Runs on the generic ``BaseTransport``
        listener thread (invoked via ``Eth.listen()``)."""
        eth = self.eth
        popleft = self._packets.popleft
        close_event_set = eth.closeEvent.is_set
        socket_fileno = self.sock.fileno
        _packets = self._packets
        _packets_condition = self._packets_condition
        feed_frame = eth._eth_receiver.feed_frame

        while True:
            if close_event_set() or socket_fileno() == -1:
                return

            with _packets_condition:
                # Wait for packets to be available
                while not _packets:
                    if close_event_set() or socket_fileno() == -1:
                        return
                    # Wait with timeout to periodically check close event
                    _packets_condition.wait(timeout=0.1)

                # Process all available packets
                count = len(_packets)
                for _ in range(count):
                    bts, timestamp = popleft()
                    feed_frame(bts, timestamp)

    def send(self, frame: bytes) -> None:
        self.sock.send(frame)

    def close_connection(self) -> None:
        if not self.invalid_socket:
            # Seems to be problematic /w IPv6
            # if self._status == 1:
            #     self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

    @property
    def status(self) -> int:
        return self._status

    @status.setter
    def status(self, value: int) -> None:
        self._status = value

    @property
    def invalid_socket(self) -> bool:
        return self.sock is None or self.sock.fileno() == -1

    def _setup_ptp(self) -> None:
        ts_info = check_timestamping_support(self.eth_config.host)
        if ts_info.timestamping_supported:
            self.logger.info(f"Hardware timestamping is supported on interface {ts_info.interface_name!r}")
            if enable_ptp_timestamping(self.sock.fileno()):
                self.ptp_enabled = True
                self.logger.info("PTP hardware timestamping enabled")
            else:
                self.logger.error("Failed to enable PTP hardware timestamping")
        else:
            self.logger.info(f"Hardware timestamping NOT supported on interface {ts_info.interface_name!r}")


class _UnavailableIocpBackend(EthIoBackend):
    """Stand-in used where the compiled IOCP backend (``pyxcp.transport.eth_ext``) cannot be
    imported, i.e. on non-Windows platforms or when the extension was not built."""

    available = False


try:
    from pyxcp.transport.eth_ext import IocpBackend as IocpSocketBackend  # Windows only (C++/IOCP).
except ImportError:
    IocpSocketBackend = _UnavailableIocpBackend

#: Registry of known Ethernet I/O backends, keyed by the name used in
#: ``Eth.experimental_backend``-driven selection (see ``create_eth_backend``).
_ETH_BACKENDS: dict[str, type[EthIoBackend]] = {
    "legacy": LegacySocketBackend,
    "iocp": IocpSocketBackend,
}


def create_eth_backend(name: str, eth: "Eth") -> EthIoBackend:
    """Factory for :class:`EthIoBackend` implementations.

    Parameters
    ----------
    name: str
        ``"legacy"`` (default, proven ``selectors``-based implementation) or
        ``"iocp"`` (experimental, native I/O completion port backend; Windows only).
    eth: :class:`pyxcp.transport.eth.Eth`
        The owning transport instance.

    Raises
    ------
    ValueError
        If ``name`` is not a known backend.
    RuntimeError
        If the requested backend is known but not (yet) available/functional
        on this platform/build.
    """
    key = name.lower()
    if key not in _ETH_BACKENDS:
        raise ValueError(f"{name!r} is an invalid Ethernet backend -- please choose one of [{' | '.join(_ETH_BACKENDS.keys())}].")
    backend_class = _ETH_BACKENDS[key]
    if not backend_class.available:
        raise RuntimeError(
            f"The {name!r} Ethernet backend is not available yet. "
            "It requires Windows and the compiled ``pyxcp.transport.eth_ext`` extension. "
            "Set `c.Eth.experimental_backend = False` to use the proven, selectors-based backend."
        )
    return backend_class(eth)

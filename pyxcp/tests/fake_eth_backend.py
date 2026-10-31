"""Pure-Python, ``selectors``-based Ethernet backend used by the unit tests.

The production transport only uses the native backends (IOCP/epoll/kqueue). This
test double speaks to (mocked) Python sockets, so that the XCP/transport logic can be
tested without real network I/O.
"""

import selectors
import socket
import threading
from collections import deque

from pyxcp.transport.transport_ext import EthConfig, EthIoBackend, EthProtocol

RECV_SIZE = 8196


class FakeSocketBackend(EthIoBackend):
    def __init__(self, eth) -> None:
        super().__init__(eth)
        self.selector = None
        self._status = 0
        self._packet_listener = None
        self._packets: deque = deque()
        self._packets_condition = None

    def setup(self, eth_config: EthConfig) -> None:
        self.eth_config = eth_config
        eth = self.eth
        address_family = socket.AF_INET6 if eth_config.ipv6 else socket.AF_INET
        proto = socket.SOCK_STREAM if eth_config.protocol == EthProtocol.TCP else socket.SOCK_DGRAM
        if eth_config.host.lower() == "localhost":
            eth_config.host = "::1" if eth_config.ipv6 else "localhost"
        addrinfo = socket.getaddrinfo(eth_config.host, eth_config.port, address_family, proto)
        (eth.address_family, eth.socktype, eth.proto, eth.canonname, eth.sockaddr) = addrinfo[0]
        self._status = 0
        self.sock = socket.socket(eth.address_family, eth.socktype, eth.proto)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ)
        self.sock.settimeout(0.5)
        if eth_config.bind_to:
            self.sock.bind(eth_config.bind_to)
        self._packets = deque()
        self._packets_condition = threading.Condition()

    def connect(self) -> None:
        if self._status == 0:
            self.sock.connect(self.eth.sockaddr)
            self._status = 1

    def start_listening(self) -> None:
        if self._packet_listener is not None and self._packet_listener.is_alive():
            self._packet_listener.join(timeout=2.0)
        self._packet_listener = threading.Thread(target=self._packet_listen, daemon=True)
        self._packet_listener.start()

    def stop_listening(self) -> None:
        if self._packet_listener is not None and self._packet_listener.is_alive():
            self._packet_listener.join(timeout=2.0)

    def _packet_listen(self) -> None:
        eth = self.eth
        use_tcp = self.eth_config.use_tcp
        while True:
            try:
                if eth.closeEvent.is_set() or self.sock.fileno() == -1:
                    return
                for _, events in self.selector.select(0.02):
                    if not events & selectors.EVENT_READ:
                        continue
                    recv_timestamp = eth.timestamp.value
                    if use_tcp:
                        response = self.sock.recv(RECV_SIZE)
                    else:
                        response, _ = self.sock.recvfrom(eth.MAX_DATAGRAM_SIZE)
                    if not response:
                        self.sock.close()
                        self._status = 0
                        break
                    with self._packets_condition:
                        self._packets.append((bytes(response), recv_timestamp))
                        self._packets_condition.notify()
            except (OSError, ValueError):
                self._status = 0
                if eth.closeEvent.is_set() or self.sock.fileno() == -1:
                    break
            except Exception:
                self._status = 0
                break

    def listen(self) -> None:
        eth = self.eth
        packets = self._packets
        condition = self._packets_condition
        feed_frame = eth._eth_receiver.feed_frame
        while True:
            if eth.closeEvent.is_set() or self.sock.fileno() == -1:
                return
            with condition:
                while not packets:
                    if eth.closeEvent.is_set() or self.sock.fileno() == -1:
                        return
                    condition.wait(timeout=0.1)
                for _ in range(len(packets)):
                    bts, timestamp = packets.popleft()
                    feed_frame(bts, timestamp)

    def send(self, frame: bytes) -> None:
        self.sock.send(frame)

    def close_connection(self) -> None:
        if not self.invalid_socket:
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

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import selectors
import socket
import struct
import threading
from collections import deque
from time import perf_counter
from time import sleep
from time import time

from pyxcp.transport.base import BaseTransport
from pyxcp.utils import SHORT_SLEEP

DEFAULT_XCP_PORT = 5555
RECV_SIZE = 8196


class Eth(BaseTransport):
    """"""

    PARAMETER_MAP = {
        #                  Type    Req'd   Default
        "HOST": (str, False, "localhost"),
        "PORT": (int, False, 5555),
        "BIND_TO_ADDRESS": (str, False, ""),
        "BIND_TO_PORT": (int, False, 5555),
        "PROTOCOL": (str, False, "TCP"),
        "IPV6": (bool, False, False),
        "TCP_NODELAY": (bool, False, False),
    }

    MAX_DATAGRAM_SIZE = 512
    HEADER = struct.Struct("<HH")
    HEADER_SIZE = HEADER.size

    def __init__(self, config=None, policy=None):
        super(Eth, self).__init__(config, policy)
        self.loadConfig(config)
        self.host = self.config.get("HOST")
        self.port = self.config.get("PORT")
        self.protocol = self.config.get("PROTOCOL")
        self.ipv6 = self.config.get("IPV6")
        self.use_tcp_no_delay = self.config.get("TCP_NODELAY")
        address_to_bind = self.config.get("BIND_TO_ADDRESS")
        port_to_bind = self.config.get("BIND_TO_PORT")
        self._local_address = (address_to_bind, port_to_bind) if address_to_bind else None
        if self.ipv6 and not socket.has_ipv6:
            raise RuntimeError("IPv6 not supported by your platform.")
        else:
            address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET
        proto = socket.SOCK_STREAM if self.protocol == "TCP" else socket.SOCK_DGRAM
        if self.host.lower() == "localhost":
            self.host = "::1" if self.ipv6 else "localhost"
        addrinfo = socket.getaddrinfo(self.host, self.port, address_family, proto)
        (
            self.address_family,
            self.socktype,
            self.proto,
            self.canonname,
            self.sockaddr,
        ) = addrinfo[0]
        self.status = 0
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
            except BaseException as ex:
                raise Exception(f"Failed to bind socket to given address {self._local_address}") from ex
        self._packet_listener = threading.Thread(
            target=self._packet_listen,
            args=(),
            kwargs={},
        )
        self._packets = deque()

    def connect(self):
        if self.status == 0:
            self.sock.connect(self.sockaddr)
            self.startListener()
            self.status = 1  # connected

    def startListener(self):
        super().startListener()
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self._packet_listener = threading.Thread(target=self._packet_listen)
        self._packet_listener.start()

    def close(self):
        """Close the transport-layer connection and event-loop."""
        self.finishListener()
        if self.listener.is_alive():
            self.listener.join()
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self.closeConnection()

    def _packet_listen(self):
        use_tcp = self.use_tcp
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
                        recv_timestamp = time()

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
            except BaseException:
                self.status = 0  # disconnected
                break

    def listen(self):
        HEADER_UNPACK_FROM = self.HEADER.unpack_from
        HEADER_SIZE = self.HEADER_SIZE
        processResponse = self.processResponse
        popleft = self._packets.popleft

        close_event_set = self.closeEvent.is_set
        socket_fileno = self.sock.fileno

        _packets = self._packets
        length, counter = None, None

        data = bytearray(b"")

        while True:
            if close_event_set() or socket_fileno() == -1:
                return

            count = len(_packets)

            if not count:
                sleep(SHORT_SLEEP)
                continue

            for _ in range(count):
                bts, timestamp = popleft()

                data += bts
                current_size = len(data)
                current_position = 0

                while True:
                    if length is None:
                        if current_size >= HEADER_SIZE:
                            length, counter = HEADER_UNPACK_FROM(data, current_position)
                            current_position += HEADER_SIZE
                            current_size -= HEADER_SIZE
                        else:
                            data = data[current_position:]
                            break
                    else:
                        if current_size >= length:
                            response = data[current_position : current_position + length]
                            processResponse(response, length, counter, timestamp)

                            current_size -= length
                            current_position += length

                            length = None

                        else:

                            data = data[current_position:]
                            break

    def send(self, frame):
        self.pre_send_timestamp = time()
        self.sock.send(frame)
        self.post_send_timestamp = time()

    def closeConnection(self):
        if not self.invalidSocket:
            # Seems to be problematic /w IPv6
            # if self.status == 1:
            #     self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

    @property
    def invalidSocket(self):
        return not hasattr(self, "sock") or self.sock.fileno() == -1

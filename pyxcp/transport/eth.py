#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2019 by Christoph Schueler <cpu12.gems@googlemail.com>

   All Rights Reserved

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

from collections import deque
import selectors
import socket
import struct
from time import perf_counter, time, sleep
import threading

from pyxcp.transport.base import BaseTransport
import pyxcp.types as types

DEFAULT_XCP_PORT = 5555
RECV_SIZE = 8196


class Eth(BaseTransport):
    """
    """

    PARAMETER_MAP = {
        #                  Type    Req'd   Default
        "HOST":           (str,    False,  "localhost"),
        "PORT":           (int,    False,  5555),
        "PROTOCOL":       (str,    False,  "TCP"),
        "IPV6":           (bool,   False,  False),
        "TCP_NODELAY":    (bool,   False,  False),
    }

    MAX_DATAGRAM_SIZE = 512
    HEADER = struct.Struct("<HH")
    HEADER_SIZE = HEADER.size

    def __init__(self, config=None):
        super(Eth, self).__init__(config)
        self.loadConfig(config)
        self.host = self.config.get("HOST")
        self.port = self.config.get("PORT")
        self.protocol = self.config.get("PROTOCOL")
        self.ipv6 = self.config.get("IPV6")
        self.use_tcp_no_delay = self.config.get("TCP_NODELAY")

        if self.ipv6 and not socket.has_ipv6:
            raise RuntimeError("IPv6 not supported by your platform.")
        else:
           address_family = socket.AF_INET6 if self.ipv6 else socket.AF_INET
        proto = socket.SOCK_STREAM if self.protocol == 'TCP' else socket.SOCK_DGRAM
        if self.host.lower() == "localhost":
            self.host = "::1" if self.ipv6 else "localhost"
        addrinfo = socket.getaddrinfo(self.host, self.port, address_family, proto)
        (self.address_family, self.socktype, self.proto, self.canonname, self.sockaddr) = addrinfo[0]
        self.status = 0
        self.sock = socket.socket(
            self.address_family,
            self.socktype,
            self.proto
        )
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ)
        self.use_tcp = (self.protocol == 'TCP')
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if self.use_tcp and self.use_tcp_no_delay:
            self.sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)

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
        self._packet_listener.start()
        self.listener.start()

    def _packet_listen(self):
        use_tcp = self.use_tcp
        EVENT_READ = selectors.EVENT_READ

        close_event_set = self.closeEvent.isSet
        socket_fileno = self.sock.fileno
        select = self.selector.select

        high_resolution_time = self.perf_counter_origin > 0
        timestamp_origin = self.timestamp_origin
        perf_counter_origin = self.perf_counter_origin

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
                        if high_resolution_time:
                            recv_timestamp = time()
                        else:
                            recv_timestamp = timestamp_origin + perf_counter() - perf_counter_origin

                        if use_tcp:
                            _packets.append((sock_recv(RECV_SIZE), recv_timestamp))
                        else:
                            response, _ = sock_recv(Eth.MAX_DATAGRAM_SIZE)
                            _packets.append((response, recv_timestamp))
            except:
                self.status = 0  # disconnected
                break

    def listen(self):
        HEADER_UNPACK_FROM = self.HEADER.unpack_from
        HEADER_SIZE = self.HEADER_SIZE
        processResponse = self.processResponse
        popleft = self._packets.popleft

        close_event_set = self.closeEvent.isSet
        socket_fileno = self.sock.fileno

        _packets = self._packets
        length, counter = None, None

        data = b''

        while True:
            if close_event_set() or socket_fileno() == -1:
                return

            count = len(_packets)

            if not count:
                sleep(0.002)
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
                            response = data[current_position: current_position + length]
                            processResponse(response, length, counter, timestamp)

                            current_size -= length
                            current_position += length

                            length = None

                        else:

                            data = data[current_position:]
                            break

    def send(self, frame):
        if self.perf_counter_origin > 0:
            self.pre_send_timestamp = time()
            self.sock.send(frame)
            self.post_send_timestamp = time()
        else:
            pre_send_timestamp = perf_counter()
            self.sock.send(frame)
            post_send_timestamp = perf_counter()
            self.pre_send_timestamp = self.timestamp_origin + pre_send_timestamp - self.perf_counter_origin
            self.post_send_timestamp = self.timestamp_origin + post_send_timestamp - self.perf_counter_origin

    def closeConnection(self):
        if not self.invalidSocket:
            # Seems to be problematic /w IPv6
            # if self.status == 1:
            #     self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

    @property
    def invalidSocket(self):
        return not hasattr(self, 'sock') or self.sock.fileno() == -1

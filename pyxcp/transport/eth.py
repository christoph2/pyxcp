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

import selectors
import socket
import struct
from time import perf_counter, time

from pyxcp.transport.base import BaseTransport
import pyxcp.types as types

DEFAULT_XCP_PORT = 5555


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

    def connect(self):
        if self.status == 0:
            self.sock.connect(self.sockaddr)
            self.startListener()
            self.status = 1  # connected

    def listen(self):
        HEADER_UNPACK = self.HEADER.unpack
        HEADER_SIZE = self.HEADER_SIZE
        use_tcp = self.use_tcp
        processResponse = self.processResponse
        EVENT_READ = selectors.EVENT_READ

        close_event_set = self.closeEvent.isSet
        socket_fileno = self.sock.fileno
        select = self.selector.select

        high_resolution_time = self.perf_counter_origin > 0
        timestamp_origin = self.timestamp_origin
        perf_counter_origin = self.perf_counter_origin

        if use_tcp:
            sock_recv = self.sock.recv
        else:
            sock_recv = self.sock.recvfrom

        while True:
            try:
                if close_event_set() or socket_fileno() == -1:
                    return
                sel = select(0.1)
                for _, events in sel:
                    if events & EVENT_READ:
                        if high_resolution_time:
                            recv_timestamp = time()
                        else:
                            recv_timestamp = timestamp_origin + perf_counter() - perf_counter_origin
                        if use_tcp:

                            # first try to get the header in one go
                            # if we are lucky this will avoid creating a
                            # bytearray and extending it
                            header = sock_recv(HEADER_SIZE)
                            size = len(header)
                            if size != HEADER_SIZE:

                                start = perf_counter()

                                header = bytearray(header)

                                while len(header) != HEADER_SIZE:
                                    header.extend(
                                        sock_recv(HEADER_SIZE - len(header))
                                    )
                                    if perf_counter() - start > 2:
                                        raise types.XcpTimeoutError("Eth frame header read timed out.") from None

                            length, counter = HEADER_UNPACK(header)

                            try:
                                # first try to get the response in one go
                                # similar to the header
                                response = sock_recv(length)
                                size = len(response)

                                if size != length:

                                    start = perf_counter()

                                    response = bytearray(response)
                                    while len(response) != length:
                                        response.extend(
                                            sock_recv(length - len(response))
                                        )

                                        if perf_counter() - start > 2:
                                            raise types.XcpTimeoutError("Eth frame payload read timed out.") from None

                            except Exception as e:
                                self.logger.error(str(e))
                                continue
                        else:
                            try:
                                response, _ = sock_recv(
                                    Eth.MAX_DATAGRAM_SIZE
                                )
                                length, counter = HEADER_UNPACK(
                                    response[:HEADER_SIZE]
                                )
                                response = response[HEADER_SIZE:]

                                if len(response) != length:
                                    raise types.FrameSizeError("Size mismatch.")

                            except Exception as e:
                                self.logger.error(str(e))
                                continue

                        processResponse(response, length, counter, recv_timestamp)
            except Exception:
                self.status = 0  # disconnected
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

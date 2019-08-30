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

from pyxcp.transport.base import BaseTransport

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

        if self.ipv6 and not socket.has_ipv6:
            raise RuntimeError("IPv6 not supported by your platform.")
        else:
            addressFamily = socket.AF_INET6 if self.ipv6 else socket.AF_INET
        self.sock = socket.socket(
            addressFamily,
            socket.SOCK_STREAM if self.protocol == 'TCP' else socket.SOCK_DGRAM
        )
        if self.host.lower() == "localhost":
            self.host = "::1" if self.ipv6 else "localhost"
        else:
            self.host = host
        self.status = 0
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ)
        self.use_tcp = (self.protocol == 'TCP')
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(socket, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)

    def connect(self):
        if self.status == 0:
            self.sock.connect((self.host, self.port))
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
                        if use_tcp:

                            # first try to get the header in one go
                            # if we are lucky this will avoid creating a
                            # bytearray and extending it
                            header = sock_recv(HEADER_SIZE)
                            size = len(header)
                            if size != HEADER_SIZE:

                                header = bytearray(header)

                                while len(header) != HEADER_SIZE:
                                    header.extend(
                                        sock_recv(HEADER_SIZE - len(header))
                                    )

                            length, counter = HEADER_UNPACK(header)

                            try:
                                # first try to get the response in one go
                                # similar to the header
                                response = sock_recv(length)
                                size = len(response)

                                if size != length:

                                    response = bytearray(response)
                                    while len(response) != length:
                                        response.extend(
                                            sock_recv(length - len(response))
                                        )

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
                            except Exception as e:
                                self.logger.error(str(e))
                                continue

                        processResponse(response, length, counter)
            except Exception:
                self.status = 0  # disconnected
                break

    def send(self, frame):
        self.sock.send(frame)

    def closeConnection(self):
        if not self.invalidSocket:
            # Seems to be problematic /w IPv6
            # if self.status == 1:
            #     self.sock.shutdown(socket.SHUT_RDWR)
            self.sock.close()

    @property
    def invalidSocket(self):
        return self.sock.fileno() == -1

#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__="""
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2018 by Christoph Schueler <cpu12.gems@googlemail.com>

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

from ..utils import hexDump
import pyxcp.types as types

from ..timing import Timing
from  pyxcp.transport.base import BaseTransport

DEFAULT_XCP_PORT = 5555


class Eth(BaseTransport):

    MAX_DATAGRAM_SIZE = 512
    HEADER = struct.Struct("<HH")
    HEADER_SIZE = HEADER.size

    def __init__(self, ipAddress, port = DEFAULT_XCP_PORT, config = {}, connected = True, loglevel = "WARN"):
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM if connected else socket.SOCK_DGRAM)
        self.selector = selectors.DefaultSelector()
        self.selector.register(self.sock, selectors.EVENT_READ)
        self.connected = connected
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(self.sock, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)
        self.sock.connect((ipAddress, port))
        super(Eth, self).__init__(config, loglevel)
        self.startListener()

    def listen(self):
        HEADER_UNPACK = self.HEADER.unpack
        HEADER_SIZE = self.HEADER_SIZE
        while True:
            if self.closeEvent.isSet() or self.sock.fileno() == -1:
                return
            sel = self.selector.select(0.1)
            for _, events in sel:
                if events & selectors.EVENT_READ:
                    if self.connected:
                        header = bytearray()

                        while len(header) < HEADER_SIZE:
                            new_bytes = self.sock.recv(HEADER_SIZE - len(header))
                            header.extend(new_bytes)

                        length, counter = HEADER_UNPACK(header)

                        try:
                            response = bytearray()
                            while len(response) < length:
                                new_bytes = self.sock.recv(length - len(response))
                                response.extend(new_bytes)

                        except Exception as e:
                            self.logger.error(str(e))
                            continue
                    else:
                        try:
                            response, server = self.sock.recvfrom(Eth.MAX_DATAGRAM_SIZE)
                            length, counter = HEADER_UNPACK(response)
                            response = response[HEADER_SIZE:]
                        except Exception as e:
                            self.logger.error(str(e))
                            continue
                    self.processResponse(response, length, counter)

    def send(self, frame):
        self.sock.send(frame)

    def closeConnection(self):
        self.sock.close()



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

import queue
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
    HEADER = "<HH"
    HEADER_SIZE = struct.calcsize(HEADER)

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

    def listen(self):
        while True:
            if self.closeEvent.isSet() or self.sock.fileno() == -1:
                return
            sel  = self.selector.select(0.1)
            for key, events in sel:
                if events & selectors.EVENT_READ:
                    if self.connected:
                        length = struct.unpack("<H", self.sock.recv(2))[0]
                        response = self.sock.recv(length + 2)
                    else:
                        response, server = self.sock.recvfrom(Eth.MAX_DATAGRAM_SIZE)
                    if len(response) < self.HEADER_SIZE:
                        raise types.FrameSizeError("Frame too short.")
                    self.logger.debug("<- {}\n".format(hexDump(response)))
                    packetLen, seqNo = struct.unpack(Eth.HEADER, response[ : 4])
                    xcpPDU = response[4 : ]
                    if len(xcpPDU) != packetLen:
                        raise types.FrameSizeError("Size mismatch.")
                    self.resQueue.put(xcpPDU)

    def send(self, frame):
        self.sock.send(frame)

    def closeConnection(self):
        self.sock.close()



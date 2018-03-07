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

import socket
import struct

from ..logger import Logger
from ..utils import hexDump
import pyxcp.types as types

from ..timing import Timing

DEFAULT_XCP_PORT = 5555


class Eth(object):

    MAX_DATAGRAM_SIZE = 512
    HEADER = "<HH"
    HEADER_SIZE = struct.calcsize(HEADER)

    def __init__(self, ipAddress, port = DEFAULT_XCP_PORT, connected = True, loglevel = "WARN"):
        self.parent = None
        #self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM if connected else socket.SOCK_DGRAM)
        self.logger = Logger("transport.Eth")
        self.logger.setLevel(loglevel)
        self.connected = connected
        self.counter = 0
        self._address = None
        self._addressExtension = None
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(self.sock, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)
        self.sock.connect((ipAddress, port))
        self.timing = Timing()

    def close(self):
        self.sock.close()

    def request(self, cmd, *data):
        self.logger.debug(cmd.name)
        header = struct.pack("<HH", len(data) + 1, self.counter)
        frame = header + bytearray([cmd, *data])
        self.logger.debug("-> {}".format(hexDump(frame)))
        self.timing.start()
        self.sock.send(frame)

        if self.connected:
            length = struct.unpack("<H", self.sock.recv(2))[0]
            response = self.sock.recv(length + 2)
        else:
            response, server = self.sock.recvfrom(Eth.MAX_DATAGRAM_SIZE)
        self.timing.stop()

        if len(response) < self.HEADER_SIZE:
            raise types.FrameSizeError("Frame too short.")
        self.logger.debug("<- {}\n".format(hexDump(response)))
        self.packetLen, self.seqNo = struct.unpack(Eth.HEADER, response[ : 4])
        self.xcpPDU = response[4 : ]
        if len(self.xcpPDU) != self.packetLen:
            raise types.FrameSizeError("Size mismatch.")

        pid = types.Response.parse(self.xcpPDU).type
        if pid != 'OK' and pid == 'ERR':
            if cmd.name != 'SYNCH':
                err = types.XcpError.parse(self.xcpPDU[1 : ])
                raise types.XcpResponseError(err)
        else:
            pass    # Und nu??
        return self.xcpPDU[1 : ]

    def __str__(self):
        return "[Current Message]: {}".format(self.message)

    __repr__ = __str__


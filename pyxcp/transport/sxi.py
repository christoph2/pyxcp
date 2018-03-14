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

import struct

import serial

from ..logger import Logger
from ..utils import hexDump
from ..timing import Timing
import pyxcp.types as types


class SxI(object):

    MAX_DATAGRAM_SIZE = 512
    HEADER = "<HH"
    HEADER_SIZE = struct.calcsize(HEADER)

    def __init__(self, portName, baudrate = 9600, bytesize = 8, parity = 'N', stopbits = 1, timeout = 0.75, config = {}, loglevel = "WARN"):
        self.parent = None
        self.portName = portName
        self.port = None
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        self.logger = Logger("transport.SxI")
        self.logger.setLevel(loglevel)
        self.counter = 0
        self.timing = Timing()
        self.connect()

    def __del__(self):
        self.disconnect()

    def connect(self):
        #SerialPort.counter += 1
        self.logger.debug("Trying to open serial port {}.".format(self.portName))
        try:
            #self.port = serial.Serial(self.portName, self._baudrate , self._bytesize, self._parity,
            #    self._stopbits, self._timeout
            #)
            self.port = serial.Serial(self.portName, self._baudrate, timeout = self._timeout)
        except serial.SerialException as e:
            self.logger.error("{}".format(e))
            raise
        self.logger.info("Serial port openend as '{}' @ {} Bits/Sec.".format(self.port.portstr, self.port.baudrate))

    def output(self, enable):
        if enable:
            self.port.rts = False
            self.port.dtr = False
        else:
            self.port.rts = True
            self.port.dtr = True

    def flush(self):
        self.port.flush()

    def disconnect(self):
        if self.port and self.port.isOpen() == True:
            self.port.close()

    def request(self, cmd, *data):
        self.logger.debug(cmd.name)
        header = struct.pack("<HH", len(data) + 1, self.counter)
        frame = header + bytearray([cmd, *data])
        self.logger.debug("-> {}".format(hexDump(frame)))
        self.timing.start()
        self.port.write(frame)

        rawLength = self.port.read(2)
        length = struct.unpack("<H", rawLength)[0]
        response = self.port.read(length + 2)
        self.timing.stop()
        response = rawLength + response

        if len(response) < self.HEADER_SIZE:
            raise types.FrameSizeError("Frame too short.")
        self.logger.debug("<- {}\n".format(hexDump(response)))
        self.packetLen, self.seqNo = struct.unpack(SxI.HEADER, response[ : 4])
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

    close = disconnect


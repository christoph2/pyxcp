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

import struct

import serial

from pyxcp.transport.base import BaseTransport


class SxI(BaseTransport):

    MAX_DATAGRAM_SIZE = 512
    TIMEOUT = 0.75
    HEADER = struct.Struct("<HH")
    HEADER_SIZE = HEADER.size

    def __init__(self, port, baudrate=9600, bytesize=8, parity='N',
                 stopbits=1, config=None, loglevel="WARN"):
        self.portName = port
        self.commPort = None
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        super(SxI, self).__init__(config, loglevel)

    def __del__(self):
        self.closeConnection()

    def connect(self):
        self.logger.debug(
            "Trying to open serial commPort {}.".format(self.portName))
        try:
            self.commPort = serial.Serial(
                self.portName, self._baudrate, timeout=SxI.TIMEOUT)
        except serial.SerialException as e:
            self.logger.error("{}".format(e))
            raise
        self.logger.info("Serial commPort openend as '{}' @ {} Bits/Sec.".format(
            self.commPort.portstr, self.commPort.baudrate))
        self.startListener()

    def output(self, enable):
        if enable:
            self.commPort.rts = False
            self.commPort.dtr = False
        else:
            self.commPort.rts = True
            self.commPort.dtr = True

    def flush(self):
        self.commPort.flush()

    def listen(self):
        while True:
            if self.closeEvent.isSet():
                return
            if not self.commPort.inWaiting():
                continue
            length, counter = self.HEADER.unpack(
                self.commPort.read(self.HEADER_SIZE))

            response = self.commPort.read(length)
            self.timing.stop()

            self.processResponse(response, length, counter)

    def send(self, frame):
        self.commPort.write(frame)

    def closeConnection(self):
        if self.commPort and self.commPort.isOpen():
            self.commPort.close()

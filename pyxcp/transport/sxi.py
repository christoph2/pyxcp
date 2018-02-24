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

"""
Name    Type        Representation  Range of value
MAX_CTO Parameter   BYTE        0x08 – 0xFF
MAX_DTO Parameter   WORD        0x0008 – 0xFFFF
"""

import struct

import serial

from ..logger import Logger

class SxI(object):

    MAX_DATAGRAM_SIZE = 512
    HEADER = "<HH"
    HEADER_SIZE = struct.calcsize(HEADER)

    def __init__(self, portName, baudrate = 9600, bytesize = serial.EIGHTBITS,
                 parity = serial.PARITY_NONE, stopbits = serial.STOPBITS_ONE, timeout = 0.5, loglevel = "WARN"):
        self.parent = None
        self._portName = portName
        self._port = None
        self._baudrate = baudrate
        self._bytesize = bytesize
        self._parity = parity
        self._stopbits = stopbits
        self._timeout = timeout
        self.logger = Logger("pycxp::SxI")
        self.logger.setLevel(loglevel)
        self.connected = False
        self.connect()

    def connect(self):
        #SerialPort.counter += 1
        self.logger.debug("Trying to open serial port {}.".format(self._portName))
        try:
            self._port = serial.Serial(self._portName, self._baudrate , self._bytesize, self._parity,
                self._stopbits, self._timeout
            )
        except serial.SerialException as e:
            self.logger.error("{}".format(e))
            raise
        self.logger.info("Serial port openend as '{}' @ {} Bits/Sec.".format(self._port.portstr, self._port.baudrate))
        self.connected = True
        return True

    def output(self, enable):
        if enable:
            self._port.rts = False
            self._port.dtr = False
        else:
            self._port.rts = True
            self._port.dtr = True

    def flush(self):
        self._port.flush()

    def disconnect(self):
        if self._port.isOpen() == True:
            self._port.close()

    close = disconnect


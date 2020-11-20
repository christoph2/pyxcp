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
from time import perf_counter, time

import serial

from pyxcp.transport.base import BaseTransport
import pyxcp.types as types


class SxI(BaseTransport):
    """

    """

    PARAMETER_MAP = {
        #                        Type    Req'd   Default
        "PORT":                 (str,    False,  "COM1"),
        "BITRATE":             (int,    False,  38400),
        "BYTESIZE":             (int,    False,  8),
        "PARITY":               (str,    False,  "N"),
        "STOPBITS":             (int,    False,  1),
    }

    MAX_DATAGRAM_SIZE = 512
    TIMEOUT = 0.75
    HEADER = struct.Struct("<HH")
    HEADER_SIZE = HEADER.size

    def __init__(self, config=None):
        super(SxI, self).__init__(config)
        self.loadConfig(config)
        self.portName = self.config.get("PORT")
        self.baudrate = self.config.get("BITRATE")

    def __del__(self):
        self.closeConnection()

    def connect(self):

        self.logger.debug(
            "Trying to open serial commPort {}.".format(self.portName))
        try:
            self.commPort = serial.Serial(
                self.portName, self.baudrate, timeout=SxI.TIMEOUT)
        except serial.SerialException as e:
            self.logger.error("{}".format(e))
            raise
        self.logger.info("Serial commPort openend as '{}' @ {} Bits/Sec.".format(
            self.commPort.portstr, self.baudrate))
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
        high_resolution_time = self.perf_counter_origin > 0
        timestamp_origin = self.timestamp_origin
        perf_counter_origin = self.perf_counter_origin

        while True:
            if self.closeEvent.isSet():
                return
            if not self.commPort.inWaiting():
                continue
            if high_resolution_time:
                recv_timestamp = time()
            else:
                recv_timestamp = timestamp_origin + perf_counter() - perf_counter_origin
            length, counter = self.HEADER.unpack(
                self.commPort.read(self.HEADER_SIZE))

            response = self.commPort.read(length)
            self.timing.stop()

            if len(response) != length:
                raise types.FrameSizeError("Size mismatch.")

            self.processResponse(response, length, counter, recv_timestamp)

    def send(self, frame):
        if self.perf_counter_origin > 0:
            self.pre_send_timestamp = time()
            self.commPort.write(frame)
            self.post_send_timestamp = time()
        else:
            pre_send_timestamp = perf_counter()
            self.commPort.write(frame)
            post_send_timestamp = perf_counter()
            self.pre_send_timestamp = self.timestamp_origin + pre_send_timestamp - self.perf_counter_origin
            self.post_send_timestamp = self.timestamp_origin + post_send_timestamp - self.perf_counter_origin

    def closeConnection(self):
        if hasattr(self, "commPort") and self.commPort.isOpen():
            self.commPort.close()

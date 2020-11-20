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

import usb.core
import usb.util
import struct
from time import perf_counter, sleep, time
from array import array
from collections import deque
from traceback import format_exc

from pyxcp.transport.base import BaseTransport
import pyxcp.types as types


class Usb(BaseTransport):
    """
    """

    PARAMETER_MAP = {
        #                            Type    Req'd   Default
        "serial_number":             (str,    True,  ""),
        "configuration_number":      (int,    True,  1),
        "interface_number":          (int,    True,  2),
        "command_endpoint_number":   (int,    True,  0),
        "reply_endpoint_number":     (int,    True,  1),
    }
    HEADER = struct.Struct("<2H")
    HEADER_SIZE = HEADER.size

    def __init__(self, config=None):
        super(Usb, self).__init__(config)
        self.loadConfig(config)
        self.serial_number = self.config.get("serial_number").strip()
        self.configuration_number = self.config.get("configuration_number")
        self.interface_number = self.config.get("interface_number")
        self.command_endpoint_number = self.config.get("command_endpoint_number")
        self.reply_endpoint_number = self.config.get("reply_endpoint_number")
        self.device = None

        self.status = 0

    def connect(self):
        for device in usb.core.find(find_all=True):
            try:
                if device.serial_number.strip().strip('\0').lower() == self.serial_number.lower():
                    self.device = device
                    break
                else:
                    print(device.serial_number.strip().strip('\0').lower(), self.serial_number.lower())
            except:
                continue
        else:
            raise Exception("Device with serial {} not found".format(self.serial_number))

        cfg = self.device.set_configuration(self.configuration_number)
        cfg = self.device.get_active_configuration()

        interface = cfg[(self.interface_number, 0)]

        self.command_endpoint = interface[self.command_endpoint_number]
        self.reply_endpoint = interface[self.reply_endpoint_number]

        self.startListener()
        self.status = 1  # connected

    def listen(self):
        HEADER_UNPACK = self.HEADER.unpack
        HEADER_SIZE = self.HEADER_SIZE

        high_resolution_time = self.perf_counter_origin > 0
        timestamp_origin = self.timestamp_origin
        perf_counter_origin = self.perf_counter_origin

        processResponse = self.processResponse
        close_event_set = self.closeEvent.isSet

        read = self.reply_endpoint.read

        header = array('B', bytes(HEADER_SIZE))

        while 1:

            try:
                if close_event_set():
                    break

                try:
                    if high_resolution_time:
                        recv_timestamp = time()
                    else:
                        recv_timestamp = timestamp_origin + perf_counter() - perf_counter_origin
                    read(header, 1)
                except:
                    sleep(0.001)
                    continue

                length, counter = HEADER_UNPACK(header)

                response = bytes(read(length))

                processResponse(response, length, counter, recv_timestamp)

            except:
                print('recv loop error', format_exc())
                self.status = 0  # disconnected
                break

    def send(self, frame):
        if self.perf_counter_origin > 0:
            self.pre_send_timestamp = time()
            self.command_endpoint.write(frame)
            self.post_send_timestamp = time()
        else:
            pre_send_timestamp = perf_counter()
            self.command_endpoint.write(frame)
            post_send_timestamp = perf_counter()
            self.pre_send_timestamp = self.timestamp_origin + pre_send_timestamp - self.perf_counter_origin
            self.post_send_timestamp = self.timestamp_origin + post_send_timestamp - self.perf_counter_origin

    def closeConnection(self):
        if self.device is not None:
            usb.util.dispose_resources(self.device)

#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__="""
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


import pyxcp.transport.can as can

from canlib import canlib, Frame
from canlib.canlib import ChannelData

class Kvaser(can.CanInterfaceBase):
    """
    """
    def __init__(self, channel = 0, openFlags = canlib.canOPEN_ACCEPT_VIRTUAL):
        self.channel = 0
        self.openFlags = openFlags

    def init(self, parent, master_id_with_ext: int, slave_id_with_ext: int, receive_callback):
        self.parent = parent
        bitrate = canlib.canBITRATE_500K
        #bitrateFlags = canlib.canDRIVER_NORMAL
        self.ch = canlib.openChannel(self.channel, self.openFlags)
        self.parent.logger.debug("{} [CANLib version: {}]".format(ChannelData(self.channel).device_name, canlib.dllversion()))
        self.ch.setBusParams(canlib.canBITRATE_250K)
        #self.ch.setBusOutputControl(bitrateFlags)
        self.ch.iocontrol.timer_scale = 10  # 10µS, fixed for now.

    def connect(self):
        self.ch.busOn()

    def close(self):
        self.tearDownChannel()

    def tearDownChannel(self):
        try:
            self.ch.busOff()
            self.ch.close()
        except canlib.exceptions.CanGeneralError:
            pass

    def transmit(self, payload):
        frame = Frame(id_ = self.parent.can_id_slave, data = payload, flags = canlib.canMSG_EXT)
        self.ch.write(frame)

    def read(self):
        try:
            frame = self.ch.read(5)
        except canlib.exceptions.CanNoMsg:
            return None
        else:
            return can.Frame(id_ = frame.id, dlc = frame.dlc, data = frame.data, timestamp = frame.timestamp)

    def getTimestampResolution(self):
        return 10 * 1000

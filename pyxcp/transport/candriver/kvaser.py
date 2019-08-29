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

from canlib import canlib
from canlib import Frame as KVFrame
from canlib.canlib import ChannelData


BAUDRATE_PRESETS = {
    1000000:    canlib.canBITRATE_1M,
    500000:     canlib.canBITRATE_500K,
    250000:     canlib.canBITRATE_250K,
    125000:     canlib.canBITRATE_125K,
    100000:     canlib.canBITRATE_100K,
    83333:      canlib.canBITRATE_83K,
    62500:      canlib.canBITRATE_62K,
    50000:      canlib.canBITRATE_50K
}


class Kvaser(can.CanInterfaceBase):
    """
    """

    PARAMETER_MAP = {
        #                        Type    Req'd   Default
        "KV_CHANNEL":           (int,    False,  0),
        "KV_ACCEPT_VIRTUAL":    (bool,   False,  True),
        "KV_BAUDRATE_PRESET":   (bool,   False,  True),
    }

    def __init__(self):
        self.connected = False

    def init(self, parent, receive_callback):
        self.parent = parent

    def connect(self):
        self.channel = self.config.get("KV_CHANNEL")
        openFlags = canlib.canOPEN_ACCEPT_VIRTUAL if self.config.get("KV_ACCEPT_VIRTUAL")== True else None
        bitrate = canlib.canBITRATE_500K
        #bitrateFlags = canlib.canDRIVER_NORMAL
        self.ch = canlib.openChannel(self.channel, openFlags)
        self.parent.logger.debug("{} [CANLib version: {}]".format(ChannelData(self.channel).device_name, canlib.dllversion()))

        baudrate = int(self.parent.config.get("BAUDRATE"))
        if self.config.get("KV_BAUDRATE_PRESET"):
            if not baudrate in BAUDRATE_PRESETS:
                raise ValueError("No preset for baudrate '{}'".format(baudrate))
            self.ch.setBusParams(BAUDRATE_PRESETS[baudrate])
        else:
            samplePoint = self.config.get("SAMPLE_POINT")
            sjw = self.config.get("SJW")
            tseg1 = self.config.get("TSEG1")
            tseg2 = self.config.get("TSEG2")
            self.ch.setBusParams(baudrate, tseg1, tseg2, sjw)
        self.ch.iocontrol.timer_scale = 10  # 10µS, fixed for now.
        self.ch.busOn()
        self.connected = True

    def close(self):
        self.tearDownChannel()
        self.connected = False

    def tearDownChannel(self):
        if hasattr(self, "ch"):
            try:
                self.ch.busOff()
                self.ch.close()
            except canlib.exceptions.CanGeneralError:
                pass

    def transmit(self, payload):
        frame = KVFrame(id_ = self.parent.can_id_slave.id, data = payload,
            flags = canlib.canMSG_EXT if self.parent.can_id_slave.is_extended else canlib.canMSG_STD)
        self.ch.write(frame)

    def read(self):
        if not self.connected:
            return
        try:
            frame = self.ch.read(5)
        except canlib.exceptions.CanNoMsg:
            return None
        else:
            extended = (frame.flags & canlib.canMSG_EXT) == canlib.canMSG_EXT
            identifier = can.Identifier.make_identifier(frame.id, extended)
            return can.Frame(id_ = identifier, dlc = frame.dlc, data = frame.data, timestamp = frame.timestamp)

    def getTimestampResolution(self):
        return 10 * 1000

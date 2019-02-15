#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = """
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

from pyxcp.master.base import MasterBaseType
from pyxcp import types
from pyxcp.utils import flatten


class Master(MasterBaseType):
    # Python <= 3.4 requires nasty hack (flatten) to unpack tuples.

    def shortDownload(self, address, addressExt, *data):
        length = len(data)
        addr = struct.pack("<I", address)
        addr_data = flatten(addr, data)
        response = self.transport.request(
            types.Command.SHORT_DOWNLOAD,
            length, 0, addressExt, *addr_data)
        return response

    def modifyBits(self, shiftValue, andMask, xorMask):
        # A = ( (A) & ((~((dword)(((word)~MA)<<S))) )^((dword)(MX<<S)) )
        am = struct.pack("<H", andMask)
        xm = struct.pack("<H", xorMask)
        response = self.transport.request(
            types.Command.MODIFY_BITS, shiftValue, *flatten(am, xm))
        return response

    def setDaqPtr(self, daqListNumber, odtNumber, odtEntryNumber):
        daqList = struct.pack("<H", daqListNumber)
        response = self.transport.request(
            types.Command.SET_DAQ_PTR,
            0, *flatten(daqList), odtNumber, odtEntryNumber)
        return response

    def setDaqListMode(self, mode, daqListNumber, eventChannelNumber,
                       prescaler, priority):
        dln = struct.pack("<H", daqListNumber)
        ecn = struct.pack("<H", eventChannelNumber)
        response = self.transport.request(
            types.Command.SET_DAQ_LIST_MODE,
            mode, *flatten(dln, ecn), prescaler, priority)
        return response

    def allocOdt(self, daqListNumber, odtCount):
        dln = struct.pack("<H", daqListNumber)
        response = self.transport.request(
            types.Command.ALLOC_ODT, 0, flatten(dln), odtCount)
        return response

    def allocOdtEntry(self, daqListNumber, odtNumber, odtEntriesCount):
        dln = struct.pack("<H", daqListNumber)
        response = self.transport.request(
            types.Command.ALLOC_ODT_ENTRY,
            0, flatten(dln), odtNumber, odtEntriesCount)
        return response

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

import array
import enum
import logging
import os
import select
import struct
import sys
import time

import six

from pyxcp import checksum
from pyxcp import types
from pyxcp import transport
from pyxcp.dllif import getKey
from pyxcp.client import Client

def test():
    xcpClient = Client(transport.Eth('localhost', connected = False))
    xcpClient.connect()

    print("calpag ?", xcpClient.supportsCalpag)
    print("daq ?", xcpClient.supportsDaq)
    print("pgm ?", xcpClient.supportsPgm)
    print("stim ?", xcpClient.supportsStim)


    xcpClient.getStatus()
    xcpClient.synch()
    xcpClient.getCommModeInfo()

    result = xcpClient.getID(0x01)
    xcpClient.upload(result.length)

    unlock(xcpClient, 4)
    #length, seed = xcpClient.getSeed(0x7ba, 0, 4)
    #print("SEED: ", hexDump(seed), flush = True)
    #_, kee = skloader.getKey(b"SeedNKeyXcp.dll", 4, seed)
    #print("KEE:", kee)
    #print(xcpClient.unlock(0x7a, len(kee), kee))


    print("DAQ_PROC_INFO: ", xcpClient.getDaqProcessorInfo())

    print("TIMESTAMP: {:04X}".format(xcpClient.getDaqClock()))

    #print("readDAQ:", xcpClient.readDaq())

    print("daqResolutionInfo", xcpClient.getDaqResolutionInfo())

    dpi = xcpClient.getDaqProcessorInfo()

    for ecn in range(dpi.maxEventChannel):
        eci = xcpClient.getEventChannelInfo(ecn)
        print(eci)
        data = xcpClient.upload(eci.eventChannelNameLength)
        print("EventChannelName:", data.decode("latin1"))

    #print("GetDAQListInfo", xcpClient.getDaqListInfo(0))
    xcpClient.freeDaq()
    print("AllocDAQ:", xcpClient.allocDaq(2))

    xcpClient.setMta(0x1C0000)
    print("CS:", xcpClient.buildChecksum(4742))

    unlock(xcpClient, 1)
    verify(xcpClient, 0x1C0000, 128)

    #print("PS:", xcpClient.programStart()) # ERR_ACCESS_LOCKED

    xcpClient.disconnect()
    xcpClient.close()


def timecode(ticks, mode):
    units = {
        "DAQ_TIMESTAMP_UNIT_1PS"  : -12,
        "DAQ_TIMESTAMP_UNIT_10PS" : -11,
        "DAQ_TIMESTAMP_UNIT_100PS": -10,
        "DAQ_TIMESTAMP_UNIT_1NS"  : -9,
        "DAQ_TIMESTAMP_UNIT_10NS" : -8,
        "DAQ_TIMESTAMP_UNIT_100NS": -7,
        "DAQ_TIMESTAMP_UNIT_1US"  : -6,
        "DAQ_TIMESTAMP_UNIT_10US" : -5,
        "DAQ_TIMESTAMP_UNIT_100US": -4,
        "DAQ_TIMESTAMP_UNIT_1MS"  : -3,
        "DAQ_TIMESTAMP_UNIT_10MS" : -2,
        "DAQ_TIMESTAMP_UNIT_100MS": -1,
        "DAQ_TIMESTAMP_UNIT_1S"   : 0,
    }
    return (10 ** units[mode.timestampMode.unit]) * mode.timestampTicks * ticks


def cstest():
    tr = transport.Eth('localhost', connected = False, loglevel = "DEBUG")
    #tr = transport.SxI("COM27", 115200, loglevel = "WARN")
    xcpClient = Client(tr)

#    tm = Timing()

    conn = xcpClient.connect()
    print(conn, flush = True)

    print("calpag ?", xcpClient.supportsCalpag)
    print("daq ?", xcpClient.supportsDaq)
    print("pgm ?", xcpClient.supportsPgm)
    print("stim ?", xcpClient.supportsStim)

    xcpClient.getStatus()
    xcpClient.synch()

    if conn.commModeBasic.optional:
        xcpClient.getCommModeInfo()
    else:
        print("No details on connection.")

    result = xcpClient.getID(0x01)
    result = xcpClient.upload(result.length)
    print("ID: '{}'".format(result.decode("utf8")))

    resInfo = xcpClient.getDaqResolutionInfo()
    print(resInfo)
    #xcpClient.getDaqProcessorInfo()

#    print("CS:", xcpClient.buildChecksum(4711))

    start = xcpClient.getDaqClock()
    print("Timestamp / Start: {}".format(start))

    length, seed = xcpClient.getSeed(0, 4)
    #print(seed)
    #print("SEED: ", hexDump(seed))
    #unlock(xcpClient, 1)
    _, kee = getKey("SeedNKeyXcp.dll", "1", seed) # b'\xa9\xe0\x7fSm;\xa3-;M')
    #res = xcpClient.unlock(len(kee), kee)
    #print(res)

##
##    xcpClient.freeDaq()
##    print("AllocDAQ:", xcpClient.allocDaq(2))
##
##    print("allocOdt", xcpClient.allocOdt(1, 5))
##    print("allocOdt", xcpClient.allocOdt(0, 4))
##    print("allocOdt", xcpClient.allocOdt(1, 3))
##
##    print("allocOdt", xcpClient.allocOdtEntry(1, 3, 5))
##    print("allocOdt", xcpClient.allocOdtEntry(0, 1, 2))
##    print("allocOdt", xcpClient.allocOdtEntry(0, 3, 6))
##    print("allocOdt", xcpClient.allocOdtEntry(1, 1, 5))
##

    #xcpClient.freeDaq()

#    for _ in range(10):
#        tm.start()
#        time.sleep(0.250)
#        tm.stop()
#        stop = xcpClient.getDaqClock()
#        print("trueValue: {}".format(timecode(stop - start, resInfo)))
#        print("Timestamp / Diff: {}".format(stop - start))

    print("Timer")
    print("=====")
#    print(tm)

    xcpClient.setMta(0x1C0000)
    xcpClient.disconnect()
    xcpClient.close()
    print("XCP roundtrip timing")
    print("=" * 20)
 #   print(tr.timing)

    #skloader.quit()


if __name__=='__main__':
    #setpriority(priority = 4)
    #sxi = transport.SxI("COM27", 115200, loglevel = "DEBUG")
    #print(sxi._port)
    #sxi.disconnect()
    cstest()


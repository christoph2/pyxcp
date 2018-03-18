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
from collections import namedtuple
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
from pyxcp.master import Master
from pyxcp.utils import hexDump

def test():
    xm = Master(transport.Eth('localhost', connected = False))
    xm.connect()

    print("calpag ?", xm.supportsCalpag)
    print("daq ?", xm.supportsDaq)
    print("pgm ?", xm.supportsPgm)
    print("stim ?", xm.supportsStim)


    xm.getStatus()
    xm.synch()
    xm.getCommModeInfo()

    result = xm.getID(0x01)
    xm.upload(result.length)

    unlock(xm, 4)
    #length, seed = xm.getSeed(0x7ba, 0, 4)
    #print("SEED: ", hexDump(seed), flush = True)
    #_, kee = skloader.getKey(b"SeedNKeyXcp.dll", 4, seed)
    #print("KEE:", kee)
    #print(xm.unlock(0x7a, len(kee), kee))


    print("DAQ_PROC_INFO: ", xm.getDaqProcessorInfo())

    print("TIMESTAMP: {:04X}".format(xm.getDaqClock()))

    #print("readDAQ:", xm.readDaq())

    print("daqResolutionInfo", xm.getDaqResolutionInfo())

    dpi = xm.getDaqProcessorInfo()

    for ecn in range(dpi.maxEventChannel):
        eci = xm.getEventChannelInfo(ecn)
        print(eci)
        data = xm.upload(eci.eventChannelNameLength)
        print("EventChannelName:", data.decode("latin1"))

    #print("GetDAQListInfo", xm.getDaqListInfo(0))
    xm.freeDaq()
    print("AllocDAQ:", xm.allocDaq(2))

    xm.setMta(0x1C0000)
    print("CS:", xm.buildChecksum(4742))

    unlock(xm, 1)
    verify(xm, 0x1C0000, 128)

    #print("PS:", xm.programStart()) # ERR_ACCESS_LOCKED

    xm.disconnect()
    xm.close()


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
    tr = transport.Eth('localhost', port= 5555, connected = False, loglevel = "DEBUG")
    #tr = transport.SxI("COM27", 115200, loglevel = "WARN")
    with Master(tr) as xm:
    #    tm = Timing()

        conn = xm.connect()
        print(conn, flush = True)

        print("calpag ?", xm.supportsCalpag)
        print("daq ?", xm.supportsDaq)
        print("pgm ?", xm.supportsPgm)
        print("stim ?", xm.supportsStim)

        xm.getStatus()
        xm.synch()

        if conn.commModeBasic.optional:
            xm.getCommModeInfo()
        else:
            print("No details on connection.")

        result = xm.getID(0x01)
        result = xm.upload(result.length)
        print("ID: '{}'".format(result.decode("utf8")))

        resInfo = xm.getDaqResolutionInfo()
        print(resInfo)
        #xm.getDaqProcessorInfo()

    #    print("CS:", xm.buildChecksum(4711))

        start = xm.getDaqClock()
        print("Timestamp / Start: {}".format(start))

        length, seed = xm.getSeed(0, 0xff)
        #print(seed)
        print("SEED: ", hexDump(seed))
        #unlock(xm, 1)
        resultCode, kee = getKey("SeedNKeyXcp.dll", 1, seed)
        if resultCode == 0:
            res = xm.unlock(len(kee), kee)
            print(res)


        startMeasurement(xm)
    ##
    ##    xm.freeDaq()
    ##    print("AllocDAQ:", xm.allocDaq(2))
    ##
    ##    print("allocOdt", xm.allocOdt(1, 5))
    ##    print("allocOdt", xm.allocOdt(0, 4))
    ##    print("allocOdt", xm.allocOdt(1, 3))
    ##
    ##    print("allocOdt", xm.allocOdtEntry(1, 3, 5))
    ##    print("allocOdt", xm.allocOdtEntry(0, 1, 2))
    ##    print("allocOdt", xm.allocOdtEntry(0, 3, 6))
    ##    print("allocOdt", xm.allocOdtEntry(1, 1, 5))
    ##

        #xm.freeDaq()

    #    for _ in range(10):
    #        tm.start()
    #        time.sleep(0.250)
    #        tm.stop()
    #        stop = xm.getDaqClock()
    #        print("trueValue: {}".format(timecode(stop - start, resInfo)))
    #        print("Timestamp / Diff: {}".format(stop - start))

        print("Timer")
        print("=====")
    #    print(tm)

        xm.setMta(0x1C0000)
        xm.disconnect()
        #xm.close()
        print("XCP roundtrip timing")
        print("=" * 20)
 #   print(tr.timing)


DaqEntry = namedtuple("DaqEntry", "daq odt entry bitoff size ext addr")

def startMeasurement(cl):
    print(cl.getDaqProcessorInfo())
    cl.freeDaq()
    cl.allocDaq(2)

    cl.allocOdt(1, 13)
    cl.allocOdt(0, 2)

    cl.allocOdtEntry(0, 0, 1)
    cl.allocOdtEntry(0, 1, 1)
    cl.allocOdtEntry(0, 2, 1)
    cl.allocOdtEntry(0, 3, 1)
    cl.allocOdtEntry(0, 4, 1)
    cl.allocOdtEntry(0, 5, 1)
    cl.allocOdtEntry(0, 6, 1)
    cl.allocOdtEntry(0, 7, 1)
    cl.allocOdtEntry(0, 8, 1)
    cl.allocOdtEntry(0, 9, 1)
    cl.allocOdtEntry(0, 10, 1)
    cl.allocOdtEntry(0, 11, 3)
    cl.allocOdtEntry(0, 12, 5)

    cl.allocOdtEntry(1, 0, 1)
    cl.allocOdtEntry(1, 1, 1)

    de0 = (
        DaqEntry(daq=0, odt=0,  entry=0, bitoff=255, size=2, ext=0, addr=0x001BE068),
        DaqEntry(daq=0, odt=1,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE06A),
        DaqEntry(daq=0, odt=2,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE070),
        DaqEntry(daq=0, odt=3,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE076),
        DaqEntry(daq=0, odt=4,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE07C),
        DaqEntry(daq=0, odt=5,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE082),
        DaqEntry(daq=0, odt=6,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE088),
        DaqEntry(daq=0, odt=7,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE08E),
        DaqEntry(daq=0, odt=8,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE094),
        DaqEntry(daq=0, odt=9,  entry=0, bitoff=255, size=6, ext=0, addr=0x001BE09A),
        DaqEntry(daq=0, odt=10, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE0A0),
        DaqEntry(daq=0, odt=11, entry=0, bitoff=255, size=2, ext=0, addr=0x001BE0A6),
        DaqEntry(daq=0, odt=11, entry=1, bitoff=255, size=1, ext=0, addr=0x001BE0CF),
        DaqEntry(daq=0, odt=11, entry=2, bitoff=255, size=3, ext=0, addr=0x001BE234),
        DaqEntry(daq=0, odt=12, entry=0, bitoff=255, size=1, ext=0, addr=0x001BE237),
        DaqEntry(daq=0, odt=12, entry=1, bitoff=255, size=1, ext=0, addr=0x001BE24F),
        DaqEntry(daq=0, odt=12, entry=2, bitoff=255, size=1, ext=0, addr=0x001BE269),
        DaqEntry(daq=0, odt=12, entry=3, bitoff=255, size=1, ext=0, addr=0x001BE5A3),
        DaqEntry(daq=0, odt=12, entry=4, bitoff=255, size=1, ext=0, addr=0x001C0003),
        DaqEntry(daq=1, odt=0 , entry=0, bitoff=255, size=2, ext=0, addr=0x001C002C),
        DaqEntry(daq=1, odt=1 , entry=0, bitoff=255, size=2, ext=0, addr=0x001C002E),
    )
    for daq, odt, entry, bitoff, size, ext, addr in de0:
        cl.setDaqPtr(daq, odt,  entry)
        cl.writeDaq(bitoff, size, ext, addr)
    """
    SET_DAQ_LIST_MODE mode=10h daq=0 event=1 prescaler=1 priority=1
    START_STOP_DAQ_LIST mode=02h daq=0
    SET_DAQ_LIST_MODE mode=10h daq=1 event=2 prescaler=1 priority=2
    START_STOP_DAQ_LIST mode=02h daq=1
    GET_DAQ_CLOCK
    GET_DAQ_CLOCK
    START_STOP_SYNCH mode=01h
    """
    cl.setDaqListMode(0x10, 0, 1, 1, 1)
    cl.startStopDaqList(0x02, 0)
    cl.setDaqListMode(0x10, 1, 2, 1, 2)
    cl.startStopDaqList(0x02, 1)
    cl.startStopSynch(0x01)

    time.sleep(3.0)

    cl.startStopSynch(0x00)

if __name__=='__main__':
    cstest()

"""
FREE_DAQ
ALLOC_DAQ count=2
ALLOC_ODT daq=0 count=13
ALLOC_ODT daq=1 count=2

ALLOC_ODT_ENTRY daq=0 odt=0 count=1
ALLOC_ODT_ENTRY daq=0 odt=1 count=1
ALLOC_ODT_ENTRY daq=0 odt=2 count=1
ALLOC_ODT_ENTRY daq=0 odt=3 count=1
ALLOC_ODT_ENTRY daq=0 odt=4 count=1
ALLOC_ODT_ENTRY daq=0 odt=5 count=1
ALLOC_ODT_ENTRY daq=0 odt=6 count=1
ALLOC_ODT_ENTRY daq=0 odt=7 count=1
ALLOC_ODT_ENTRY daq=0 odt=8 count=1
ALLOC_ODT_ENTRY daq=0 odt=9 count=1
ALLOC_ODT_ENTRY daq=0 odt=10 count=1
ALLOC_ODT_ENTRY daq=0 odt=11 count=3
ALLOC_ODT_ENTRY daq=0 odt=12 count=5

ALLOC_ODT_ENTRY daq=1 odt=0 count=1
ALLOC_ODT_ENTRY daq=1 odt=1 count=1

SET_DAQ_PTR daq=0 odt=0 entry=0
WRITE_DAQ bitoff=255 size=2 ext=0 addr=001BE068h        
SET_DAQ_PTR daq=0 odt=1 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE06Ah        
SET_DAQ_PTR daq=0 odt=2 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE070h        
SET_DAQ_PTR daq=0 odt=3 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE076h        
SET_DAQ_PTR daq=0 odt=4 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE07Ch        
SET_DAQ_PTR daq=0 odt=5 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE082h        
SET_DAQ_PTR daq=0 odt=6 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE088h        
SET_DAQ_PTR daq=0 odt=7 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE08Eh        
SET_DAQ_PTR daq=0 odt=8 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE094h        
SET_DAQ_PTR daq=0 odt=9 entry=0                         
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE09Ah        
SET_DAQ_PTR daq=0 odt=10 entry=0                        
WRITE_DAQ bitoff=255 size=6 ext=0 addr=001BE0A0h        
SET_DAQ_PTR daq=0 odt=11 entry=0                        
WRITE_DAQ bitoff=255 size=2 ext=0 addr=001BE0A6h        
WRITE_DAQ bitoff=255 size=1 ext=0 addr=001BE0CFh        
WRITE_DAQ bitoff=255 size=3 ext=0 addr=001BE234h        
SET_DAQ_PTR daq=0 odt=12 entry=0                        
WRITE_DAQ bitoff=255 size=1 ext=0 addr=001BE237h        
WRITE_DAQ bitoff=255 size=1 ext=0 addr=001BE24Fh        
WRITE_DAQ bitoff=255 size=1 ext=0 addr=001BE269h        
WRITE_DAQ bitoff=255 size=1 ext=0 addr=001BE5A3h        
WRITE_DAQ bitoff=255 size=1 ext=0 addr=001C0003h        
SET_DAQ_PTR daq=1 odt=0 entry=0
WRITE_DAQ bitoff=255 size=2 ext=0 addr=001C002Ch
SET_DAQ_PTR daq=1 odt=1 entry=0
WRITE_DAQ bitoff=255 size=2 ext=0 addr=001C002Eh

SET_DAQ_LIST_MODE mode=10h daq=0 event=1 prescaler=1 priority=1
START_STOP_DAQ_LIST mode=02h daq=0
SET_DAQ_LIST_MODE mode=10h daq=1 event=2 prescaler=1 priority=2
START_STOP_DAQ_LIST mode=02h daq=1
GET_DAQ_CLOCK
GET_DAQ_CLOCK
START_STOP_SYNCH mode=01h
"""


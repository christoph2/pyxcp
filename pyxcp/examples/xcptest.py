#!/usr/bin/env python
# -*- coding: utf-8 -*-
from collections import OrderedDict
from pprint import pprint

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

import array
from collections import namedtuple
import time

from pyxcp import checksum
from pyxcp import types
from pyxcp import transport
from pyxcp.dllif import getKey
from pyxcp.master import Master
from pyxcp.utils import hexDump


def test():
    xm = Master(transport.Eth("localhost", connected=False))
    xm.connect()

    print("calpag ?", xm.supportsCalpag)
    print("daq ?", xm.supportsDaq)
    print("pgm ?", xm.supportsPgm)
    print("stim ?", xm.supportsStim)

    xm.getStatus()
    xm.synch()
    xm.getCommModeInfo()

    result = xm.getID(0x04)
    print(result)
    # xm.upload(result.length)

    #    unlock(xm, 4)
    # length, seed = xm.getSeed(0x7ba, 0, 4)
    # print("SEED: ", hexDump(seed), flush = True)
    # _, kee = skloader.getKey(b"SeedNKeyXcp.dll", 4, seed)
    # print("KEE:", kee)
    # print(xm.unlock(0x7a, len(kee), kee))

    print("DAQ_PROC_INFO: ", xm.getDaqProcessorInfo())

    print("TIMESTAMP: {:04X}".format(xm.getDaqClock()))

    # print("readDAQ:", xm.readDaq())

    print("daqResolutionInfo", xm.getDaqResolutionInfo())

    dpi = xm.getDaqProcessorInfo()

    for ecn in range(dpi.maxEventChannel):
        eci = xm.getEventChannelInfo(ecn)
        print(eci)
        data = xm.upload(eci.eventChannelNameLength)
        print("EventChannelName:", data.decode("latin1"))

    # print("GetDAQListInfo", xm.getDaqListInfo(0))
    xm.freeDaq()
    print("AllocDAQ:", xm.allocDaq(2))

    xm.setMta(0x1C0000)
    print("CS:", xm.buildChecksum(4742))

    #    unlock(xm, 1)
    #    verify(xm, 0x1C0000, 128)

    # print("PS:", xm.programStart()) # ERR_ACCESS_LOCKED

    xm.disconnect()
    xm.close()


def timecode(ticks, mode):
    units = {
        "DAQ_TIMESTAMP_UNIT_1PS": -12,
        "DAQ_TIMESTAMP_UNIT_10PS": -11,
        "DAQ_TIMESTAMP_UNIT_100PS": -10,
        "DAQ_TIMESTAMP_UNIT_1NS": -9,
        "DAQ_TIMESTAMP_UNIT_10NS": -8,
        "DAQ_TIMESTAMP_UNIT_100NS": -7,
        "DAQ_TIMESTAMP_UNIT_1US": -6,
        "DAQ_TIMESTAMP_UNIT_10US": -5,
        "DAQ_TIMESTAMP_UNIT_100US": -4,
        "DAQ_TIMESTAMP_UNIT_1MS": -3,
        "DAQ_TIMESTAMP_UNIT_10MS": -2,
        "DAQ_TIMESTAMP_UNIT_100MS": -1,
        "DAQ_TIMESTAMP_UNIT_1S": 0,
    }
    return (10 ** units[mode.timestampMode.unit]) * mode.timestampTicks * ticks


def cstest():
    tr = transport.Eth("localhost", port=5555, protocol="UDP", loglevel="WARN")  # "DEBUG"
    # tr = transport.SxI("COM27", 115200, loglevel = "WARN")
    with Master(tr) as xm:
        #    tm = Timing()

        conn = xm.connect()
        print(conn, flush=True)

        print("calpag ?", xm.supportsCalpag)
        print("daq ?", xm.supportsDaq)
        print("pgm ?", xm.supportsPgm)
        print("stim ?", xm.supportsStim)

        print(xm.getStatus(), flush=True)
        xm.synch()

        if conn.commModeBasic.optional:
            print(xm.getCommModeInfo(), flush=True)
        else:
            print("No details on connection.")

        gid = xm.getID(0x1)
        # gid = xm.getID(0xdb)
        print("GET_ID:", gid, flush=True)
        result = xm.fetch(gid.length)
        print(result.decode("utf8"))

        #        bench(xm)

        # gid = xm.getID(0xdb)
        # print("DB", gid)
        #        result = xm.upload()
        #        print("ID: '{}'".format(result.decode("utf8")))

        #        start = time.perf_counter()
        #        result = xm.fetch(gid.length, 252)
        #        stop = time.perf_counter()
        #        print("ETA: {:.2f} s - rate: {:.2f} kB/s".format(stop - start, (gid.length / (stop - start)) / 1000 ) )

        #        print("ID: '{}'".format(result.decode("utf8")))

        xm.setMta(0x0040C280)
        bhv = xm.fetch(0x100, 16)
        print(bhv)

        resInfo = xm.getDaqResolutionInfo()
        print(resInfo, flush=True)
        xm.getDaqProcessorInfo()

        #    print("CS:", xm.buildChecksum(4711))

        start = xm.getDaqClock()
        print("Timestamp / Start: {}".format(start))
        """
        length, seed = xm.getSeed(0, 0xff)
        print("SEED: ", hexDump(seed))
        resultCode, kee = getKey("SeedNKeyXcp.dll", 1, seed)
        if resultCode == 0:
            res = xm.unlock(len(kee), kee)
            print(res)
        """

        startMeasurement(xm)
        ##
        # xm.freeDaq()
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

        # xm.freeDaq()

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

        print(xm.setMta(0x1C0000), flush=True)
        # print(xm.setRequest(0x3, 1))
        print(xm.disconnect(), flush=True)
        # xm.close()
        print("XCP roundtrip timing")
        print("=" * 20)
    for _ in range(tr.daqQueue.qsize()):
        daq = tr.daqQueue.get(timeout=1.0)
        print(types.DAQ.parse(daq))

    # dq = construct.Struct(
    #     "odt" / construct.Byte,
    #     "dl" / construct.Byte,
    #     "data" / construct.GreedyBytes,
    # )

    # ev = tr.evQueue.get(timeout = 1.0)
    # print(ev)


#   print(tr.timing)


# import pandas as pd


def bench(xm):
    import pandas as pd

    result = OrderedDict()
    for pn in range(8, 257, 8):
        # for pn in range(8, 257, 32):
        result[pn] = []
        for i in range(10):
            gid = xm.getID(0x4)
            start = time.perf_counter()
            xm.fetch(gid.length, pn)
            stop = time.perf_counter()
            eta = stop - start
            result[pn].append(eta)
    pprint(result)
    df = pd.DataFrame(result)
    df.to_csv("payloads01.csv")


# A2L linearizer


DaqEntry = namedtuple("DaqEntry", "daq odt entry bitoff size ext addr")


def startMeasurement(cl):
    print(cl.getDaqProcessorInfo())
    cl.freeDaq()
    cl.allocDaq(2)

    # cl.allocOdt(1, 13)
    # cl.allocOdt(0, 2)

    cl.allocOdt(0, 13)
    cl.allocOdt(1, 2)

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
        DaqEntry(daq=0, odt=0, entry=0, bitoff=255, size=2, ext=0, addr=0x001BE068),
        DaqEntry(daq=0, odt=1, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE06A),
        DaqEntry(daq=0, odt=2, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE070),
        DaqEntry(daq=0, odt=3, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE076),
        DaqEntry(daq=0, odt=4, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE07C),
        DaqEntry(daq=0, odt=5, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE082),
        DaqEntry(daq=0, odt=6, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE088),
        DaqEntry(daq=0, odt=7, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE08E),
        DaqEntry(daq=0, odt=8, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE094),
        DaqEntry(daq=0, odt=9, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE09A),
        DaqEntry(daq=0, odt=10, entry=0, bitoff=255, size=6, ext=0, addr=0x001BE0A0),
        DaqEntry(daq=0, odt=11, entry=0, bitoff=255, size=2, ext=0, addr=0x001BE0A6),
        DaqEntry(daq=0, odt=11, entry=1, bitoff=255, size=1, ext=0, addr=0x001BE0CF),
        DaqEntry(daq=0, odt=11, entry=2, bitoff=255, size=3, ext=0, addr=0x001BE234),
        DaqEntry(daq=0, odt=12, entry=0, bitoff=255, size=1, ext=0, addr=0x001BE237),
        DaqEntry(daq=0, odt=12, entry=1, bitoff=255, size=1, ext=0, addr=0x001BE24F),
        DaqEntry(daq=0, odt=12, entry=2, bitoff=255, size=1, ext=0, addr=0x001BE269),
        DaqEntry(daq=0, odt=12, entry=3, bitoff=255, size=1, ext=0, addr=0x001BE5A3),
        DaqEntry(daq=0, odt=12, entry=4, bitoff=255, size=1, ext=0, addr=0x001C0003),
        DaqEntry(daq=1, odt=0, entry=0, bitoff=255, size=2, ext=0, addr=0x001C002C),
        DaqEntry(daq=1, odt=1, entry=0, bitoff=255, size=2, ext=0, addr=0x001C002E),
    )
    """
-> CONNECT mode=0
<- 0xFF version=01h/01h, maxcro=FFh, maxdto=5DCh, resource=1D, mode=C0
-> GET_STATUS
<- 0xFF sessionstatus=00h, protectionstatus=1D
-> SYNC
<- 0xFE 0x00
-> GET_COMM_MODE_INFO
<- 0xFF
-> GET_ID type=1
<- 0xFF mode=0,len=6
-> UPLOAD size=6
<- 0xFF data=58 43 50 73 69 6D
-> GET_DAQ_RESOLUTION_INFO
<- 0xFF , mode=44h, , ticks=0Ah
-> GET_DAQ_CLOCK
<- 0xFF time=36779B9Ah
-> GET_SEED resource=FFh
<- 0xFF length=0Ah, seed=7C4FBDFBA3D8
-> UNLOCK key=3C7012190000
<- 0xFF
-> GET_DAQ_PROCESSOR_INFO
<- 0xFF

-> FREE_DAQ
<- 0xFF
-> ALLOC_DAQ count=2
[XcpAllocMemory] 17/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT daq=0, count=13
[XcpAllocMemory] 121/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT daq=1, count=2
[XcpAllocMemory] 137/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=0, count=1
[XcpAllocMemory] 142/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=1, count=1
[XcpAllocMemory] 147/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=2, count=1
[XcpAllocMemory] 152/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=3, count=1
[XcpAllocMemory] 157/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=4, count=1
[XcpAllocMemory] 162/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=5, count=1
[XcpAllocMemory] 167/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=6, count=1
[XcpAllocMemory] 172/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=7, count=1
[XcpAllocMemory] 177/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=8, count=1
[XcpAllocMemory] 182/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=9, count=1
[XcpAllocMemory] 187/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=10, count=1
[XcpAllocMemory] 192/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=11, count=3
[XcpAllocMemory] 207/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=0, odt=12, count=5
[XcpAllocMemory] 232/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=1, odt=0, count=1
[XcpAllocMemory] 237/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> ALLOC_ODT_ENTRY daq=1, odt=1, count=1
[XcpAllocMemory] 242/65535 Bytes used
[XcpAllocMemory] Queuesize=127
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=0,idx=0
<- 0xFF
-> WRITE_DAQ size=2,addr=001BE068h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=1,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE06Ah,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=2,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE070h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=3,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE076h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=4,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE07Ch,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=5,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE082h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=6,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE088h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=7,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE08Eh,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=8,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE094h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=9,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE09Ah,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=10,idx=0
<- 0xFF
-> WRITE_DAQ size=6,addr=001BE0A0h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=11,idx=0
<- 0xFF
-> WRITE_DAQ size=2,addr=001BE0A6h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=11,idx=1
<- 0xFF
-> WRITE_DAQ size=1,addr=001BE0CFh,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=11,idx=2
<- 0xFF
-> WRITE_DAQ size=3,addr=001BE234h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=12,idx=0
<- 0xFF
-> WRITE_DAQ size=1,addr=001BE237h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=12,idx=1
<- 0xFF
-> WRITE_DAQ size=1,addr=001BE24Fh,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=12,idx=2
<- 0xFF
-> WRITE_DAQ size=1,addr=001BE269h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=12,idx=3
<- 0xFF
-> WRITE_DAQ size=1,addr=001BE5A3h,00h
<- 0xFF
-> SET_DAQ_PTR daq=0,odt=12,idx=4
<- 0xFF
-> WRITE_DAQ size=1,addr=001C0003h,00h
<- 0xFF

-> SET_DAQ_PTR daq=1,odt=0,idx=0
<- 0xFF
-> WRITE_DAQ size=2,addr=001C002Ch,00h
<- 0xFF
-> SET_DAQ_PTR daq=1,odt=1,idx=0
<- 0xFF
-> WRITE_DAQ size=2,addr=001C002Eh,00h
<- 0xFF
-> SET_DAQ_LIST_MODE daq=0, mode=10h, prescaler=1, eventchannel=1, priority=1
<- 0xFF
DAQ 0:
 eventchannel=0001h, prescaler=1, firstOdt=0, lastOdt=12, flags=11h
 firstPid=00h
  ODT 0 (0):
   pid=0:
   firstOdtEntry=0,lastOdtEntry=0:
   [005BE068h,2]
  ODT 1 (1):
   pid=1:
   firstOdtEntry=1,lastOdtEntry=1:
   [005BE06Ah,6]
  ODT 2 (2):
   pid=2:
   firstOdtEntry=2,lastOdtEntry=2:
   [005BE070h,6]
  ODT 3 (3):
   pid=3:
   firstOdtEntry=3,lastOdtEntry=3:
   [005BE076h,6]
  ODT 4 (4):
   pid=4:
   firstOdtEntry=4,lastOdtEntry=4:
   [005BE07Ch,6]
  ODT 5 (5):
   pid=5:
   firstOdtEntry=5,lastOdtEntry=5:
   [005BE082h,6]
  ODT 6 (6):
   pid=6:
   firstOdtEntry=6,lastOdtEntry=6:
   [005BE088h,6]
  ODT 7 (7):
   pid=7:
   firstOdtEntry=7,lastOdtEntry=7:
   [005BE08Eh,6]
  ODT 8 (8):
   pid=8:
   firstOdtEntry=8,lastOdtEntry=8:
   [005BE094h,6]
  ODT 9 (9):
   pid=9:
   firstOdtEntry=9,lastOdtEntry=9:
   [005BE09Ah,6]
  ODT 10 (10):
   pid=10:
   firstOdtEntry=10,lastOdtEntry=10:
   [005BE0A0h,6]
  ODT 11 (11):
   pid=11:
   firstOdtEntry=11,lastOdtEntry=13:
   [005BE0A6h,2]
   [005BE0CFh,1]
   [005BE234h,3]
  ODT 12 (12):
   pid=12:
   firstOdtEntry=14,lastOdtEntry=18:
   [005BE237h,1]
   [005BE24Fh,1]
   [005BE269h,1]
   [005BE5A3h,1]
   [005C0003h,1]
Queue:
 xcp.pQueue        = 59DF1A
 xcp.QueueSize     = 127
 xcp.QueueLen      = 0
 xcp.QueueRp       = 0
-> START_STOP mode=02h, daq=0
<- 0xFF
-> SET_DAQ_LIST_MODE daq=1, mode=10h, prescaler=1, eventchannel=2, priority=2
<- 0xFF
DAQ 1:
 eventchannel=0002h, prescaler=1, firstOdt=13, lastOdt=14, flags=11h
 firstPid=0Dh
  ODT 0 (13):
   pid=13:
   firstOdtEntry=19,lastOdtEntry=19:
   [005C002Ch,2]
  ODT 1 (14):
   pid=14:
   firstOdtEntry=20,lastOdtEntry=20:
   [005C002Eh,2]
Queue:
 xcp.pQueue        = 59DF1A
 xcp.QueueSize     = 127
 xcp.QueueLen      = 0
 xcp.QueueRp       = 0
-> START_STOP mode=02h, daq=1
<- 0xFF
-> CC_START_STOP_SYNCH mode=01h
<- 0xFF
-> CC_START_STOP_SYNCH mode=00h
<- 0xFF
-> SET_MTA addr=001C0000h, addrext=00h
<- 0xFF
-> DISCONNECT
<- 0xFF
    """

    for daq, odt, entry, bitoff, size, ext, addr in de0:
        cl.setDaqPtr(daq, odt, entry)
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
    cl.setDaqListMode(0x10, 0, 1, 1, 0)  # , 1)
    print("startStopDaqList #0", cl.startStopDaqList(0x02, 0))
    cl.setDaqListMode(0x10, 1, 2, 1, 0)  # , 2)
    print("startStopDaqList #1", cl.startStopDaqList(0x02, 1))
    cl.startStopSynch(0x01)

    time.sleep(3.0)

    cl.startStopSynch(0x00)


if __name__ == "__main__":
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

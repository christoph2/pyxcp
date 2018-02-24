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

import asyncio
import array
import enum
import logging
import os
import select
import socket
import struct
import sys
import time

import serial
import six

from pyxcp import checksum
from pyxcp import types
from pyxcp import transport
from pyxcp import skloader

## Setup Logger.
level = logging.DEBUG
logger = logging.getLogger("pyXCP")
logger.setLevel(level)
ch = logging.StreamHandler()
ch.setLevel(level)
fmt = '%(asctime)s %(name)-12s %(levelname)-8s %(message)s'
formatter = logging.Formatter(fmt)
ch.setFormatter(formatter)
logger.addHandler(ch)

class FrameSizeError(Exception): pass
class XcpResponseError(Exception): pass

def hexDump(arr):
    return "[{}]".format(' '.join(["{:02x}".format(x) for x in arr]))


##
##  todo: Meta-Programming wg. Persistenz/ Speicherung
##        als XML-File.
##

##
##  1)  Packet for transferring generic control commands    : CTO
##  2)  Packet for transferring synchronous data            : DTO
##

##
##  MAX_CTO     indicates the maximum length of a CTO packet in bytes.
##  MAX_DTO     indicates the maximum length of a DTO packet in bytes.
##

class XCPMessage(object):
    pass

##
##  ... consists of:
##
class XCPHeader(object):
    pass

class XCPPacket(object):
    ##
    ## - Identification Field
    ##      - PID
    ##      - FILL
    ##      - DAQ
    ## - Timestamp Field
    ##      - TIMESTAMP
    ## - Data Field
    ##      - DATA
    ##
    pass

class XCPTail(object):
    pass

##
##  XCPHeaderOnEthernet
##
class XCPHeaderOnEthernet(XCPHeader):
    ##
    ## LEN CTR. - Words im Intel (Little-Endian-Format).
    ##

    """
    Length
    ------
    LEN is the number of bytes in the original XCP Packet.

    Counter
    -------
    The CTR value in the XCP Header allows to detect missing Packets.
    The master has to generate a CTR value when sending a CMD or STIM. The master has to
    increment the CTR value for each new packet sent from master to slave.
    The slave has to generate a (second independent) CTR value when sending a RES, ERR_EV,
    SRM or DAQ. The slave has to increment the CTR value for each new packet sent from slave to
    master.
    """
    pass

DEFAULT_XCP_PORT = 5555

class CANMessageObject(object):

    def __init__(self, canID, dlc, data, extendedAddr = False, rtr = False):
        self.canID = canID
        self.dlc = dlc
        self.data = data
        self.extendedAddr = extendedAddr
        self.rtr = rtr

    def __str__(self):
        addrFmt =  "[{:08X}]  " if self.extendedAddr else "{:04X}  "
        fmt = addrFmt + "{}"
        return fmt.format(self.canID, " ".join(["{:02X}".format(x) for x in self.data]))

    __repr__ = __str__


class MockTransport(object):

    def __init__(self, canID):
        self.parent = None
        self.canID = canID

    def send(self, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, b7 = 0):
        self.message = CANMessageObject(self.canID, 8, bytearray((b0, b1, b2, b3, b4, b5, b6, b7)))
        #print("Sending: {}".format(self.message))

    def receive(self, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, b7 = 0):
        self.message = CANMessageObject(self.canID, 8, bytearray((b0, b1, b2, b3, b4, b5, b6, b7)))
        self.parent.receive(self.message)

    def __str__(self):
        return "[Current Message]: {}".format(self.message)

    __repr__ = __str__



class EthTransport(object):

    MAX_DATAGRAM_SIZE = 512
    HEADER = "<HH"
    HEADER_SIZE = struct.calcsize(HEADER)

    def __init__(self, ipAddress, port = DEFAULT_XCP_PORT, connected = True):
        self.parent = None
        #self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM if connected else socket.SOCK_DGRAM)
        self.logger = logging.getLogger("pyXCP")
        self.connected = connected
        self.counter = 0
        self._address = None
        self._addressExtension = None
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(self.sock, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(0.5)
        self.sock.connect((ipAddress, port))

    def close(self):
        self.sock.close()

    def request(self, cmd, *data):
        print(cmd.name, flush = True)
        header = struct.pack("<HH", len(data) + 1, self.counter)
        frame = header + bytearray([cmd, *data])
        print("-> {}".format(hexDump(frame)), flush = True)
        self.sock.send(frame)

        if self.connected:
            length = struct.unpack("<H", self.sock.recv(2))[0]
            response = self.sock.recv(length + 2)
        else:
            response, server = self.sock.recvfrom(EthTransport.MAX_DATAGRAM_SIZE)

        if len(response) < self.HEADER_SIZE:
            raise FrameSizeError("Frame too short.")
        print("<- {}\n".format(hexDump(response)), flush = True)
        self.packetLen, self.seqNo = struct.unpack(EthTransport.HEADER, response[ : 4])
        self.xcpPDU = response[4 : ]
        if len(self.xcpPDU) != self.packetLen:
            raise FrameSizeError("Size mismatch.")

        pid = types.Response.parse(self.xcpPDU).type
        if pid != 'OK' and pid == 'ERR':
            if cmd.name != 'SYNCH':
                err = types.XcpError.parse(self.xcpPDU[1 : ])
                raise XcpResponseError(err)
        else:
            pass    # Und nu??
        return self.xcpPDU[1 : ]

    #def receive(self, canID, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, b7 = 0):
    #    self.message = CANMessageObject(canID, 8, bytearray((b0, b1, b2, b3, b4, b5, b6, b7)))
    #    self.parent.receive(self.message)

    def __str__(self):
        return "[Current Message]: {}".format(self.message)

    __repr__ = __str__




class XCPClient(object):

    def __init__(self, transport, asyncLoop):
        self.ctr = 0
        self.logger = logging.getLogger("pyXCP")
        self.transport = transport
        self.asyncLoop = asyncLoop
        print("loop style: {}".format(asyncLoop))

    def close(self):
        self.transport.close()

    def sendCRO(self, canID, cmd, ctr, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0):
        """Transfer up to 6 data bytes from master to slave (ECU).
        """
        self.transport.send(canID, cmd, ctr, b0, b1, b2, b3, b4, b5)

    ##
    ## Mandatory Commands.
    ##
    def connect(self):
        response = self.transport.request(types.Command.CONNECT, 0x00)
        result = types.ConnectResponse.parse(response)
        self.maxCto = result.maxCto
        self.maxDto = result.maxDto

        self.supportsPgm = True if result.resource.pgm == 1 else False
        self.supportsStim = True if result.resource.stim == 1 else False
        self.supportsDaq = True if result.resource.daq == 1 else False
        self.supportsCalpag = True if result.resource.calpag == 1 else False
        return result

#        print(result, flush = True)

    def disconnect(self):
        response = self.transport.request(types.Command.DISCONNECT)
        self.asyncLoop.stop()

    def getStatus(self):
        response = self.transport.request(types.Command.GET_STATUS)
        result = types.GetStatusResponse.parse(response)
        print(result, flush = True)

    def synch(self):
        response = self.transport.request(types.Command.SYNCH)

    def getCommModeInfo(self):
        response = self.transport.request(types.Command.GET_COMM_MODE_INFO)
        result = types.GetCommModeInfoResponse.parse(response)
        print(result, flush = True)
        return result

    def getID(self, mode):
        class XcpIdType(enum.IntEnum):
            ASCII_TEXT = 0
            FILENAME = 1
            FILE_AND_PATH = 2
            URL = 3
            FILE_TO_UPLOAD = 4
        response = self.transport.request(types.Command.GET_ID, mode)
        result = types.GetIDResponse.parse(response)
        result.length = struct.unpack("<I", response[3 : 7])[0]
        return result

    def setRequest(self, mode, sessionConfigurationId):
        response = self.transport.request(types.Command.SET_REQUEST, mode, sessionConfigurationId >> 8, sessionConfigurationId & 0xff)

    def upload(self, length):
        response = self.transport.request(types.Command.UPLOAD, length)
        return response

    def shortUpload(self, length):
        response = self.transport.request(types.Command.SHORT_UPLOAD, length)
        return response[1 : ]

    def setMta(self, address):
        addr = struct.pack("<I", address)
        response = self.transport.request(types.Command.SET_MTA, 0, 0, 0, *addr)

    def getSeed(self, first, resource):
        response = self.transport.request(types.Command.GET_SEED, first, resource)
        return response[1], response[1 : ]

    def unlock(self, length, key):
        response = self.transport.request(types.Command.UNLOCK, length, *key)
        return types.ResourceProtectionStatus.parse(response)

    def fetch(self, length): ## TODO: pull
        chunkSize = self.maxDto - 1
        chunks = range(length // chunkSize)
        remaining = length % chunkSize
        result = []
        for idx in chunks:
            data = self.upload(chunkSize)
            result.extend(data)
        if remaining:
            data = self.upload(remaining)
            result.extend(data)
        return result

    def buildChecksum(self, blocksize):
        bs = struct.pack("<I", blocksize)
        response = self.transport.request(types.Command.BUILD_CHECKSUM, 0, 0, 0, *bs)
        return types.BuildChecksumResponse.parse(response)

    def transportLayerCommand(self, subCommand, *data):
        response = self.transport.request(types.Command.TRANSPORT_LAYER_CMD, subCommand, *data)
        return response

    def userCommand(self, subCommand, *data):
        response = self.transport.request(types.Command.USER_CMD, subCommand, *data)
        return response

    def download(self, *data):
        length = len(data)
        response = self.transport.request(types.Command.DOWNLOAD, length, *data)
        return response

    def downloadNext(self, *data):
        length = len(data)
        response = self.transport.request(types.Command.DOWNLOAD_NEXT, length, *data)
        return response

    def downloadMax(self, *data):
        response = self.transport.request(types.Command.DOWNLOAD_MAX, *data)
        return response

    def shortDownload(self, address, addressExt, *data):
        length = len(data)
        addr = struct.pack("<I", address)
        response = self.transport.request(types.Command.SHORT_DOWNLOAD, length, 0, addressExt, *addr, *data)
        return response

    def modifyBits(self, shiftValue, andMask, xorMask):
        # A = ( (A) & ((~((dword)(((word)~MA)<<S))) )^((dword)(MX<<S)) )
        am = struct.pack("<H", andMask)
        xm = struct.pack("<H", xorMask)
        response = self.transport.request(types.Command.MODIFY_BITS, shiftValue, *am, *xm)
        return response

    ##
    ## Page Switching Commands (PAG)
    ##
    def setCalPage(self, mode, logicalDataSegment, logicalDataPage):
        response = self.transport.request(types.Command.SET_CAL_PAGE, mode, logicalDataSegment, logicalDataPage)
        return response

    def getCalPage(self, mode, logicalDataSegment):
        response = self.transport.request(types.Command.GET_CAL_PAGE, mode, logicalDataSegment)
        return response

    def getPagProcessorInfo(self):
        response = self.transport.request(types.Command.GET_PAG_PROCESSOR_INFO)
        return types.GetPagProcessorInfoResponse.parse(response)

    def getSegmentInfo(self, mode, segmentNumber, segmentInfo, mappingIndex):
        response = self.transport.request(types.Command.GET_SEGMENT_INFO, mode, segmentNumber, segmentInfo, mappingIndex)
        if mode == 0:
            return types.GetSegmentInfoMode0Response.parse(response)
        elif mode == 1:
            return types.GetSegmentInfoMode1Response.parse(response)
        elif mode == 2:
            return types.GetSegmentInfoMode2Response.parse(response)

    def getPageInfo(self, segmentNumber, pageNumber):
        response = self.transport.request(types.Command.GET_PAGE_INFO, 0, pageNumber)
        return (types.PageProperties.parse(response[1]), response[2])

    def setSegmentMode(self, mode, segmentNumber):
        response = self.transport.request(types.Command.SET_SEGMENT_MODE, mode, segmentNumber)
        return response

    def getSegmentMode(self, segmentNumber):
        response = self.transport.request(types.Command.GET_SEGMENT_MODE, 0, segmentNumber)
        return response[2]

    def copyCalPage(self, srcSegment, srcPage, dstSegment, dstPage):
        response = self.transport.request(types.Command.COPY_CAL_PAGE, srcSegment, srcPage, dstSegment, dstPage)
        return response

    ##
    ## DAQ
    ##
    def clearDaqList(self, daqListNumber):
        daqList = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.CLEAR_DAQ_LIST, 0, *daqList)
        return response

    def setDaqPtr(self, daqListNumber, odtNumber, odtEntryNumber):
        daqList = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.SET_DAQ_PTR, 0, *daqList, odtNumber, odtEntryNumber)
        return response

    def writeDaq(self, bitOffset, entrySize, addressExt, address):
        addr = struct.pack("<I", address)
        response = self.transport.request(types.Command.WRITE_DAQ, 0, bitOffset, entrySize, addressExt, *addr)
        return response

    def setDaqListMode(self, mode, daqListNumber, eventChannelNumber, prescaler, priority):
        dln = struct.pack("<I", daqListNumber)
        ecn = struct.pack("<I", eventChannelNumber)
        response = self.transport.request(types.Command.SET_DAQ_LIST_MODE, mode, *dln, *ecn, prescaler, priority)
        return response

    def getDaqListMode(self, daqListNumber):
        dln = struct.pack("<I", daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_LIST_MODE, 0, *dln)
        return types.GetDaqListModeResponse.parse(response)

    def startStopDaqList(self, mode, daqListNumber):
        dln = struct.pack("<I", daqListNumber)
        response = self.transport.request(types.Command.START_STOP_DAQ_LIST, mode, *dln)
        return response

    def startStopSynch(self, mode):
        response = self.transport.request(types.Command.START_STOP_SYNCH, mode)
        return response

    ## optional.
    def getDaqClock(self):
        response = self.transport.request(types.Command.GET_DAQ_CLOCK)
        result = types.GetDaqClockResponse.parse(response)
        return result.timestamp

    def readDaq(self):
        response = self.transport.request(types.Command.READ_DAQ)
        return types.ReadDaqResponse.parse(response)

    def getDaqProcessorInfo(self):
        response = self.transport.request(types.Command.GET_DAQ_PROCESSOR_INFO)
        return types.GetDaqProcessorInfoResponse.parse(response)

    def getDaqResolutionInfo(self):
        response = self.transport.request(types.Command.GET_DAQ_RESOLUTION_INFO)
        return types.GetDaqResolutionInfoResponse.parse(response)

    def getDaqListInfo(self, daqListNumber):
        dln = struct.pack("<I", daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_LIST_INFO, 0, *dln)
        return types.GetDaqListInfoResponse.parse(response)

    def getEventChannelInfo(self, eventChannelNumber):
        ecn = struct.pack("<I", eventChannelNumber)
        response = self.transport.request(types.Command.GET_DAQ_EVENT_INFO, 0, *ecn)
        return types.GetEventChannelInfoResponse.parse(response)

    # dynamic
    def freeDaq(self):
        response = self.transport.request(types.Command.FREE_DAQ)
        return response

    def allocDaq(self, daqCount):
        dq = struct.pack("<I", daqCount)
        response = self.transport.request(types.Command.ALLOC_DAQ, 0, *dq)
        return response

    def allocOdt(self, daqListNumber, odtCount):
        dln = struct.pack("<I", daqListNumber)
        response = self.transport.request(types.Command.ALLOC_ODT, 0, *dln, odtCount)
        return response

    def allocOdtEntry(self, daqListNumber, odtNumber, odtEntriesCount):
        dln = struct.pack("<I", daqListNumber)
        response = self.transport.request(types.Command.ALLOC_ODT_ENTRY, 0, *dln, odtNumber, odtEntriesCount)
        return response

    ##
    ## PGM
    ##
    def programStart(self):
        response = self.transport.request(types.Command.PROGRAM_START)
        return types.ProgramStartResponse.parse(response)

    def programClear(self, mode, clearRange):
        cr = struct.pack("<I", clearRange)
        response = self.transport.request(types.Command.PROGRAM_CLEAR, mode, 0, 0, *cr)
        # ERR_ACCESS_LOCKED
        return response

    def program(self):
        """
        PROGRAM
        Position Type Description
        0 BYTE Command Code = 0xD0
        1 BYTE Number of data elements [AG] [1..(MAX_CTO-2)/AG]
        2..AG-1 BYTE Used for alignment, only if AG >2
            AG=1: 2..MAX_CTO-2
            AG>1: AG MAX_CTO-AG
        ELEMENT Data elements
        """


def unlock(client, privilege):
    length, seed = client.getSeed(0, privilege)
    print("SEED: ", hexDump(seed), flush = True)
    _, kee = skloader.getKey(b"SeedNKeyXcp.dll", privilege, seed)
    print("KEE:", kee)
    print(client.unlock(len(kee), kee))


def verify(client, addr, length):
    client.setMta(addr)
    cs = client.buildChecksum(length)
    print("CS: {:08X}".format(cs.checksum))
    client.setMta(addr)
    data = client.upload(length)
    cc = checksum.check(data, cs.checksumType)
    print("CS: {:08X}".format(cc))


def test(loop):
    xcpClient = XCPClient(EthTransport('localhost', connected = False), loop)
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

    skloader.quit()


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


def cstest(loop):
    xcpClient = XCPClient(EthTransport('localhost', connected = False), loop)
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

##
##    for _ in range(10):
##        time.sleep(0.250)
##        stop = xcpClient.getDaqClock()
##        print("trueValue: {}".format(timecode(stop - start, resInfo)))
##        print("Timestamp / Diff: {}".format(stop - start))
##

    xcpClient.setMta(0x1C0000)
    xcpClient.disconnect()
    xcpClient.close()

    skloader.quit()


if __name__=='__main__':
    sxi = transport.SxI("COM27", 115200, loglevel = "DEBUG")
    print(sxi._port)
    sxi.disconnect()
    loop = asyncio.get_event_loop()
    #test(loop)
    cstest(loop)
    loop.run_forever()
#    loop.close()

    # CreateNamedPipe = ctypes.windll.kernel32.CreateNamedPipeA
    # CreateNamedPipe(ctypes.c_char_p(br"\\.\pipe\hello"), 3, 7, 255, 1024, 1024, 0, 0)

# "..\_Simulators\XCPSim\XCPsim.exe" -cro1 -dto2 -t1 -gaXCPSIM.A2L

"""
Time    ID  Name    Dir DLC Data    Interpretation  Event Type  Comment
80.427775   1   CMD Tx  2   FF 00   CONNECT mode=0  XCP Frame
80.443270   2   RES Rx  8   FF 1D C0 08 08 00 01 01 Ok:CONNECT resource=1Dh commMode=C0h ctoSize=8 dtoSize=8 protVer=1 transVer=1   XCP Frame
80.443349   1   CMD Tx  1   FB  GET_COMM_MODE_INFO  XCP Frame
80.451251   2   RES Rx  8   FF 1D 01 08 2B 00 00 19 Ok:GET_COMM_MODE_INFO commModeOptional=01h maxBs=43 minSt=0 queueSize=0 driverVersion=25    XCP Frame
80.451370   1   CMD Tx  1   FD  GET_STATUS  XCP Frame
80.451877   2   RES Rx  6   FF 00 1D 08 00 00   Ok:GET_STATUS sessionStatus=00h protectionStatus=1Dh configurationID=0000h  XCP Frame
80.529628   1   CMD Tx  3   F8 00 04    GET_SEED mode=0 res=04h XCP Frame
80.530392   2   RES Rx  8   FF 0A 9B 23 83 58 74 EF Ok:GET_SEED length=10 data=9Bh 23h 83h 58h 74h EFh  XCP Frame
80.530444   1   CMD Tx  3   F8 01 04    GET_SEED mode=1 res=04h XCP Frame
80.531132   2   RES Rx  6   FF 04 3D 50 BF FD   Ok:GET_SEED length=4 data=3Dh 50h BFh FDh   XCP Frame
80.536909   1   CMD Tx  8   F7 09 A5 B6 5F 88 00 00 UNLOCK length=09h key=A5h B6h 5Fh 88h 00h 00h   XCP Frame
80.541223   2   RES Rx  2   FF 1D   Ok:UNLOCK status=1Dh    XCP Frame
80.541504   1   CMD Tx  5   F7 03 00 00 00  UNLOCK length=03h key=00h 00h 00h   XCP Frame
80.547825   2   RES Rx  2   FF 19   Ok:UNLOCK status=19h    XCP Frame
80.549740   1   CMD Tx  1   DA  GET_DAQ_PROCESSOR_INFO  XCP Frame
80.551853   2   RES Rx  8   FF 57 00 00 06 00 00 40 Ok:GET_DAQ_PROCESSOR_INFO prop=57h maxDAQlists=0 evtChan=6 predefDAQlists=0 key=40h XCP Frame
80.551935   1   CMD Tx  1   D9  GET_DAQ_RESOLUTION_INFO XCP Frame
80.554764   2   RES Rx  8   FF 01 06 01 06 44 0A 00 Ok:GET_DAQ_RESOLUTION_INFO granularityODTEntryDAQ=1 maxSizeODTEntryDAQ=6 granularityODTEntrySTIM=1 maxSizeODTEntrySTIM=6 timestampMode=44h timestampTicks=10    XCP Frame
80.557471   1   CMD Tx  4   D7 00 00 00 GET_DAQ_EVENT_INFO eventChannel=0   XCP Frame
80.560827   2   RES Rx  7   FF 04 01 05 00 06 00    Ok:GET_DAQ_EVENT_INFO eventProp=04h maxDAQLists=1 length=5 timeCycle=0 timeUnit=6 priority=00h  XCP Frame
80.560950   1   CMD Tx  2   F5 05   UPLOAD size=5   XCP Frame
80.565015   2   RES Rx  6   FF 4B 65 79 20 54   Ok:UPLOAD data=4Bh 65h 79h 20h 54h  XCP Frame
80.565122   1   CMD Tx  4   D7 00 01 00 GET_DAQ_EVENT_INFO eventChannel=1   XCP Frame
80.568230   2   RES Rx  7   FF 0C 01 05 0A 06 01    Ok:GET_DAQ_EVENT_INFO eventProp=0Ch maxDAQLists=1 length=5 timeCycle=10 timeUnit=6 priority=01h XCP Frame
80.568314   1   CMD Tx  2   F5 05   UPLOAD size=5   XCP Frame
80.582963   2   RES Rx  6   FF 31 30 20 6D 73   Ok:UPLOAD data=31h 30h 20h 6Dh 73h  XCP Frame
80.583556   1   CMD Tx  4   D7 00 02 00 GET_DAQ_EVENT_INFO eventChannel=2   XCP Frame
80.585039   2   RES Rx  7   FF 0C 01 05 64 06 02    Ok:GET_DAQ_EVENT_INFO eventProp=0Ch maxDAQLists=1 length=5 timeCycle=100 timeUnit=6 priority=02h    XCP Frame
80.585099   1   CMD Tx  2   F5 05   UPLOAD size=5   XCP Frame
80.591058   2   RES Rx  6   FF 31 30 30 6D 73   Ok:UPLOAD data=31h 30h 30h 6Dh 73h  XCP Frame
80.591262   1   CMD Tx  4   D7 00 03 00 GET_DAQ_EVENT_INFO eventChannel=3   XCP Frame
80.595005   2   RES Rx  7   FF 0C 01 03 01 06 03    Ok:GET_DAQ_EVENT_INFO eventProp=0Ch maxDAQLists=1 length=3 timeCycle=1 timeUnit=6 priority=03h  XCP Frame
80.595102   1   CMD Tx  2   F5 03   UPLOAD size=3   XCP Frame
80.599369   2   RES Rx  4   FF 31 6D 73 Ok:UPLOAD data=31h 6Dh 73h  XCP Frame
80.599460   1   CMD Tx  4   D7 00 04 00 GET_DAQ_EVENT_INFO eventChannel=4   XCP Frame
80.602631   2   RES Rx  7   FF 0C 01 0F 0A 06 04    Ok:GET_DAQ_EVENT_INFO eventProp=0Ch maxDAQLists=1 length=15 timeCycle=10 timeUnit=6 priority=04h    XCP Frame
80.602706   1   CMD Tx  2   F5 0F   UPLOAD size=15  XCP Frame
80.609165   2   RES Rx  8   FF 46 69 6C 74 65 72 42 Ok:UPLOAD data=46h 69h 6Ch 74h 65h 72h 42h  XCP Frame
80.613593   2   RES Rx  8   FF 79 70 61 73 73 44 61 Ok:UPLOAD data=79h 70h 61h 73h 73h 44h 61h  XCP Frame
80.618701   2   RES Rx  2   FF 71   Ok:UPLOAD data=71h  XCP Frame
80.618823   1   CMD Tx  4   D7 00 05 00 GET_DAQ_EVENT_INFO eventChannel=5   XCP Frame
80.621267   2   RES Rx  7   FF 08 01 10 0A 06 05    Ok:GET_DAQ_EVENT_INFO eventProp=08h maxDAQLists=1 length=16 timeCycle=10 timeUnit=6 priority=05h    XCP Frame
80.621340   1   CMD Tx  2   F5 10   UPLOAD size=16  XCP Frame
80.628657   2   RES Rx  8   FF 46 69 6C 74 65 72 42 Ok:UPLOAD data=46h 69h 6Ch 74h 65h 72h 42h  XCP Frame
80.633416   2   RES Rx  8   FF 79 70 61 73 73 53 74 Ok:UPLOAD data=79h 70h 61h 73h 73h 53h 74h  XCP Frame
80.637298   2   RES Rx  3   FF 69 6D    Ok:UPLOAD data=69h 6Dh  XCP Frame
80.679744   1   CMD Tx  3   F8 00 01    GET_SEED mode=0 res=01h XCP Frame
80.682607   2   RES Rx  8   FF 0A E1 D5 70 94 6F 93 Ok:GET_SEED length=10 data=E1h D5h 70h 94h 6Fh 93h  XCP Frame
80.682701   1   CMD Tx  3   F8 01 01    GET_SEED mode=1 res=01h XCP Frame
80.685035   2   RES Rx  6   FF 04 18 C9 60 D4   Ok:GET_SEED length=4 data=18h C9h 60h D4h   XCP Frame
80.691321   1   CMD Tx  8   F7 09 A8 B7 7B 96 00 00 UNLOCK length=09h key=A8h B7h 7Bh 96h 00h 00h   XCP Frame
80.693500   2   RES Rx  2   FF 19   Ok:UNLOCK status=19h    XCP Frame
80.693608   1   CMD Tx  5   F7 03 00 00 00  UNLOCK length=03h key=00h 00h 00h   XCP Frame
80.696823   2   RES Rx  2   FF 18   Ok:UNLOCK status=18h    XCP Frame
80.696895   1   CMD Tx  4   EB 83 00 00 SET_CAL_PAGE mode=83h segment=0 page=0  XCP Frame
80.711278   2   RES Rx  1   FF  Ok:SET_CAL_PAGE XCP Frame
80.711538   1   CMD Tx  8   F6 00 00 00 00 00 1C 00 SET_MTA addrext=0 addr=001C0000h    XCP Frame
80.716912   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
80.717065   1   CMD Tx  8   F3 00 00 00 86 12 00 00 BUILD_CHECKSUM size=4742    XCP Frame
80.915503   2   RES Rx  8   FF 08 18 C9 CC E6 00 00 Ok:BUILD_CHECKSUM type=8 result=0000E6CCh   XCP Frame
94.490923   1   CMD Tx  8   F6 00 00 00 00 00 1C 00 SET_MTA addrext=0 addr=001C0000h    XCP Frame
94.493553   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.493664   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.497106   2   RES Rx  8   FF 08 18 C9 6F C2 00 00 Ok:BUILD_CHECKSUM type=8 result=0000C26Fh   XCP Frame
94.497211   1   CMD Tx  8   F6 00 00 00 00 00 1C 00 SET_MTA addrext=0 addr=001C0000h    XCP Frame
94.497623   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.497686   1   CMD Tx  2   F5 80   UPLOAD size=128 XCP Frame
94.505427   2   RES Rx  8   FF AA AA 00 00 44 65 66 Ok:UPLOAD data=AAh AAh 00h 00h 44h 65h 66h  XCP Frame
94.506844   2   RES Rx  8   FF 61 75 6C 74 00 00 00 Ok:UPLOAD data=61h 75h 6Ch 74h 00h 00h 00h  XCP Frame
94.509524   2   RES Rx  8   FF 00 00 00 00 00 00 00 Ok:UPLOAD data=00h 00h 00h 00h 00h 00h 00h  XCP Frame
94.510829   2   RES Rx  8   FF 00 00 00 00 00 00 00 Ok:UPLOAD data=00h 00h 00h 00h 00h 00h 00h  XCP Frame
94.512098   2   RES Rx  8   FF 00 00 00 00 00 00 00 Ok:UPLOAD data=00h 00h 00h 00h 00h 00h 00h  XCP Frame
94.513352   2   RES Rx  8   FF 00 00 00 80 3F 00 00 Ok:UPLOAD data=00h 00h 00h 80h 3Fh 00h 00h  XCP Frame
94.514605   2   RES Rx  8   FF A0 40 00 00 C0 40 00 Ok:UPLOAD data=A0h 40h 00h 00h C0h 40h 00h  XCP Frame
94.515919   2   RES Rx  8   FF 00 C8 42 00 00 00 00 Ok:UPLOAD data=00h C8h 42h 00h 00h 00h 00h  XCP Frame
94.517728   2   RES Rx  8   FF 00 00 00 00 00 00 32 Ok:UPLOAD data=00h 00h 00h 00h 00h 00h 32h  XCP Frame
94.519077   2   RES Rx  8   FF 01 00 00 20 41 00 00 Ok:UPLOAD data=01h 00h 00h 20h 41h 00h 00h  XCP Frame
94.520330   2   RES Rx  8   FF C0 40 00 00 C8 42 00 Ok:UPLOAD data=C0h 40h 00h 00h C8h 42h 00h  XCP Frame
94.521588   2   RES Rx  8   FF 00 20 41 00 00 20 41 Ok:UPLOAD data=00h 20h 41h 00h 00h 20h 41h  XCP Frame
94.522855   2   RES Rx  8   FF 01 00 02 03 00 00 00 Ok:UPLOAD data=01h 00h 02h 03h 00h 00h 00h  XCP Frame
94.531281   2   RES Rx  8   FF 00 00 00 14 40 00 00 Ok:UPLOAD data=00h 00h 00h 14h 40h 00h 00h  XCP Frame
94.532637   2   RES Rx  8   FF 00 00 00 00 18 40 00 Ok:UPLOAD data=00h 00h 00h 00h 18h 40h 00h  XCP Frame
94.533944   2   RES Rx  8   FF 00 00 00 00 00 F0 3F Ok:UPLOAD data=00h 00h 00h 00h 00h F0h 3Fh  XCP Frame
94.535210   2   RES Rx  8   FF 00 00 00 00 00 00 F0 Ok:UPLOAD data=00h 00h 00h 00h 00h 00h F0h  XCP Frame
94.536500   2   RES Rx  8   FF 3F 00 00 00 00 00 00 Ok:UPLOAD data=3Fh 00h 00h 00h 00h 00h 00h  XCP Frame
94.537683   2   RES Rx  3   FF F0 3F    Ok:UPLOAD data=F0h 3Fh  XCP Frame
94.537829   1   CMD Tx  8   F6 00 00 00 80 00 1C 00 SET_MTA addrext=0 addr=001C0080h    XCP Frame
94.538228   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.538272   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.547640   2   RES Rx  8   FF 08 3F 00 3A 8F 00 00 Ok:BUILD_CHECKSUM type=8 result=00008F3Ah   XCP Frame
94.547800   1   CMD Tx  8   F6 00 00 00 00 01 1C 00 SET_MTA addrext=0 addr=001C0100h    XCP Frame
94.548224   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.548253   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.561704   2   RES Rx  8   FF 08 3F 00 73 12 00 00 Ok:BUILD_CHECKSUM type=8 result=00001273h   XCP Frame
94.561833   1   CMD Tx  8   F6 00 00 00 80 01 1C 00 SET_MTA addrext=0 addr=001C0180h    XCP Frame
94.565248   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.565299   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.567562   2   RES Rx  8   FF 08 3F 00 C0 36 00 00 Ok:BUILD_CHECKSUM type=8 result=000036C0h   XCP Frame
94.567699   1   CMD Tx  8   F6 00 00 00 00 02 1C 00 SET_MTA addrext=0 addr=001C0200h    XCP Frame
94.568108   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.568153   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.577686   2   RES Rx  8   FF 08 3F 00 30 81 00 00 Ok:BUILD_CHECKSUM type=8 result=00008130h   XCP Frame
94.577826   1   CMD Tx  8   F6 00 00 00 80 02 1C 00 SET_MTA addrext=0 addr=001C0280h    XCP Frame
94.578271   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.578316   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.590687   2   RES Rx  8   FF 08 3F 00 C2 5D 00 00 Ok:BUILD_CHECKSUM type=8 result=00005DC2h   XCP Frame
94.590887   1   CMD Tx  8   F6 00 00 00 00 03 1C 00 SET_MTA addrext=0 addr=001C0300h    XCP Frame
94.605686   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.605768   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.627682   2   RES Rx  8   FF 08 3F 00 B0 2C 00 00 Ok:BUILD_CHECKSUM type=8 result=00002CB0h   XCP Frame
94.627812   1   CMD Tx  8   F6 00 00 00 80 03 1C 00 SET_MTA addrext=0 addr=001C0380h    XCP Frame
94.637004   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.637150   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.648400   2   RES Rx  8   FF 08 3F 00 CA C5 00 00 Ok:BUILD_CHECKSUM type=8 result=0000C5CAh   XCP Frame
94.648534   1   CMD Tx  8   F6 00 00 00 00 04 1C 00 SET_MTA addrext=0 addr=001C0400h    XCP Frame
94.653078   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.653144   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.661472   2   RES Rx  8   FF 08 3F 00 84 AB 00 00 Ok:BUILD_CHECKSUM type=8 result=0000AB84h   XCP Frame
94.661628   1   CMD Tx  8   F6 00 00 00 80 04 1C 00 SET_MTA addrext=0 addr=001C0480h    XCP Frame
94.678797   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.678912   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.687986   2   RES Rx  8   FF 08 3F 00 53 23 00 00 Ok:BUILD_CHECKSUM type=8 result=00002353h   XCP Frame
94.688126   1   CMD Tx  8   F6 00 00 00 00 05 1C 00 SET_MTA addrext=0 addr=001C0500h    XCP Frame
94.690081   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.690153   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.698210   2   RES Rx  8   FF 08 3F 00 84 AB 00 00 Ok:BUILD_CHECKSUM type=8 result=0000AB84h   XCP Frame
94.698373   1   CMD Tx  8   F6 00 00 00 80 05 1C 00 SET_MTA addrext=0 addr=001C0580h    XCP Frame
94.700151   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.700222   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.716032   2   RES Rx  8   FF 08 3F 00 0C 20 00 00 Ok:BUILD_CHECKSUM type=8 result=0000200Ch   XCP Frame
94.716242   1   CMD Tx  8   F6 00 00 00 00 06 1C 00 SET_MTA addrext=0 addr=001C0600h    XCP Frame
94.733790   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.733873   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.749732   2   RES Rx  8   FF 08 3F 00 7D 4A 00 00 Ok:BUILD_CHECKSUM type=8 result=00004A7Dh   XCP Frame
94.750311   1   CMD Tx  8   F6 00 00 00 80 06 1C 00 SET_MTA addrext=0 addr=001C0680h    XCP Frame
94.767756   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.767836   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.801964   2   RES Rx  8   FF 08 3F 00 07 E4 00 00 Ok:BUILD_CHECKSUM type=8 result=0000E407h   XCP Frame
94.802090   1   CMD Tx  8   F6 00 00 00 00 07 1C 00 SET_MTA addrext=0 addr=001C0700h    XCP Frame
94.804479   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.804645   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.807107   2   RES Rx  8   FF 08 3F 00 BF 38 00 00 Ok:BUILD_CHECKSUM type=8 result=000038BFh   XCP Frame
94.807234   1   CMD Tx  8   F6 00 00 00 80 07 1C 00 SET_MTA addrext=0 addr=001C0780h    XCP Frame
94.809185   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.809354   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.817128   2   RES Rx  8   FF 08 3F 00 DF 35 00 00 Ok:BUILD_CHECKSUM type=8 result=000035DFh   XCP Frame
94.817242   1   CMD Tx  8   F6 00 00 00 00 08 1C 00 SET_MTA addrext=0 addr=001C0800h    XCP Frame
94.819506   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.819569   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.828096   2   RES Rx  8   FF 08 3F 00 31 DB 00 00 Ok:BUILD_CHECKSUM type=8 result=0000DB31h   XCP Frame
94.828238   1   CMD Tx  8   F6 00 00 00 80 08 1C 00 SET_MTA addrext=0 addr=001C0880h    XCP Frame
94.830450   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.830542   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.837975   2   RES Rx  8   FF 08 3F 00 1D 5C 00 00 Ok:BUILD_CHECKSUM type=8 result=00005C1Dh   XCP Frame
94.838097   1   CMD Tx  8   F6 00 00 00 00 09 1C 00 SET_MTA addrext=0 addr=001C0900h    XCP Frame
94.844189   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.844297   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.847699   2   RES Rx  8   FF 08 3F 00 49 D1 00 00 Ok:BUILD_CHECKSUM type=8 result=0000D149h   XCP Frame
94.848319   1   CMD Tx  8   F6 00 00 00 80 09 1C 00 SET_MTA addrext=0 addr=001C0980h    XCP Frame
94.855940   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.856015   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.867760   2   RES Rx  8   FF 08 3F 00 7D 6E 00 00 Ok:BUILD_CHECKSUM type=8 result=00006E7Dh   XCP Frame
94.867876   1   CMD Tx  8   F6 00 00 00 00 0A 1C 00 SET_MTA addrext=0 addr=001C0A00h    XCP Frame
94.869460   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.869508   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.878900   2   RES Rx  8   FF 08 3F 00 AB 45 00 00 Ok:BUILD_CHECKSUM type=8 result=000045ABh   XCP Frame
94.879022   1   CMD Tx  8   F6 00 00 00 80 0A 1C 00 SET_MTA addrext=0 addr=001C0A80h    XCP Frame
94.880903   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.880965   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.887839   2   RES Rx  8   FF 08 3F 00 3E 7C 00 00 Ok:BUILD_CHECKSUM type=8 result=00007C3Eh   XCP Frame
94.887958   1   CMD Tx  8   F6 00 00 00 00 0B 1C 00 SET_MTA addrext=0 addr=001C0B00h    XCP Frame
94.889887   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.889947   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.897142   2   RES Rx  8   FF 08 3F 00 BD 71 00 00 Ok:BUILD_CHECKSUM type=8 result=000071BDh   XCP Frame
94.897258   1   CMD Tx  8   F6 00 00 00 80 0B 1C 00 SET_MTA addrext=0 addr=001C0B80h    XCP Frame
94.899279   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.899327   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.907093   2   RES Rx  8   FF 08 3F 00 89 3E 00 00 Ok:BUILD_CHECKSUM type=8 result=00003E89h   XCP Frame
94.907201   1   CMD Tx  8   F6 00 00 00 00 0C 1C 00 SET_MTA addrext=0 addr=001C0C00h    XCP Frame
94.910320   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.910392   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.921748   2   RES Rx  8   FF 08 3F 00 DE DB 00 00 Ok:BUILD_CHECKSUM type=8 result=0000DBDEh   XCP Frame
94.921907   1   CMD Tx  8   F6 00 00 00 80 0C 1C 00 SET_MTA addrext=0 addr=001C0C80h    XCP Frame
94.923349   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.923403   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.927162   2   RES Rx  8   FF 08 3F 00 53 82 00 00 Ok:BUILD_CHECKSUM type=8 result=00008253h   XCP Frame
94.927312   1   CMD Tx  8   F6 00 00 00 00 0D 1C 00 SET_MTA addrext=0 addr=001C0D00h    XCP Frame
94.927989   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.928276   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.938146   2   RES Rx  8   FF 08 3F 00 0A F0 00 00 Ok:BUILD_CHECKSUM type=8 result=0000F00Ah   XCP Frame
94.938272   1   CMD Tx  8   F6 00 00 00 80 0D 1C 00 SET_MTA addrext=0 addr=001C0D80h    XCP Frame
94.941094   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.941189   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.948152   2   RES Rx  8   FF 08 3F 00 0A F0 00 00 Ok:BUILD_CHECKSUM type=8 result=0000F00Ah   XCP Frame
94.948280   1   CMD Tx  8   F6 00 00 00 00 0E 1C 00 SET_MTA addrext=0 addr=001C0E00h    XCP Frame
94.949697   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.949761   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.957303   2   RES Rx  8   FF 08 3F 00 0A F0 00 00 Ok:BUILD_CHECKSUM type=8 result=0000F00Ah   XCP Frame
94.957445   1   CMD Tx  8   F6 00 00 00 80 0E 1C 00 SET_MTA addrext=0 addr=001C0E80h    XCP Frame
94.961016   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.961096   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.967153   2   RES Rx  8   FF 08 3F 00 0A F0 00 00 Ok:BUILD_CHECKSUM type=8 result=0000F00Ah   XCP Frame
94.967266   1   CMD Tx  8   F6 00 00 00 00 0F 1C 00 SET_MTA addrext=0 addr=001C0F00h    XCP Frame
94.969422   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.969479   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.979220   2   RES Rx  8   FF 08 3F 00 0A F0 00 00 Ok:BUILD_CHECKSUM type=8 result=0000F00Ah   XCP Frame
94.979371   1   CMD Tx  8   F6 00 00 00 80 0F 1C 00 SET_MTA addrext=0 addr=001C0F80h    XCP Frame
94.984152   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.984228   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.987319   2   RES Rx  8   FF 08 3F 00 0A F0 00 00 Ok:BUILD_CHECKSUM type=8 result=0000F00Ah   XCP Frame
94.987454   1   CMD Tx  8   F6 00 00 00 00 10 1C 00 SET_MTA addrext=0 addr=001C1000h    XCP Frame
94.989255   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
94.989311   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
94.999112   2   RES Rx  8   FF 08 3F 00 F8 3E 00 00 Ok:BUILD_CHECKSUM type=8 result=00003EF8h   XCP Frame
94.999242   1   CMD Tx  8   F6 00 00 00 80 10 1C 00 SET_MTA addrext=0 addr=001C1080h    XCP Frame
95.001965   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
95.002042   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
95.007490   2   RES Rx  8   FF 08 3F 00 80 AC 00 00 Ok:BUILD_CHECKSUM type=8 result=0000AC80h   XCP Frame
95.007624   1   CMD Tx  8   F6 00 00 00 00 11 1C 00 SET_MTA addrext=0 addr=001C1100h    XCP Frame
95.011071   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
95.011155   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
95.017704   2   RES Rx  8   FF 08 3F 00 90 D4 00 00 Ok:BUILD_CHECKSUM type=8 result=0000D490h   XCP Frame
95.018032   1   CMD Tx  8   F6 00 00 00 80 11 1C 00 SET_MTA addrext=0 addr=001C1180h    XCP Frame
95.020768   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
95.020863   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
95.028312   2   RES Rx  8   FF 08 3F 00 C3 BD 00 00 Ok:BUILD_CHECKSUM type=8 result=0000BDC3h   XCP Frame
95.028500   1   CMD Tx  8   F6 00 00 00 00 12 1C 00 SET_MTA addrext=0 addr=001C1200h    XCP Frame
95.029943   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
95.030008   1   CMD Tx  8   F3 00 00 00 80 00 00 00 BUILD_CHECKSUM size=128 XCP Frame
95.037310   2   RES Rx  8   FF 08 3F 00 D1 F2 00 00 Ok:BUILD_CHECKSUM type=8 result=0000F2D1h   XCP Frame
95.037425   1   CMD Tx  8   F6 00 00 00 80 12 1C 00 SET_MTA addrext=0 addr=001C1280h    XCP Frame
95.039459   2   RES Rx  1   FF  Ok:SET_MTA  XCP Frame
95.039521   1   CMD Tx  8   F3 00 00 00 06 00 00 00 BUILD_CHECKSUM size=6   XCP Frame
95.049285   2   RES Rx  8   FF 08 3F 00 05 E8 00 00 Ok:BUILD_CHECKSUM type=8 result=0000E805h   XCP Frame
237.809619  2   DAQ Rx  8   FF 00 00 00 00 00 00 00     XCP Frame
238.813643  2   EV  Rx  2   FD 00   EV event=00h    XCP Frame
238.818669  2   EV  Rx  6   FD FE 01 02 03 04   EV event=FEh code=0201h XCP Frame
251.178669  2   EV  Rx  2   FD 01   EV event=01h    XCP Frame
251.180475  2   EV  Rx  6   FD FE 01 02 03 04   EV event=FEh code=0201h XCP Frame
251.181134  2   SERV    Rx  8   FC 01 54 68 69 73 20 69 SERV Service request=54h    XCP Frame
251.181157  2       Rx  0       SERV Service request=00h    XCP Frame
255.747712  2   SERV    Rx  8   FC 01 54 68 69 73 20 69 SERV Service request=54h    XCP Frame
255.747742  2       Rx  0       SERV Service request=00h    XCP Frame

"""

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

import enum
import logging
import os
import select
import struct
import sys
import traceback

from pyxcp import checksum
from pyxcp import types
from pyxcp import transport

from pyxcp.timing import Timing
from pyxcp.utils import setpriority

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

    def receive(self, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, b7 = 0):
        self.message = CANMessageObject(self.canID, 8, bytearray((b0, b1, b2, b3, b4, b5, b6, b7)))
        self.parent.receive(self.message)

    def __str__(self):
        return "[Current Message]: {}".format(self.message)

    __repr__ = __str__


class Master(object):

    def __init__(self, transport):
        self.ctr = 0
        self.succeeded = True
        self.logger = logging.getLogger("pyXCP")
        self.transport = transport

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.close()
        if exc_type is None:
            return
        else:
            self.succeeded = False
            #print("=" * 79)
            #print("Exception while in Context-Manager:\n")
            self.logger.error(''.join(traceback.format_exception(exc_type, exc_val, exc_tb)))
            #print("=" * 79)
        return True

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
        """Build up connection to an XCP slave.

        Before the actual XCP traffic starts a connection is required.

        Parameters
        ----------
        None

        Returns
        -------
        `types.ConnectResponse`
            Describes fundamental client properties.

        Note
        ----
        Every XCP slave supports at most one connection,
        more attempts to connect are silently ignored.

        """
        response = self.transport.request(types.Command.CONNECT, 0x00)
        result = types.ConnectResponse.parse(response)
        self.maxCto = result.maxCto
        self.maxDto = result.maxDto

        self.supportsPgm = True if result.resource.pgm == 1 else False
        self.supportsStim = True if result.resource.stim == 1 else False
        self.supportsDaq = True if result.resource.daq == 1 else False
        self.supportsCalpag = True if result.resource.calpag == 1 else False
        return result

    def disconnect(self):
        """Releases the connection to the XCP slave.

        Thereafter, no further communication with the slave is possible (besides `connect`).

        Parameters
        ----------
        None

        Returns
        -------
        None

        """
        response = self.transport.request(types.Command.DISCONNECT)

    def getStatus(self):
        response = self.transport.request(types.Command.GET_STATUS)
        result = types.GetStatusResponse.parse(response)
        return result

    def synch(self):
        response = self.transport.request(types.Command.SYNCH)

    def getCommModeInfo(self):
        response = self.transport.request(types.Command.GET_COMM_MODE_INFO)
        result = types.GetCommModeInfoResponse.parse(response)
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
        chunkSize = self.maxCto - 1
        chunks = range(length // chunkSize)
        remaining = length % chunkSize
        result = []
        for idx in chunks:
            data = self.upload(chunkSize)
            result.extend(data)
        if remaining:
            data = self.upload(remaining)
            result.extend(data)
        return bytes(result)

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
        response = self.transport.request(types.Command.WRITE_DAQ, bitOffset, entrySize, addressExt, *addr)
        return response

    def setDaqListMode(self, mode, daqListNumber, eventChannelNumber, prescaler, priority):
        dln = struct.pack("<H", daqListNumber)
        ecn = struct.pack("<H", eventChannelNumber)
        response = self.transport.request(types.Command.SET_DAQ_LIST_MODE, mode, *dln, *ecn, prescaler, priority)
        return response

    def getDaqListMode(self, daqListNumber):
        dln = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_LIST_MODE, 0, *dln)
        return types.GetDaqListModeResponse.parse(response)

    def startStopDaqList(self, mode, daqListNumber):
        dln = struct.pack("<H", daqListNumber)
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
        dln = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.GET_DAQ_LIST_INFO, 0, *dln)
        return types.GetDaqListInfoResponse.parse(response)

    def getEventChannelInfo(self, eventChannelNumber):
        ecn = struct.pack("<H", eventChannelNumber)
        response = self.transport.request(types.Command.GET_DAQ_EVENT_INFO, 0, *ecn)
        return types.GetEventChannelInfoResponse.parse(response)

    # dynamic
    def freeDaq(self):
        response = self.transport.request(types.Command.FREE_DAQ)
        return response

    def allocDaq(self, daqCount):
        dq = struct.pack("<H", daqCount)
        response = self.transport.request(types.Command.ALLOC_DAQ, 0, *dq)
        return response

    def allocOdt(self, daqListNumber, odtCount):
        dln = struct.pack("<H", daqListNumber)
        response = self.transport.request(types.Command.ALLOC_ODT, 0, *dln, odtCount)
        return response

    def allocOdtEntry(self, daqListNumber, odtNumber, odtEntriesCount):
        dln = struct.pack("<H", daqListNumber)
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
    #print("SEED: ", hexDump(seed), flush = True)
    _, kee = dllif.getKey(b"SeedNKeyXcp.dll", privilege, seed)
    print("KEE:", kee)
#    res = client.unlock(len(kee), kee)
    #print(res)


def verify(client, addr, length):
    client.setMta(addr)
    cs = client.buildChecksum(length)
    print("CS: {:08X}".format(cs.checksum))
    client.setMta(addr)
    data = client.upload(length)
    cc = checksum.check(data, cs.checksumType)
    print("CS: {:08X}".format(cc))


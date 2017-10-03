#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__="""
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2017 by Christoph Schueler <cpu12.gems@googlemail.com>

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
import socket
import struct
import sys
import time

import construct
if construct.version < (2, 8):
    print("pyXCP requires at least construct 2.8")
    exit(1)

from construct import Struct, If, Const, Adapter, FlagsEnum, Enum, String, Array, Padding, Tell, Union, HexDump
from construct import Probe, CString, IfThenElse, Pass, Float64l, Int8ul, Construct, this, GreedyBytes, Switch
from construct import OnDemandPointer, Pointer, Byte, GreedyRange, Bytes, Int16ul, Int16sl, Int32ul, Int32sl, Int64ul
from construct import BitStruct, BitsInteger
import six


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


def hexDump(arr):
    return "[{}]".format(' '.join(["{:02x}".format(x) for x in arr]))

class Command(enum.IntEnum):

# class STD(Command):
    ##
    ## Mandantory Commnands.
    ##
    CONNECT                 = 0xFF
    DISCONNECT              = 0xFE
    GET_STATUS              = 0xFD
    SYNCH                   = 0xFC
    ##
    ## Optional Commands.
    ##
    GET_COMM_MODE_INFO      = 0xFB
    GET_ID                  = 0xFA
    SET_REQUEST             = 0xF9
    GET_SEED                = 0xF8
    UNLOCK                  = 0xF7
    SET_MTA                 = 0xF6
    UPLOAD                  = 0xF5
    SHORT_UPLOAD            = 0xF4
    BUILD_CHECKSUM          = 0xF3

    TRANSPORT_LAYER_CMD     = 0xF2
    USER_CMD                = 0xF1

#class CAL:
    ##
    ## Mandantory Commnands.
    ##
    DOWNLOAD                = 0xF0
    ##
    ## Optional Commands.
    ##
    DOWNLOAD_NEXT           = 0xEF
    DOWNLOAD_MAX            = 0xEE
    SHORT_DOWNLOAD          = 0xED
    MODIFY_BITS             = 0xEC

#class PAG:
    ##
    ## Mandantory Commnands.
    ##
    SET_CAL_PAGE            = 0xEB
    GET_CAL_PAGE            = 0xEA
    ##
    ## Optional Commands.
    ##
    GET_PAG_PROCESSOR_INFO  = 0xE9
    GET_SEGMENT_INFO        = 0xE8
    GET_PAGE_INFO           = 0xE7
    SET_SEGMENT_MODE        = 0xE6
    GET_SEGMENT_MODE        = 0xE5
    COPY_CAL_PAGE           = 0xE4

#class DAQ:
    ##
    ## Mandantory Commnands.
    ##
    CLEAR_DAQ_LIST          = 0xE3
    SET_DAQ_PTR             = 0xE2
    WRITE_DAQ               = 0xE1
    SET_DAQ_LIST_MODE       = 0xE0
    GET_DAQ_LIST_MODE       = 0xDF
    START_STOP_DAQ_LIST     = 0xDE
    START_STOP_SYNCH        = 0xDD
    ##
    ## Optional Commands.
    ##
    GET_DAQ_CLOCK           = 0xDC
    READ_DAQ                = 0xDB
    GET_DAQ_PROCESSOR_INFO  = 0xDA
    GET_DAQ_RESOLUTION_INFO = 0xD9
    GET_DAQ_LIST_INFO       = 0xD8
    GET_DAQ_EVENT_INFO      = 0xD7
    FREE_DAQ                = 0xD6
    ALLOC_DAQ               = 0xD5
    ALLOC_ODT               = 0xD4
    ALLOC_ODT_ENTRY         = 0xD3

#class PGM:
    ##
    ## Mandantory Commnands.
    ##
    PROGRAM_START           = 0xD2
    PROGRAM_CLEAR           = 0xD1
    PROGRAM                 = 0xD0
    PROGRAM_RESET           = 0xCF
    ##
    ## Optional Commands.
    ##
    GET_PGM_PROCESSOR_INFO  = 0xCE
    GET_SECTOR_INFO         = 0xCD
    PROGRAM_PREPARE         = 0xCC
    PROGRAM_FORMAT          = 0xCB
    PROGRAM_NEXT            = 0xCA
    PROGRAM_MAX             = 0xC9
    PROGRAM_VERIFY          = 0xC8



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

    def __init__(self):
        self.parent = None

    def send(self, canID, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, b7 = 0):
        self.message = CANMessageObject(canID, 8, bytearray((b0, b1, b2, b3, b4, b5, b6, b7)))
        #print("Sending: {}".format(self.message))

    def receive(self, canID, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, b7 = 0):
        self.message = CANMessageObject(canID, 8, bytearray((b0, b1, b2, b3, b4, b5, b6, b7)))
        self.parent.receive(self.message)

    def __str__(self):
        return "[Current Message]: {}".format(self.message)

    __repr__ = __str__



class UdpTransport(object):

    def __init__(self, ipAddress, port = DEFAULT_XCP_PORT):
        self.parent = None
        #self.sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self.sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.logger = logging.getLogger("pyXCP")
        self.counter = 0
        self._address = None
        self._addressExtension = None
        self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        if hasattr(self.sock, "SO_REUSEPORT"):
            self.sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEPORT, 1)
        self.sock.settimeout(5.0)
        self.sock.connect((ipAddress, port))

    def close(self):
        self.sock.close()

    def send(self, canID, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, b7 = 0):
        self.message = CANMessageObject(canID, 8, bytearray((b0, b1, b2, b3, b4, b5, b6, b7)))
        print("Sending: {}".format(self.message.data))
        hdr = struct.pack("<HH", 8, 0)
        print(hdr)
        self.sock.send(hdr)
        self.sock.send(self.message.data)
        result = self.sock.recv(2)
        print(result)

    def request(self, canID, cmd, *data):
        print(cmd.name)
        header = struct.pack("<HH", len(data) + 1, self.counter)
        frame = header + bytearray([cmd, *data])
        print("-> {}".format(hexDump(frame)))
        self.sock.send(frame)
        length = struct.unpack("<H", self.sock.recv(2))[0]
        response = self.sock.recv(length + 2)
        print("<- {}\n".format(hexDump(response)))
        return response[ 2 : ]

    def receive(self, canID, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0, b6 = 0, b7 = 0):
        self.message = CANMessageObject(canID, 8, bytearray((b0, b1, b2, b3, b4, b5, b6, b7)))
        self.parent.receive(self.message)

    def __str__(self):
        return "[Current Message]: {}".format(self.message)

    __repr__ = __str__


XcpError = Enum(Int8ul,
    ERR_CMD_SYNCH           = 0x00, # Command processor synchronization.                            S0

    ERR_CMD_BUSY            = 0x10, # Command was not executed.                                     S2
    ERR_DAQ_ACTIVE          = 0x11, # Command rejected because DAQ is running.                      S2
    ERR_PGM_ACTIVE          = 0x12, # Command rejected because PGM is running.                      S2

    ERR_CMD_UNKNOWN         = 0x20, # Unknown command or not implemented optional command.          S2
    ERR_CMD_SYNTAX          = 0x21, # Command syntax invalid                                        S2
    ERR_OUT_OF_RANGE        = 0x22, # Command syntax valid but command parameter(s) out of range.   S2
    ERR_WRITE_PROTECTED     = 0x23, # The memory location is write protected.                       S2
    ERR_ACCESS_DENIED       = 0x24, # The memory location is not accessible.                        S2
    ERR_ACCESS_LOCKED       = 0x25, # Access denied, Seed & Key is required                         S2
    ERR_PAGE_NOT_VALID      = 0x26, # Selected page not available                                   S2
    ERR_MODE_NOT_VALID      = 0x27, # Selected page mode not available                              S2
    ERR_SEGMENT_NOT_VALID   = 0x28, # Selected segment not valid                                    S2
    ERR_SEQUENCE            = 0x29, # Sequence error                                                S2
    ERR_DAQ_CONFIG          = 0x2A, # DAQ configuration not valid                                   S2

    ERR_MEMORY_OVERFLOW     = 0x30, # Memory overflow error                                         S2
    ERR_GENERIC             = 0x31, # Generic error.                                                S2
    ERR_VERIFY              = 0x32, # The slave internal program verify routine detects an error.   S3
)

Response = Struct(
    "type" / Enum(Int8ul,
        OK = 0xff,
        ERR = 0xfe,
        EV = 0xfd,
        SERV = 0xfc,
    ),

)

#st = Struct(
#    "type" / Enum(Byte, INT1=1, INT2=2, INT4=3, STRING=4),
#    "data" / Switch(this.type, {
#        "INT1" : Int8ub,
#        "INT2" : Int16ub,
#        "INT4" : Int32ub,
#        "STRING" : String(10),
#    }),
#)

Resource = BitStruct (
    Padding(3),
    "pgm" / BitsInteger(1),
    "stim" / BitsInteger(1),
    "daq" / BitsInteger(1),
    Padding(1),
    "calpag" / BitsInteger(1),
)

CommModeBasic = BitStruct (
    "optional" / BitsInteger(1),    # The OPTIONAL flag indicates whether additional information on supported types
                                    # of Communication mode is available. The master can get that additional
                                    # information with GET_COMM_MODE_INFO
    "slaveBlockMode" / BitsInteger(1),
    Padding(3),
    "addressGranularity" / Enum(BitsInteger(2),
        BYTE = 0,
        WORD = 1,
        DWORD = 2,
        RESERVED = 3,
    ),
    "byteOrder" / Enum(BitsInteger(1),
        INTEL = 0,
        MOTOROLA = 1,
    )
)

ConnectResponse = Struct(
    Const(b'\xff'),
    "resource" / Resource,
    "commModeBasic" / CommModeBasic,
    "maxCto" / Int8ul,
    "maxDto" / Int16ul,
    "protocolLayerVersion" / Int8ul,
    "transportLayerVersion" / Int8ul
)

SessionStatus = BitStruct(
    "resume" / BitsInteger(1),
    "daqRunning" / BitsInteger(1),
    Padding(2),
    "clearDaqRequest" / BitsInteger(1),
    "storeDaqRequest" / BitsInteger(1),
    Padding(1),
    "storeCalRequest" / BitsInteger(1),
)

ResourceProtectionStatus = BitStruct(
    Padding(3),
    "pgm" / BitsInteger(1),
    "stim" / BitsInteger(1),
    "daq" / BitsInteger(1),
    Padding(1),
    "calpag" / BitsInteger(1),
)

GetStatusResponse = Struct(
    Const(b'\xff'),
    "sessionStatus" / SessionStatus,
    "resourceProtectionStatus" / ResourceProtectionStatus,
    "reserved" / Int8ul,
    "sessionConfiguration" / Int16ul,
)

CommModeOptional = BitStruct(
    Padding(6),
    "interleavedMode" / BitsInteger(1),
    "masterBlockMode" / BitsInteger(1),
)

GetCommModeInfoResponse = Struct(
    Const(b'\xff'),
    "reserved" / Int8ul,
    "commModeOptional" / CommModeOptional,
    Int8ul,
    "maxbs" / Int8ul,
    "minSt" / Int8ul,
    "queueSize" / Int8ul,
    "xcpDriverVersionNumber" / Int8ul,
)

GetIDResponse = Struct(
    "mode" / Int8ul,
    "reserved" / Int16ul,
    "length" / Int32ul,
)

SetRequestMode = BitStruct(
    Padding(4),
    "clearDaqReq" / BitsInteger(1),
    "storeDaqReq" / BitsInteger(1),
    Padding(1),
    "storeCalReq" / BitsInteger(1),
)

BuildChecksumResponse = Struct(
    "checksumType" / Enum(Int8ul,
        XCP_ADD_11 = 0x01,
        XCP_ADD_12 = 0x02,
        XCP_ADD_14 = 0x03,
        XCP_ADD_22 = 0x04,
        XCP_ADD_24 = 0x05,
        XCP_ADD_44 = 0x06,

        XCP_CRC_16 = 0x07,
        XCP_CRC_16 = 0x08,
        XCP_CRC_32 = 0x09,

        XCP_USER_DEFINED = 0xFF,
    ),
    "reserved" / Int16ul,
    "checksum" / Int32ul,
)

class XCPClient(object):

    def __init__(self, transport):
        self.ctr = 0
        self.logger = logging.getLogger("pyXCP")
        self.transport = transport

    def close(self):
        self.transport.close()

    def sendCRO(self, canID, cmd, ctr, b0 = 0, b1 = 0, b2 = 0, b3 = 0, b4 = 0, b5 = 0):
        """Transfer up to 6 data bytes from master to slave (ECU).
        """
        self.transport.send(canID, cmd, ctr, b0, b1, b2, b3, b4, b5)

    ##
    ## Mandatory Commands.
    ##
    def connect(self, canID):
        response = self.transport.request(canID, Command.CONNECT, 0x00)
        result = ConnectResponse.parse(response)
        print(result)

    def disconnect(self, canID):
        response = self.transport.request(canID, Command.DISCONNECT)

    def getStatus(self, canID):
        response = self.transport.request(canID, Command.GET_STATUS)
        result = GetStatusResponse.parse(response)
        print(result)

    def synch(self, canID):
        response = self.transport.request(canID, Command.SYNCH)

    def getCommModeInfo(self, canID):
        response = self.transport.request(canID, Command.GET_COMM_MODE_INFO)
        result = GetCommModeInfoResponse.parse(response)
        print(result)
        return result

    def getID(self, canID, mode):
        class XcpIdType(enum.IntEnum):
            ASCII_TEXT = 0
            FILENAME = 1
            FILE_AND_PATH = 2
            URL = 3
            FILE_TO_UPLOAD = 4
        response = self.transport.request(canID, Command.GET_ID, mode)
        result = GetIDResponse.parse(response)
        print(result.length)
        result.length = struct.unpack("<I", response[4:8])[0]
        return result

    def setRequest(self, canID, mode, sessionConfigurationId):
        response = self.transport.request(canID, Command.SET_REQUEST, mode, sessionConfigurationId >> 8, sessionConfigurationId & 0xff)

    def upload(self, canID, length):
        response = self.transport.request(canID, Command.UPLOAD, length)
        return response[1 : ]

    def shortUpload(self, canID, length):
        response = self.transport.request(canID, Command.SHORT_UPLOAD, length)
        return response[1 : ]

    def setMta(self, canID, address):
        addr = struct.pack("<I", address)
        response = self.transport.request(canID, Command.SET_MTA, 0, 0, 0, *addr)


    def getSeed(self, canID, first, resource):
        response = self.transport.request(canID, Command.GET_SEED, first, resource)
        return response

    def fetch(self, canID, length):
        max_dto = 8
        chunkSize = max_dto - 1
        chunks = range(length // chunkSize)
        remaining = length % chunkSize
        result = []
        for idx in chunks:
            data = self.upload(canID, chunkSize)
            result.extend(data)
        if remaining:
            data = self.upload(canID, remaining)
            result.extend(data)
        return result

    def buildChecksum(self, canID, blocksize):
        bs = struct.pack("<I", blocksize)
        response = self.transport.request(canID, Command.BUILD_CHECKSUM, 0, 0, 0, *bs)
        return BuildChecksumResponse.parse(response)

#CALRAM_ADDR  = 0x00E3200C
CALRAM_ADDR  = 0x00E1058
#CALRAM_SIZE  = 0x000001C1
CALRAM_SIZE  = 0x00000E9D

def test():
    xcpClient = XCPClient(UdpTransport('localhost'))
    xcpClient.connect(0x7ba)
    xcpClient.getStatus(0x7ba)
    xcpClient.synch(0x7ba)
    xcpClient.getCommModeInfo(0x7ba)

    result = xcpClient.getID(0x7ba, 0x01)
    xcpClient.upload(0x7ba, result.length)
    #result = xcpClient.getSeed(0x7ba, 0, 1)

    #  name = xcpClient.fetch(0x7ba, result.length)
    #  print(name)
    #xcpClient.setRequest(0x7ba, 0x08, 0x1010)

#    xcpClient.setMta(0x7ba, CALRAM_ADDR)
#    xcpClient.buildChecksum(0x7ba, CALRAM_SIZE)
    #xcpClient.fetch(0x7ba, CALRAM_SIZE)

    xcpClient.disconnect(0x7ba)
    xcpClient.close()

if __name__=='__main__':
    test()



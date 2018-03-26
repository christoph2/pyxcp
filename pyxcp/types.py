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

import construct
if construct.version < (2, 8):
    print("pyXCP requires at least construct 2.8")
    exit(1)

from construct import Struct,  Adapter, FlagsEnum, Enum, Array, Padding, Tell, Union, HexDump
from construct import CString, IfThenElse, Pass, Float64l, Int8ul, Construct, this, GreedyBytes, Switch
from construct import Byte, GreedyRange, Bytes, Int16ul, Int16sl, Int32ul, Int32sl, Int64ul
from construct import BitStruct, BitsInteger, Flag


class FrameSizeError(Exception): pass
class XcpResponseError(Exception): pass
class XcpTimeoutError(Exception): pass

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

ResourceType = BitStruct (
    Padding(3),
    "pgm" / Flag,
    "stim" / Flag,
    "daq" / Flag,
    Padding(1),
    "calpag" / Flag,
)

CommModeBasic = BitStruct (
    "optional" / Flag,    # The OPTIONAL flag indicates whether additional information on supported types
                                    # of Communication mode is available. The master can get that additional
                                    # information with GET_COMM_MODE_INFO
    "slaveBlockMode" / Flag,
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
    "resource" / ResourceType,
    "commModeBasic" / CommModeBasic,
    "maxCto" / Int8ul,
    "maxDto" / Int16ul,
    "protocolLayerVersion" / Int8ul,
    "transportLayerVersion" / Int8ul
)

SessionStatus = BitStruct(
    "resume" / Flag,
    "daqRunning" / Flag,
    Padding(2),
    "clearDaqRequest" / Flag,
    "storeDaqRequest" / Flag,
    Padding(1),
    "storeCalRequest" / Flag,
)

GetStatusResponse = Struct(
    "sessionStatus" / SessionStatus,
    "resourceProtectionStatus" / ResourceType,
    "reserved" / Int8ul,
    "sessionConfiguration" / Int16ul,
)

CommModeOptional = BitStruct(
    Padding(6),
    "interleavedMode" / Flag,
    "masterBlockMode" / Flag,
)

GetCommModeInfoResponse = Struct(
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
    "clearDaqReq" / Flag,
    "storeDaqReq" / Flag,
    Padding(1),
    "storeCalReq" / Flag,
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
        XCP_CRC_16_CITT = 0x08,
        XCP_CRC_32 = 0x09,
        XCP_USER_DEFINED = 0xFF,
    ),
    "reserved" / Int16ul,
    "checksum" / Int32ul,
)

SetCalPageMode = BitStruct(
    "all" / Flag,
    Padding(5),
    "xcp" / Flag,
    "ecu" / Flag,
)

GetPagProcessorInfoResponse = Struct(
    "maxSegment" / Int8ul,
    "pagProperties" / Int8ul,
)

GetSegmentInfoMode0Response = Struct(
    "reserved" / Int8ul,
    "basicInfo" / Int32ul,
)

GetSegmentInfoMode1Response = Struct(
    "maxPages" / Int8ul,
    "addressExtension" / Int8ul,
    "maxMapping" / Int8ul,
    "compressionMethod" / Int8ul,
    "encryptionMethod" / Int8ul,
)

GetSegmentInfoMode2Response = Struct(
    "reserved" / Int8ul,
    "mappingInfo" / Int32ul,
)

PageProperties = BitStruct(
    Padding(2),
    "xcpWriteAccessWithEcu" / Flag,
    "xcpWriteAccessWithoutEcu" / Flag,
    "xcpReadAccessWithEcu" / Flag,
    "xcpReadAccessWithoutEcu" / Flag,
    "ecuAccessWithXcp" / Flag,
    "ecuAccessWithoutXcp" / Flag,
)

###
DaqProperties = BitStruct(
    "overloadEvent" / Flag,
    "overloadMsb" / Flag,
    "pidOffSupported" / Flag,
    "timestampSupported" / Flag,
    "bitStimSupported" / Flag,
    "resumeSupported" / Flag,
    "prescalerSupported" / Flag,
    "daqConfigType" / Flag,
)

GetDaqProcessorInfoResponse = Struct(
    "daqProperties" / DaqProperties,
    "maxDaq" / Int16ul,
    "maxEventChannel" / Int16ul,
    "minDaq" / Int8ul,
    "daqKeyByte" / BitStruct(
        "Identification_Field" / Enum(BitsInteger(2),
            IDF_ABS_ODT_NUMBER                                      = 0b00,
            IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_BYTE             = 0b01,
            IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_WORD             = 0b10,
            IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_WORD_ALIGNED     = 0b11,
        ),
        "Address_Extension" / Enum(BitsInteger(2),
           AE_DIFFERENT_WITHIN_ODT  = 0b00,
           AE_SAME_FOR_ALL_ODT      = 0b01,
           _NOT_ALLOWED             = 0b10,
           AE_SAME_FOR_ALL_DAQ      = 0b11,
        ),
        "Optimisation_Type" / Enum(BitsInteger(4),
            OM_DEFAULT              = 0b0000,
            OM_ODT_TYPE_16          = 0b0001,
            OM_ODT_TYPE_32          = 0b0010,
            OM_ODT_TYPE_64          = 0b0011,
            OM_ODT_TYPE_ALIGNMENT   = 0b0100,
            OM_MAX_ENTRY_SIZE       = 0b0101,
        ),
    ),
)

CurrentMode = BitStruct(
    "resume" / Flag,
    "running" / Flag,
    "pid_off" / Flag,
    "timestamp" / Flag,
    Padding(2),
    "direction" / Flag,
    "selected" / Flag,
)

GetDaqListModeResponse = Struct(
    "currentMode" / CurrentMode,
    Padding(2),
    "currentEventChannel" / Int16ul,
    "currentPrescaler" / Int8ul,
    "currentPriority" / Int8ul,
)

GetDaqClockResponse = Struct(
    Padding(3),
    "timestamp" / Int32ul,
)

ReadDaqResponse = Struct(
    "bitOffset" / Int8ul,
    "sizeofDaqElement" / Int8ul,
    "adressExtension" / Int8ul,
    "address" / Int32ul,
)

GetDaqResolutionInfoResponse = Struct(
    "granularityOdtEntrySizeDaq" / Int8ul,
    "maxOdtEntrySizeDaq" / Int8ul,
    "granularityOdtEntrySizeStim" / Int8ul,
    "maxOdtEntrySizeStim" / Int8ul,
    "timestampMode" / BitStruct(#Int8ul,
        "unit" / Enum(BitsInteger(4),
             DAQ_TIMESTAMP_UNIT_1NS   = 0b0000,
             DAQ_TIMESTAMP_UNIT_10NS  = 0b0001,
             DAQ_TIMESTAMP_UNIT_100NS = 0b0010,
             DAQ_TIMESTAMP_UNIT_1US   = 0b0011,
             DAQ_TIMESTAMP_UNIT_10US  = 0b0100,
             DAQ_TIMESTAMP_UNIT_100US = 0b0101,
             DAQ_TIMESTAMP_UNIT_1MS   = 0b0110,
             DAQ_TIMESTAMP_UNIT_10MS  = 0b0111,
             DAQ_TIMESTAMP_UNIT_100MS = 0b1000,
             DAQ_TIMESTAMP_UNIT_1S    = 0b1001,
             DAQ_TIMESTAMP_UNIT_1PS   = 0b1010,
             DAQ_TIMESTAMP_UNIT_10PS  = 0b1011,
             DAQ_TIMESTAMP_UNIT_100PS = 0b1100,
        ),
        "fixed" / Flag,
        "size" / Enum(BitsInteger(3),
            NO_TIME_STAMP =  0b000,
            S1 = 0b001,
            S2 = 0b010,
            NOT_ALLOWED = 0b011,
            S4 = 0b100,
        ),
    ),
    "timestampTicks" / Int16ul,
)

DaqListProperties = BitStruct(
    Padding(4),
    "stim" / Flag,
    "daq" / Flag,
    "eventFixed" / Flag,
    "predefined" / Flag,
)

GetDaqListInfoResponse = Struct(
    "daqListProperties" / DaqListProperties,
    "maxOdt" / Int8ul,
    "maxOdtEntries" / Int8ul,
    "fixedEvent" / Int16ul,
)

DaqEventProperties = BitStruct(
    Padding(4),
    "stim" / Flag,
    "daq" / Flag,
    Padding(2)
)

GetEventChannelInfoResponse = Struct(
    "daqEventProperties" / DaqEventProperties,
    "maxDaqList" / Int8ul,
    "eventChannelNameLength" / Int8ul,
    "eventChannelTimeCycle" / Int8ul,
    "eventChannelTimeUnit" / Int8ul,
    "eventChannelPriority" / Int8ul,
)

CommModePgm = BitStruct(
    Padding(1),
    "slaveBlockMode" / Flag,
    Padding(4),
    "interleavedMode" / Flag,
    "masterBlockMode" / Flag,
)

ProgramStartResponse = Struct(
    Padding(1),
    "commModePgm" / CommModePgm,
    "maxCtoPgm" / Int8ul,
    "maxBsPgm" / Int8ul,
    "minStPgm" / Int8ul,
    "queueSizePgm" / Int8ul,
)



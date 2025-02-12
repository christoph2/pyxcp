#!/usr/bin/env python
import enum
from collections import namedtuple

import construct
from construct import (
    BitsInteger,
    BitStruct,
    Bytes,
    Enum,
    Flag,
    GreedyBytes,
    GreedyRange,
    If,
    IfThenElse,
    Int8ul,
    Int16ub,
    Int16ul,
    Int32ub,
    Int32ul,
    Int64ub,
    Int64ul,
    Padding,
    Struct,
    Switch,
    this,
)


if construct.version < (2, 8):
    print("pyXCP requires at least construct 2.8")
    exit(1)


NumericType = (int, float)
MtaType = namedtuple("MtaType", "address ext")


class FrameSizeError(Exception):
    """
    A frame with an invalid size was received.
    """


class XcpResponseError(Exception):
    """
    Raise an `exception` from an XCP error packet.
    """

    def get_error_code(self):
        return self.args[0]


class XcpTimeoutError(Exception):
    """
    Timeout while waiting for a response occured.
    """


class XcpGetIdType(enum.IntEnum):
    ASCII_TEXT = 0
    FILENAME = 1
    FILE_AND_PATH = 2
    URL = 3
    FILE_TO_UPLOAD = 4
    EPK = 5
    ECU = 6
    SYSID = 7
    # Extensions by Vector Informatik.
    VECTOR_MAPNAMES = 0xDB
    VECTOR_MDI = 0xDC


class XcpGetIdModeType(enum.IntEnum):
    TRANSFER_MODE = 1
    COMPRESSED_ENCRYPTED = 2


class Command(enum.IntEnum):
    # STD

    # Mandatory Commands
    CONNECT = 0xFF
    DISCONNECT = 0xFE
    GET_STATUS = 0xFD
    SYNCH = 0xFC

    # Optional Commands
    GET_COMM_MODE_INFO = 0xFB
    GET_ID = 0xFA
    SET_REQUEST = 0xF9
    GET_SEED = 0xF8
    UNLOCK = 0xF7
    SET_MTA = 0xF6
    UPLOAD = 0xF5
    SHORT_UPLOAD = 0xF4
    BUILD_CHECKSUM = 0xF3
    TRANSPORT_LAYER_CMD = 0xF2
    USER_CMD = 0xF1
    GET_VERSION = 0xC000

    # CAL

    # Mandatory Commands
    DOWNLOAD = 0xF0

    # Optional Commands
    DOWNLOAD_NEXT = 0xEF
    DOWNLOAD_MAX = 0xEE
    SHORT_DOWNLOAD = 0xED
    MODIFY_BITS = 0xEC

    # PAG

    # Mandatory Commands
    SET_CAL_PAGE = 0xEB
    GET_CAL_PAGE = 0xEA

    # Optional Commands
    GET_PAG_PROCESSOR_INFO = 0xE9
    GET_SEGMENT_INFO = 0xE8
    GET_PAGE_INFO = 0xE7
    SET_SEGMENT_MODE = 0xE6
    GET_SEGMENT_MODE = 0xE5
    COPY_CAL_PAGE = 0xE4

    # DAQ

    # Mandatory Commands
    CLEAR_DAQ_LIST = 0xE3
    SET_DAQ_PTR = 0xE2
    WRITE_DAQ = 0xE1
    WRITE_DAQ_MULTIPLE = 0xC7
    SET_DAQ_LIST_MODE = 0xE0
    GET_DAQ_LIST_MODE = 0xDF
    START_STOP_DAQ_LIST = 0xDE
    START_STOP_SYNCH = 0xDD

    # Optional Commands
    GET_DAQ_CLOCK = 0xDC
    READ_DAQ = 0xDB
    GET_DAQ_PROCESSOR_INFO = 0xDA
    GET_DAQ_RESOLUTION_INFO = 0xD9
    GET_DAQ_LIST_INFO = 0xD8
    GET_DAQ_EVENT_INFO = 0xD7
    DTO_CTR_PROPERTIES = 0xC5
    SET_DAQ_PACKED_MODE = 0xC001
    GET_DAQ_PACKED_MODE = 0xC002
    FREE_DAQ = 0xD6
    ALLOC_DAQ = 0xD5
    ALLOC_ODT = 0xD4
    ALLOC_ODT_ENTRY = 0xD3

    # PGM

    # Mandatory Commands
    PROGRAM_START = 0xD2
    PROGRAM_CLEAR = 0xD1
    PROGRAM = 0xD0
    PROGRAM_RESET = 0xCF

    # Optional Commands
    GET_PGM_PROCESSOR_INFO = 0xCE
    GET_SECTOR_INFO = 0xCD
    PROGRAM_PREPARE = 0xCC
    PROGRAM_FORMAT = 0xCB
    PROGRAM_NEXT = 0xCA
    PROGRAM_MAX = 0xC9
    PROGRAM_VERIFY = 0xC8

    TIME_CORRELATION_PROPERTIES = 0xC6

    # DBG

    DBG_ATTACH = 0xC0FC00
    DBG_GET_VENDOR_INFO = 0xC0FC01
    DBG_GET_MODE_INFO = 0xC0FC02
    DBG_GET_JTAG_ID = 0xC0FC03
    DBG_HALT_AFTER_RESET = 0xC0FC04
    DBG_GET_HWIO_INFO = 0xC0FC05
    DBG_SET_HWIO_EVENT = 0xC0FC06
    DBG_HWIO_CONTROL = 0xC0FC07
    DBG_EXCLUSIVE_TARGET_ACCESS = 0xC0FC08
    DBG_SEQUENCE_MULTIPLE = 0xC0FC09
    DBG_LLT = 0xC0FC0A
    DBG_READ_MODIFY_WRITE = 0xC0FC0B
    DBG_WRITE = 0xC0FC0C
    DBG_WRITE_NEXT = 0xC0FC0D
    DBG_WRITE_CAN1 = 0xC0FC0E
    DBG_WRITE_CAN2 = 0xC0FC0F
    DBG_WRITE_CAN_NEXT = 0xC0FC10
    DBG_READ = 0xC0FC11
    DBG_READ_CAN1 = 0xC0FC12
    DBG_READ_CAN2 = 0xC0FC13
    DBG_GET_TRI_DESC_TBL = 0xC0FC14
    DBG_LLBT = 0xC0FC15


class CommandCategory(enum.IntEnum):
    """Values reflect resources (resource protection status / unlock)."""

    STD = 0
    CAL_PAG = 1
    DAQ = 4
    STIM = 8
    PGM = 16


COMMAND_CATEGORIES = {  # Mainly needed to automatically UNLOCK.
    Command.CONNECT: CommandCategory.STD,
    Command.DISCONNECT: CommandCategory.STD,
    Command.GET_STATUS: CommandCategory.STD,
    Command.SYNCH: CommandCategory.STD,
    Command.GET_COMM_MODE_INFO: CommandCategory.STD,
    Command.GET_ID: CommandCategory.STD,
    Command.SET_REQUEST: CommandCategory.STD,
    Command.GET_SEED: CommandCategory.STD,
    Command.UNLOCK: CommandCategory.STD,
    Command.SET_MTA: CommandCategory.STD,
    Command.UPLOAD: CommandCategory.STD,
    Command.SHORT_UPLOAD: CommandCategory.STD,
    Command.BUILD_CHECKSUM: CommandCategory.STD,
    Command.TRANSPORT_LAYER_CMD: CommandCategory.STD,
    Command.USER_CMD: CommandCategory.STD,
    Command.GET_VERSION: CommandCategory.STD,
    Command.DOWNLOAD: CommandCategory.CAL_PAG,
    Command.DOWNLOAD_NEXT: CommandCategory.CAL_PAG,
    Command.DOWNLOAD_MAX: CommandCategory.CAL_PAG,
    Command.SHORT_DOWNLOAD: CommandCategory.CAL_PAG,
    Command.MODIFY_BITS: CommandCategory.CAL_PAG,
    Command.SET_CAL_PAGE: CommandCategory.CAL_PAG,
    Command.GET_CAL_PAGE: CommandCategory.CAL_PAG,
    Command.GET_PAG_PROCESSOR_INFO: CommandCategory.CAL_PAG,
    Command.GET_SEGMENT_INFO: CommandCategory.CAL_PAG,
    Command.GET_PAGE_INFO: CommandCategory.CAL_PAG,
    Command.SET_SEGMENT_MODE: CommandCategory.CAL_PAG,
    Command.GET_SEGMENT_MODE: CommandCategory.CAL_PAG,
    Command.COPY_CAL_PAGE: CommandCategory.CAL_PAG,
    Command.CLEAR_DAQ_LIST: CommandCategory.DAQ,
    Command.CLEAR_DAQ_LIST: CommandCategory.DAQ,
    Command.SET_DAQ_PTR: CommandCategory.DAQ,
    Command.WRITE_DAQ: CommandCategory.DAQ,
    Command.WRITE_DAQ_MULTIPLE: CommandCategory.DAQ,
    Command.SET_DAQ_LIST_MODE: CommandCategory.DAQ,
    Command.GET_DAQ_LIST_MODE: CommandCategory.DAQ,
    Command.START_STOP_DAQ_LIST: CommandCategory.DAQ,
    Command.START_STOP_SYNCH: CommandCategory.DAQ,
    Command.GET_DAQ_CLOCK: CommandCategory.DAQ,
    Command.READ_DAQ: CommandCategory.DAQ,
    Command.GET_DAQ_PROCESSOR_INFO: CommandCategory.DAQ,
    Command.GET_DAQ_RESOLUTION_INFO: CommandCategory.DAQ,
    Command.GET_DAQ_LIST_INFO: CommandCategory.DAQ,
    Command.GET_DAQ_EVENT_INFO: CommandCategory.DAQ,
    Command.DTO_CTR_PROPERTIES: CommandCategory.DAQ,
    Command.SET_DAQ_PACKED_MODE: CommandCategory.DAQ,
    Command.GET_DAQ_PACKED_MODE: CommandCategory.DAQ,
    Command.FREE_DAQ: CommandCategory.DAQ,
    Command.ALLOC_DAQ: CommandCategory.DAQ,
    Command.ALLOC_ODT: CommandCategory.DAQ,
    Command.ALLOC_ODT_ENTRY: CommandCategory.DAQ,
    Command.PROGRAM_START: CommandCategory.PGM,
    Command.PROGRAM_CLEAR: CommandCategory.PGM,
    Command.PROGRAM: CommandCategory.PGM,
    Command.PROGRAM_RESET: CommandCategory.PGM,
    Command.GET_PGM_PROCESSOR_INFO: CommandCategory.PGM,
    Command.GET_SECTOR_INFO: CommandCategory.PGM,
    Command.PROGRAM_PREPARE: CommandCategory.PGM,
    Command.PROGRAM_FORMAT: CommandCategory.PGM,
    Command.PROGRAM_NEXT: CommandCategory.PGM,
    Command.PROGRAM_MAX: CommandCategory.PGM,
    Command.PROGRAM_VERIFY: CommandCategory.PGM,
    # Well... ?
    # TIME_CORRELATION_PROPERTIES
}


class TransportLayerCommands(enum.IntEnum):
    # CAN
    GET_SLAVE_ID = 0xFF
    GET_DAQ_ID = 0xFE
    SET_DAQ_ID = 0xFD

    # Flexray
    FLX_ASSIGN = 0xFF
    FLX_ACTIVATE = 0xFE
    FLX_DEACTIVATE = 0xFD
    GET_DAQ_FLX_BUF = 0xFC
    SET_DAQ_FLX_BUF = 0xFB

    # USB
    GET_DAQ_EP = 0xFF
    SET_DAQ_EP = 0xFE


XcpError = Enum(
    Int8ul,
    ERR_CMD_SYNCH=0x00,  # Command processor synchronization. S0
    ERR_CMD_BUSY=0x10,  # Command was not executed. S2
    ERR_DAQ_ACTIVE=0x11,  # Command rejected because DAQ is running. S2
    ERR_PGM_ACTIVE=0x12,  # Command rejected because PGM is running. S2
    ERR_CMD_UNKNOWN=0x20,  # Unknown command or not implemented optional
    # command. S2
    ERR_CMD_SYNTAX=0x21,  # Command syntax invalid. S2
    ERR_OUT_OF_RANGE=0x22,  # Command syntax valid but command parameter(s)
    # out of range. S2
    ERR_WRITE_PROTECTED=0x23,  # The memory location is write protected. S2
    ERR_ACCESS_DENIED=0x24,  # The memory location is not accessible. S2
    ERR_ACCESS_LOCKED=0x25,  # Access denied, Seed & Key is required. S2
    ERR_PAGE_NOT_VALID=0x26,  # Selected page not available. S2
    ERR_MODE_NOT_VALID=0x27,  # Selected page mode not available. S2
    ERR_SEGMENT_NOT_VALID=0x28,  # Selected segment not valid. S2
    ERR_SEQUENCE=0x29,  # Sequence error. S2
    ERR_DAQ_CONFIG=0x2A,  # DAQ configuration not valid. S2
    ERR_MEMORY_OVERFLOW=0x30,  # Memory overflow error. S2
    ERR_GENERIC=0x31,  # Generic error. S2
    ERR_VERIFY=0x32,  # The slave internal program verify routine detects an
    # error. S3
    # NEW IN 1.1
    ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE=0x33,
    # Access to the requested resource is temporary not possible. S3
    ERR_TIMEOUT=0xFF,  # Used by errorhandler; not an offical errorcode.
)


class Event(enum.IntEnum):
    """XCP Event Codes"""

    EV_RESUME_MODE = 0x00
    EV_CLEAR_DAQ = 0x01
    EV_STORE_DAQ = 0x02
    EV_STORE_CAL = 0x03
    EV_CMD_PENDING = 0x05
    EV_DAQ_OVERLOAD = 0x06
    EV_SESSION_TERMINATED = 0x07
    EV_TIME_SYNC = 0x08
    EV_STIM_TIMEOUT = 0x09
    EV_SLEEP = 0x0A
    EV_WAKE_UP = 0x0B
    EV_USER = 0xFE
    EV_TRANSPORT = 0xFF


Response = Struct(
    "type"
    / Enum(
        Int8ul,
        OK=0xFF,
        ERR=0xFE,
        EV=0xFD,
        SERV=0xFC,
    )
)

DAQ = Struct(
    "odt" / Int8ul,
    "daq" / Int8ul,
    "data" / GreedyBytes,
)

ResourceType = BitStruct(
    Padding(2),
    "dbg" / Flag,
    "pgm" / Flag,
    "stim" / Flag,
    "daq" / Flag,
    Padding(1),
    "calpag" / Flag,
)

RESOURCE_VALUES = {
    "dbg": 32,
    "pgm": 16,
    "stim": 8,
    "daq": 4,
    "calpag": 1,
}

AddressGranularity = Enum(BitsInteger(2), BYTE=0b00, WORD=0b01, DWORD=0b10, RESERVED=0b11)

ByteOrder = Enum(BitsInteger(1), INTEL=0, MOTOROLA=1)

# byte-order dependent types
Int16u = IfThenElse(this._.byteOrder == ByteOrder.INTEL, Int16ul, Int16ub)
Int32u = IfThenElse(this._.byteOrder == ByteOrder.INTEL, Int32ul, Int32ub)
Int64u = IfThenElse(this._.byteOrder == ByteOrder.INTEL, Int64ul, Int64ub)

CommModeBasic = BitStruct(
    "optional" / Flag,  # The OPTIONAL flag indicates whether additional
    # information on supported types of Communication mode
    # is available. The master can get that additional
    # information with GET_COMM_MODE_INFO
    "slaveBlockMode" / Flag,
    Padding(3),
    "addressGranularity" / AddressGranularity,
    "byteOrder" / ByteOrder,
)

ConnectResponsePartial = Struct("resource" / ResourceType, "commModeBasic" / CommModeBasic)

ConnectResponse = Struct(
    "resource" / ResourceType,
    "commModeBasic" / CommModeBasic,
    "maxCto" / Int8ul,
    "maxDto" / Int16u,
    "protocolLayerVersion" / Int8ul,
    "transportLayerVersion" / Int8ul,
)

GetVersionResponse = Struct(
    Padding(1),
    "protocolMajor" / Int8ul,
    "protocolMinor" / Int8ul,
    "transportMajor" / Int8ul,
    "transportMinor" / Int8ul,
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
    Padding(1),
    "sessionConfiguration" / Int16u,
)

CommModeOptional = BitStruct(
    Padding(6),
    "interleavedMode" / Flag,
    "masterBlockMode" / Flag,
)

GetCommModeInfoResponse = Struct(
    Padding(1),
    "commModeOptional" / CommModeOptional,
    Padding(1),
    "maxBs" / Int8ul,
    "minSt" / Int8ul,
    "queueSize" / Int8ul,
    "xcpDriverVersionNumber" / Int8ul,
)

GetIDResponse = Struct(
    "mode" / Int8ul,
    Padding(2),
    "length" / Int32u,
    "identification" / If(this.mode == 1, Int8ul[this.length]),
)

GetSeedResponse = Struct("length" / Int8ul, "seed" / If(this.length > 0, Int8ul[this.length]))

SetRequestMode = BitStruct(
    Padding(4),
    "clearDaqReq" / Flag,
    "storeDaqReq" / Flag,
    Padding(1),
    "storeCalReq" / Flag,
)

BuildChecksumResponse = Struct(
    "checksumType"
    / Enum(
        Int8ul,
        XCP_NONE=0x00,
        XCP_ADD_11=0x01,
        XCP_ADD_12=0x02,
        XCP_ADD_14=0x03,
        XCP_ADD_22=0x04,
        XCP_ADD_24=0x05,
        XCP_ADD_44=0x06,
        XCP_CRC_16=0x07,
        XCP_CRC_16_CITT=0x08,
        XCP_CRC_32=0x09,
        XCP_USER_DEFINED=0xFF,
    ),
    Padding(2),
    "checksum" / Int32u,
)

SetCalPageMode = BitStruct(
    "all" / Flag,
    Padding(5),
    "xcp" / Flag,
    "ecu" / Flag,
)

PagProperties = BitStruct(
    Padding(7),
    "freezeSupported" / Flag,
)


GetPagProcessorInfoResponse = Struct(
    "maxSegments" / Int8ul,
    "pagProperties" / PagProperties,
)

GetSegmentInfoMode0Response = Struct(
    Padding(3),
    "basicInfo" / Int32u,
)

GetSegmentInfoMode1Response = Struct(
    "maxPages" / Int8ul,
    "addressExtension" / Int8ul,
    "maxMapping" / Int8ul,
    "compressionMethod" / Int8ul,
    "encryptionMethod" / Int8ul,
)

GetSegmentInfoMode2Response = Struct(
    Padding(3),
    "mappingInfo" / Int32u,
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

DaqProperties = BitStruct(
    "overloadEvent" / Flag,
    "overloadMsb" / Flag,
    "pidOffSupported" / Flag,
    "timestampSupported" / Flag,
    "bitStimSupported" / Flag,
    "resumeSupported" / Flag,
    "prescalerSupported" / Flag,
    "daqConfigType" / Enum(BitsInteger(1), STATIC=0b0, DYNAMIC=0b1),
)

GetDaqProcessorInfoResponse = Struct(
    "daqProperties" / DaqProperties,
    "maxDaq" / Int16u,
    "maxEventChannel" / Int16u,
    "minDaq" / Int8ul,
    "daqKeyByte"
    / BitStruct(
        "Identification_Field"
        / Enum(
            BitsInteger(2),
            IDF_ABS_ODT_NUMBER=0b00,
            IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_BYTE=0b01,
            IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_WORD=0b10,
            IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_WORD_ALIGNED=0b11,
        ),
        "Address_Extension"
        / Enum(
            BitsInteger(2),
            AE_DIFFERENT_WITHIN_ODT=0b00,
            AE_SAME_FOR_ALL_ODT=0b01,
            _NOT_ALLOWED=0b10,
            AE_SAME_FOR_ALL_DAQ=0b11,
        ),
        "Optimisation_Type"
        / Enum(
            BitsInteger(4),
            OM_DEFAULT=0b0000,
            OM_ODT_TYPE_16=0b0001,
            OM_ODT_TYPE_32=0b0010,
            OM_ODT_TYPE_64=0b0011,
            OM_ODT_TYPE_ALIGNMENT=0b0100,
            OM_MAX_ENTRY_SIZE=0b0101,
        ),
    ),
)

DAQ_DIRECTION = Enum(BitsInteger(1), DAQ=0, STIM=1)

PID_OFF = Enum(BitsInteger(1), DTO_WITH_ID_FIELD=0, DTO_WITHOUT_ID_FIELD=1)

CurrentMode = BitStruct(
    "resume" / Flag,
    "running" / Flag,
    "pid_off" / PID_OFF,
    "timestamp" / Flag,
    Padding(2),
    "direction" / DAQ_DIRECTION,
    "selected" / Flag,
)

GetDaqListModeResponse = Struct(
    "currentMode" / CurrentMode,
    Padding(2),
    "currentEventChannel" / Int16u,
    "currentPrescaler" / Int8ul,
    "currentPriority" / Int8ul,
)

SetDaqListMode = BitStruct(
    Padding(2),
    "pid_off" / PID_OFF,
    "enable_timestamp" / Flag,
    Padding(2),
    "direction" / DAQ_DIRECTION,
    Padding(1),
)

DaqElement = Struct(
    "bitOffset" / Int8ul,
    "size" / Int8ul,
    "address" / Int32u,
    "addressExt" / Int8ul,
    Padding(1),
)

GetDaqClockResponse = Struct(
    Padding(3),
    "timestamp" / Int32u,
)

DaqPackedMode = Enum(Int8ul, NONE=0, ELEMENT_GROUPED=1, EVENT_GROUPED=2)

GetDaqPackedModeResponse = Struct(
    Padding(1),
    "daqPackedMode" / DaqPackedMode,
    "dpmTimestampMode"
    / If(
        (this.daqPackedMode == "ELEMENT_GROUPED") | (this.daqPackedMode == "EVENT_GROUPED"),
        Int8ul,
    ),
    "dpmSampleCount"
    / If(
        (this.daqPackedMode == "ELEMENT_GROUPED") | (this.daqPackedMode == "EVENT_GROUPED"),
        Int16u,
    ),
)

ReadDaqResponse = Struct(
    "bitOffset" / Int8ul,
    "sizeofDaqElement" / Int8ul,
    "adressExtension" / Int8ul,
    "address" / Int32u,
)

DaqTimestampUnit = Enum(
    BitsInteger(4),
    DAQ_TIMESTAMP_UNIT_1NS=0b0000,
    DAQ_TIMESTAMP_UNIT_10NS=0b0001,
    DAQ_TIMESTAMP_UNIT_100NS=0b0010,
    DAQ_TIMESTAMP_UNIT_1US=0b0011,
    DAQ_TIMESTAMP_UNIT_10US=0b0100,
    DAQ_TIMESTAMP_UNIT_100US=0b0101,
    DAQ_TIMESTAMP_UNIT_1MS=0b0110,
    DAQ_TIMESTAMP_UNIT_10MS=0b0111,
    DAQ_TIMESTAMP_UNIT_100MS=0b1000,
    DAQ_TIMESTAMP_UNIT_1S=0b1001,
    DAQ_TIMESTAMP_UNIT_1PS=0b1010,
    DAQ_TIMESTAMP_UNIT_10PS=0b1011,
    DAQ_TIMESTAMP_UNIT_100PS=0b1100,
)

GetDaqResolutionInfoResponse = Struct(
    "granularityOdtEntrySizeDaq" / Int8ul,
    "maxOdtEntrySizeDaq" / Int8ul,
    "granularityOdtEntrySizeStim" / Int8ul,
    "maxOdtEntrySizeStim" / Int8ul,
    "timestampMode"
    / BitStruct(  # Int8ul,
        "unit" / DaqTimestampUnit,
        "fixed" / Flag,
        "size"
        / Enum(
            BitsInteger(3),
            NO_TIME_STAMP=0b000,
            S1=0b001,
            S2=0b010,
            NOT_ALLOWED=0b011,
            S4=0b100,
        ),
    ),
    "timestampTicks" / Int16u,
)

DaqListProperties = BitStruct(
    Padding(3),
    "packed" / Flag,
    "stim" / Flag,
    "daq" / Flag,
    "eventFixed" / Flag,
    "predefined" / Flag,
)

GetDaqListInfoResponse = Struct(
    "daqListProperties" / DaqListProperties,
    "maxOdt" / Int8ul,
    "maxOdtEntries" / Int8ul,
    "fixedEvent" / Int16u,
)

StartStopDaqListResponse = Struct("firstPid" / Int8ul)

DaqEventProperties = BitStruct(
    "consistency"
    / Enum(
        BitsInteger(2),
        CONSISTENCY_ODT=0b00,
        CONSISTENCY_DAQ=0b01,
        CONSISTENCY_EVENTCHANNEL=0b10,
        CONSISTENCY_NONE=0b11,
    ),
    Padding(1),
    "packed" / Flag,
    "stim" / Flag,
    "daq" / Flag,
    Padding(2),
)

GetEventChannelInfoResponse = Struct(
    "daqEventProperties" / DaqEventProperties,
    "maxDaqList" / Int8ul,
    "eventChannelNameLength" / Int8ul,
    "eventChannelTimeCycle" / Int8ul,
    "eventChannelTimeUnit"
    / Enum(
        Int8ul,
        EVENT_CHANNEL_TIME_UNIT_1NS=0,
        EVENT_CHANNEL_TIME_UNIT_10NS=1,
        EVENT_CHANNEL_TIME_UNIT_100NS=2,
        EVENT_CHANNEL_TIME_UNIT_1US=3,
        EVENT_CHANNEL_TIME_UNIT_10US=4,
        EVENT_CHANNEL_TIME_UNIT_100US=5,
        EVENT_CHANNEL_TIME_UNIT_1MS=6,
        EVENT_CHANNEL_TIME_UNIT_10MS=7,
        EVENT_CHANNEL_TIME_UNIT_100MS=8,
        EVENT_CHANNEL_TIME_UNIT_1S=9,
        EVENT_CHANNEL_TIME_UNIT_1PS=10,
        EVENT_CHANNEL_TIME_UNIT_10PS=11,
        EVENT_CHANNEL_TIME_UNIT_100PS=12,
    ),
    "eventChannelPriority" / Int8ul,
)

GetSlaveIdResponse = Struct(
    "magic" / Bytes(3),
    "identifier" / Int32u,
)

GetDaqIdResponse = Struct(
    "canIdFixed"
    / Enum(
        Int8ul,
        CONFIGURABLE=0,
        FIXED=1,
    ),
    Padding(2),
    "identifier" / Int32u,
)

DtoCtrProperties = BitStruct(
    "evtCtrPresent" / Flag,
    "stimCtrCpyPresent" / Flag,
    "stimModePresent" / Flag,
    "daqModePresent" / Flag,
    "relatedEventPresent" / Flag,
    "stimModeFixed" / Flag,
    "daqModeFixed" / Flag,
    "relatedEventFixed" / Flag,
)

DtoCtrMode = BitStruct(Padding(6), "stimMode" / Flag, "daqMode" / Flag)

DtoCtrPropertiesResponse = Struct("properties" / DtoCtrProperties, "relatedEventChannel" / Int16u, "mode" / DtoCtrMode)

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

PgmProperties = BitStruct(
    "nonSeqPgmRequired" / Flag,
    "nonSeqPgmSupported" / Flag,
    "encryptionRequired" / Flag,
    "encryptionSupported" / Flag,
    "compressionRequired" / Flag,
    "compressionSupported" / Flag,
    "functionalMode" / Flag,
    "absoluteMode" / Flag,
)

GetPgmProcessorInfoResponse = Struct("pgmProperties" / PgmProperties, "maxSector" / Int8ul)

GetSectorInfoResponseMode01 = Struct(
    "clearSequenceNumber" / Int8ul,
    "programSequenceNumber" / Int8ul,
    "programmingMethod" / Int8ul,
    "sectorInfo" / Int32u,
)

GetSectorInfoResponseMode2 = Struct("sectorNameLength" / Int8ul)

TimeCorrelationPropertiesResponse = Struct(
    "slaveConfig" / Int8ul,
    "observableClocks" / Int8ul,
    "syncState" / Int8ul,
    "clockInfo" / Int8ul,
    Padding(1),
    "clusterId" / Int16u,
)

DaqPtr = namedtuple("DaqPtr", "daqListNumber odtNumber odtEntryNumber")

DbgAttachResponse = Struct(
    "major" / Int8ul,
    "minor" / Int8ul,
    "timeout1" / Int8ul,
    "timeout7" / Int8ul,
    Padding(1),
    "maxCtoDbg" / Int16u,
)

DbgGetVendorInfoResponse = Struct(
    "length" / Int8ul,
    "vendorId" / Int16u,
    "vendorInfo" / Int8ul[this.length],
)

DbgGetModeInfoResponse = Struct(
    Padding(1),
    "maxHwIoPins" / Int8ul,
    "dialect" / Int8ul,
    "feature" / Int8ul,
    "serviceLevel" / Int8ul,
)

DbgGetJtagIdResponse = Struct(
    Padding(3),
    "jtagId" / Int32u,
)

DbgGetHwioInfoPin = Struct(
    "index" / Int8ul,
    "mode" / Int8ul,
    "pinClass" / Int8ul,
    "state" / Int8ul,
)

DbgGetHwioInfoResponse = Struct(
    "num" / Int8ul,
    "pins" / DbgGetHwioInfoPin[this.num],
)

DbgHwioControlResponse = GreedyBytes

DbgSequenceMultipleResult = Struct(
    "status" / Int8ul,
    "repeat" / Int8ul,
    "tdo" / Int32ub,
)

DbgSequenceMultipleResponse = Struct(
    Padding(1),
    "num" / Int8ul,
    "results" / DbgSequenceMultipleResult[this.num],
)

DbgLltResult = Struct(
    "length" / Int8ul,
    "data" / Int8ul[this.length // 8],
)

DbgLltResponse = Struct(
    "num" / Int8ul,
    "results" / DbgLltResult[this.num],
)

DbgReadModifyWriteResponse = Struct(
    If(this._.width == 2, Padding(1)),
    If(this._.width == 4, Padding(3)),
    If(this._.width == 8, Padding(7)),
    "value" / Switch(this._.width, {1: Int8ul, 2: Int16u, 4: Int32u, 8: Int64u}),
)

DbgReadResponse = Struct(
    If(this._.width == 2, Padding(1)),
    If(this._.width == 4, Padding(3)),
    If(this._.width == 8, Padding(7)),
    "data" / GreedyRange(Switch(this._.width, {1: Int8ul, 2: Int16u, 4: Int32u, 8: Int64u})),
)

DbgGetTriDescTblTrad = Struct(
    "trai" / Int64ul,
    "trdt" / Int16ul,
    "trat" / Int16ul,
    Padding(4),
)

DbgGetTriDescTblTri = Struct(
    "tri" / Int8ul,
    "trad_cnt" / Int8ul,
    Padding(6),
    "trads" / DbgGetTriDescTblTrad[this.trad_cnt],
)

DbgGetTriDescTbl = Struct("tri_cnt" / Int8ul, Padding(7), "tris" / DbgGetTriDescTblTri[this.tri_cnt])

DbgGetTriDescTblResponse = Struct("mode" / Int8ul, Padding(2), "length" / Int32u, "table" / DbgGetTriDescTbl)

DbgLlbtResponse = Struct(Padding(1), "length" / Int16u, "data" / Int8ul[this.length])

# Convert to seconds.
DAQ_TIMESTAMP_UNIT_TO_EXP = {
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

# Convert to nano-seconds.
DAQ_TIMESTAMP_UNIT_TO_NS = {
    "DAQ_TIMESTAMP_UNIT_1PS": 0.001,
    "DAQ_TIMESTAMP_UNIT_10PS": 0.01,
    "DAQ_TIMESTAMP_UNIT_100PS": 0.1,
    "DAQ_TIMESTAMP_UNIT_1NS": 1,
    "DAQ_TIMESTAMP_UNIT_10NS": 10,
    "DAQ_TIMESTAMP_UNIT_100NS": 100,
    "DAQ_TIMESTAMP_UNIT_1US": 1000,
    "DAQ_TIMESTAMP_UNIT_10US": 10 * 1000,
    "DAQ_TIMESTAMP_UNIT_100US": 100 * 1000,
    "DAQ_TIMESTAMP_UNIT_1MS": 1000 * 1000,
    "DAQ_TIMESTAMP_UNIT_10MS": 10 * 1000 * 1000,
    "DAQ_TIMESTAMP_UNIT_100MS": 100 * 1000 * 1000,
    "DAQ_TIMESTAMP_UNIT_1S": 1000 * 1000 * 1000,
}

EVENT_CHANNEL_TIME_UNIT_TO_EXP = {
    "EVENT_CHANNEL_TIME_UNIT_1PS": -12,
    "EVENT_CHANNEL_TIME_UNIT_10PS": -11,
    "EVENT_CHANNEL_TIME_UNIT_100PS": -10,
    "EVENT_CHANNEL_TIME_UNIT_1NS": -9,
    "EVENT_CHANNEL_TIME_UNIT_10NS": -8,
    "EVENT_CHANNEL_TIME_UNIT_100NS": -7,
    "EVENT_CHANNEL_TIME_UNIT_1US": -6,
    "EVENT_CHANNEL_TIME_UNIT_10US": -5,
    "EVENT_CHANNEL_TIME_UNIT_100US": -4,
    "EVENT_CHANNEL_TIME_UNIT_1MS": -3,
    "EVENT_CHANNEL_TIME_UNIT_10MS": -2,
    "EVENT_CHANNEL_TIME_UNIT_100MS": -1,
    "EVENT_CHANNEL_TIME_UNIT_1S": 0,
}


class XcpGetSeedMode(enum.IntEnum):
    FIRST_PART = 0
    REMAINING = 1


class FrameCategory(enum.IntEnum):
    """XCP frame categories."""

    METADATA = 0
    CMD = 1
    RESPONSE = 2
    ERROR = 3
    EVENT = 4
    SERV = 5
    DAQ = 6
    STIM = 7


class TryCommandResult(enum.IntEnum):
    """ """

    OK = 0
    XCP_ERROR = 1
    NOT_IMPLEMENTED = 2
    OTHER_ERROR = 3

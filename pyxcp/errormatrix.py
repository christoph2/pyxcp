#!/usr/bin/env python
"""Types and structures to support error-handling as specified by XCP.
"""
import enum
from collections import namedtuple

from pyxcp.types import Command, XcpError


Handler = namedtuple("Handler", "preAction  action")

TIMEOUT = 255


class PreAction(enum.IntEnum):
    """Pre-action to be taken, s. XCP spec."""

    NONE = 0
    WAIT_T7 = 1
    SYNCH = 2
    GET_SEED_UNLOCK = 3
    SET_MTA = 4
    SET_DAQ_PTR = 6
    START_STOP_X = 7
    REINIT_DAQ = 8
    DISPLAY_ERROR = 9
    DOWNLOAD = 10
    PROGRAM = 11
    UPLOAD = 12
    UNLOCK_SLAVE = 13


class Action(enum.IntEnum):
    """Action to be taken, s. XCP spec."""

    NONE = 0
    DISPLAY_ERROR = 1
    RETRY_SYNTAX = 2
    RETRY_PARAM = 3
    USE_A2L = 4  # Please refer to your A2L database.
    USE_ALTERATIVE = 5
    REPEAT = 6
    REPEAT_2_TIMES = 7
    REPEAT_INF_TIMES = 8
    RESTART_SESSION = 9
    TERMINATE_SESSION = 10
    SKIP = 11
    NEW_FLASH_WARE = 12


class Timeout(enum.IntEnum):
    """Various timeouts, s. XCP spec."""

    T1 = 0
    T2 = 1
    T3 = 2
    T4 = 3
    T5 = 4
    T6 = 5
    T7 = 6


class Severity(enum.IntEnum):
    """Severity of error.
    ---
    S0  = Information
    S1  = Warning / Request
    S2  = Resolvable Error
    S3  = Fatal Error
    """

    S0 = 0
    S1 = 1
    S2 = 2
    S3 = 3


ERROR_TABLE = {
    XcpError.ERR_CMD_SYNCH: ("Command processor synchronization.", Severity.S0),
    XcpError.ERR_CMD_BUSY: ("Command was not executed.", Severity.S2),
    XcpError.ERR_DAQ_ACTIVE: ("Command rejected because DAQ is running.", Severity.S2),
    XcpError.ERR_PGM_ACTIVE: ("Command rejected because PGM is running.", Severity.S2),
    XcpError.ERR_CMD_UNKNOWN: (
        "Unknown command or not implemented optional command.",
        Severity.S2,
    ),
    XcpError.ERR_CMD_SYNTAX: ("Command syntax invalid", Severity.S2),
    XcpError.ERR_OUT_OF_RANGE: (
        "Command syntax valid but command parameter(s) out of range.",
        Severity.S2,
    ),
    XcpError.ERR_WRITE_PROTECTED: (
        "The memory location is write protected.",
        Severity.S2,
    ),
    XcpError.ERR_ACCESS_DENIED: ("The memory location is not accessible.", Severity.S2),
    XcpError.ERR_ACCESS_LOCKED: ("Access denied, Seed & Key is required", Severity.S2),
    XcpError.ERR_PAGE_NOT_VALID: ("Selected page not available", Severity.S2),
    XcpError.ERR_MODE_NOT_VALID: ("Selected page mode not available", Severity.S2),
    XcpError.ERR_SEGMENT_NOT_VALID: ("Selected segment not valid", Severity.S2),
    XcpError.ERR_SEQUENCE: ("Sequence error", Severity.S2),
    XcpError.ERR_DAQ_CONFIG: ("DAQ configuration not valid", Severity.S2),
    XcpError.ERR_MEMORY_OVERFLOW: ("Memory overflow error", Severity.S2),
    XcpError.ERR_GENERIC: ("Generic error.", Severity.S2),
    XcpError.ERR_VERIFY: (
        "The slave internal program verify routine detects an error.",
        Severity.S3,
    ),
    XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
        "Access to the requested resource is temporary not possible",
        Severity.S2,
    ),
}


ERROR_MATRIX = {
    Command.CONNECT: {
        XcpError.ERR_TIMEOUT: ((PreAction.NONE,), Action.REPEAT_INF_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    # CONNECT(USER_DEFINED)  timeout t6  wait t7  repeat  8 times
    Command.DISCONNECT: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
    },
    Command.GET_STATUS: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.SYNCH: {
        XcpError.ERR_TIMEOUT: ((PreAction.NONE,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_SYNCH: ((PreAction.NONE), Action.SKIP),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.RESTART_SESSION),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_COMM_MODE_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.GET_ID: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.SET_REQUEST: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_SEED: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.UNLOCK: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.NONE), Action.RESTART_SESSION),
        XcpError.ERR_SEQUENCE: ((PreAction.GET_SEED_UNLOCK), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.SET_MTA: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.UPLOAD: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.SHORT_UPLOAD: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_ALTERATIVE),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.BUILD_CHECKSUM: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.TRANSPORT_LAYER_CMD: {
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.USER_CMD: {
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.DOWNLOAD: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_WRITE_PROTECTED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.DOWNLOAD_NEXT: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.DOWNLOAD),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.SET_MTA), Action.USE_ALTERATIVE),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_WRITE_PROTECTED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_SEQUENCE: ((PreAction.SET_MTA), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.DOWNLOAD_MAX: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.SET_MTA), Action.USE_ALTERATIVE),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_WRITE_PROTECTED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.SHORT_DOWNLOAD: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_ALTERATIVE),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_WRITE_PROTECTED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.MODIFY_BITS: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: (
            (PreAction.UPLOAD, PreAction.DOWNLOAD),
            Action.USE_ALTERATIVE,
        ),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_WRITE_PROTECTED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.SET_CAL_PAGE: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_PAGE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_MODE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_SEGMENT_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_CAL_PAGE: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_PAGE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_MODE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_SEGMENT_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_PAG_PROCESSOR_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.GET_SEGMENT_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEGMENT_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.GET_PAGE_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_PAGE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_SEGMENT_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.SET_SEGMENT_MODE: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_MODE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_SEGMENT_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_SEGMENT_MODE: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEGMENT_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.COPY_CAL_PAGE: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_PAGE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_SEGMENT_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.SET_DAQ_PTR: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_DAQ_ACTIVE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.WRITE_DAQ: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_DAQ_PTR),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_DAQ_ACTIVE: ((PreAction.START_STOP_X), Action.REPEAT_2_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_WRITE_PROTECTED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_DAQ_CONFIG: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.SET_DAQ_LIST_MODE: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_DAQ_ACTIVE: ((PreAction.START_STOP_X), Action.REPEAT_2_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_MODE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.START_STOP_DAQ_LIST: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_MODE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_DAQ_CONFIG: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.START_STOP_SYNCH: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_MODE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_DAQ_CONFIG: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.CLEAR_DAQ_LIST: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_DAQ_LIST_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.WRITE_DAQ_MULTIPLE: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_DAQ_PTR),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_DAQ_ACTIVE: ((PreAction.START_STOP_X), Action.REPEAT_2_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_WRITE_PROTECTED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_DAQ_CONFIG: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.READ_DAQ: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_DAQ_PTR),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_DAQ_CLOCK: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.GET_DAQ_PROCESSOR_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.GET_DAQ_RESOLUTION_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.GET_DAQ_LIST_MODE: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_DAQ_EVENT_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.FREE_DAQ: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.ALLOC_DAQ: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.REINIT_DAQ), Action.REPEAT_2_TIMES),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.REINIT_DAQ), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.ALLOC_ODT: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.REINIT_DAQ), Action.REPEAT_2_TIMES),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.REINIT_DAQ), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.ALLOC_ODT_ENTRY: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.REINIT_DAQ), Action.REPEAT_2_TIMES),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.REINIT_DAQ), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.PROGRAM_START: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_DAQ_ACTIVE: ((PreAction.START_STOP_X), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_GENERIC: ((PreAction.NONE), Action.RESTART_SESSION),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.PROGRAM_CLEAR: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.PROGRAM: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.PROGRAM_RESET: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_PGM_ACTIVE: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.GET_PGM_PROCESSOR_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.GET_SECTOR_INFO: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_A2L),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_MODE_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_SEGMENT_NOT_VALID: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (PreAction.NONE, Action.SKIP),
    },
    Command.PROGRAM_PREPARE: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_GENERIC: ((PreAction.NONE), Action.RESTART_SESSION),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.PROGRAM_FORMAT: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.PROGRAM_NEXT: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.PROGRAM),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_ALTERATIVE),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_DENIED: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_SEQUENCE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.PROGRAM_MAX: {
        XcpError.ERR_TIMEOUT: (
            (PreAction.SYNCH, PreAction.SET_MTA),
            Action.REPEAT_2_TIMES,
        ),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.USE_ALTERATIVE),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_MEMORY_OVERFLOW: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
    Command.PROGRAM_VERIFY: {
        XcpError.ERR_TIMEOUT: ((PreAction.SYNCH,), Action.REPEAT_2_TIMES),
        XcpError.ERR_CMD_BUSY: ((PreAction.WAIT_T7), Action.REPEAT_INF_TIMES),
        XcpError.ERR_CMD_UNKNOWN: ((PreAction.NONE), Action.DISPLAY_ERROR),
        XcpError.ERR_CMD_SYNTAX: ((PreAction.NONE), Action.RETRY_SYNTAX),
        XcpError.ERR_OUT_OF_RANGE: ((PreAction.NONE), Action.RETRY_PARAM),
        XcpError.ERR_ACCESS_LOCKED: ((PreAction.UNLOCK_SLAVE), Action.REPEAT_2_TIMES),
        XcpError.ERR_SEQUENCE: ((PreAction.NONE), Action.REPEAT_2_TIMES),
        XcpError.ERR_GENERIC: ((PreAction.NONE), Action.RESTART_SESSION),
        XcpError.ERR_VERIFY: ((PreAction.NONE), Action.NEW_FLASH_WARE),
        XcpError.ERR_RESOURCE_TEMPORARY_NOT_ACCESSIBLE: (
            PreAction.DISPLAY_ERROR,
            Action.REPEAT,
        ),
    },
}

ALTERNATIVES = {
    Command.SHORT_UPLOAD: (),
    Command.DOWNLOAD_NEXT: (),
    Command.DOWNLOAD_MAX: (),
    Command.SHORT_DOWNLOAD: (),
    Command.MODIFY_BITS: (),
    Command.PROGRAM_NEXT: (),
    Command.PROGRAM_MAX: (),
}

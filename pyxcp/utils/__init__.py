#!/usr/bin/env python
import datetime
import functools
import operator
import sys
import time
from enum import IntEnum
from time import perf_counter, sleep
from typing import Union

import chardet
from pyxcp.cpp_ext.cpp_ext import TimestampInfo


def hexDump(arr: bytes | bytearray):
    if not isinstance(arr, (bytes, bytearray)):
        arr = bytes(arr)

    return f"[{arr.hex(' ')}]"


def seconds_to_nanoseconds(value: float) -> int:
    return int(value * 1_000_000_000)


def slicer(iterable, sliceLength, converter=None):
    if converter is None:
        converter = type(iterable)
    length = len(iterable)
    return [converter(iterable[item : item + sliceLength]) for item in range(0, length, sliceLength)]


def functools_reduce_iconcat(a):
    return functools.reduce(operator.iconcat, a, [])


def flatten(*args):
    """Flatten a list of lists into a single list.

    s. https://stackoverflow.com/questions/952914/how-do-i-make-a-flat-list-out-of-a-list-of-lists
    """
    return functools.reduce(operator.iconcat, args[0], [])


def getPythonVersion():
    return sys.version_info


def decode_bytes(byte_str: bytes) -> str:
    """Decode bytes with the help of chardet"""
    encoding = chardet.detect(byte_str).get("encoding")
    if not encoding:
        return byte_str.decode("ascii", "ignore")
    else:
        return byte_str.decode(encoding)


PYTHON_VERSION = getPythonVersion()


def short_sleep():
    sleep(0.0005)


def delay(amount: float):
    """Performe a busy-wait delay, which is much more precise than `time.sleep`"""

    start = perf_counter()
    while perf_counter() < start + amount:
        pass


class CurrentDatetime(TimestampInfo):
    def __init__(self, timestamp_ns: int):
        TimestampInfo.__init__(self, timestamp_ns)
        # Read the offsets from the local time zone directly: on Linux `timezone` is an
        # abbreviation such as "JST", which is not a valid IANA zone name.
        local_time = time.localtime(timestamp_ns // 1_000_000_000)
        self.utc_offset = local_time.tm_gmtoff // 60
        self.dst_offset = (local_time.tm_gmtoff + time.timezone) // 60 if local_time.tm_isdst > 0 else 0

    def __str__(self):
        return f"""CurrentDatetime(
    datetime="{datetime.datetime.fromtimestamp(self.timestamp_ns / 1_000_000_000.0)!s}",
    timezone="{self.timezone}",
    timestamp_ns={self.timestamp_ns},
    utc_offset={self.utc_offset},
    dst_offset={self.dst_offset}
)"""


def enum_from_str(enum_class: IntEnum, enumerator: str) -> IntEnum:
    """Create an `IntEnum` instance from an enumerator `str`.

    Parameters
    ----------
    enum_class: IntEnum

    enumerator: str

    Examples
    --------

    class Color(enum.IntEnum):
        RED = 0
        GREEN = 1
        BLUE = 2

    color: Color = enum_from_str(Color, "GREEN")


    """
    member = enum_class.__members__.get(enumerator)
    if member is None:
        return None
    return enum_class(member)

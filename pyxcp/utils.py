#!/usr/bin/env python
import datetime
import functools
import operator
import sys
from binascii import hexlify
from enum import IntEnum
from time import perf_counter, sleep
from typing import Any, List, Optional, Union

import chardet
import pytz

from pyxcp.cpp_ext.cpp_ext import TimestampInfo


def hexDump(arr: Union[bytes | bytearray]):
    if isinstance(arr, (bytes, bytearray)):
        size = len(arr)
        try:
            arr = arr.hex()
        except BaseException:  # noqa: B036
            arr = hexlify(arr).decode("ascii")
        return "[{}]".format(" ".join([arr[i * 2 : (i + 1) * 2] for i in range(size)]))
    elif isinstance(arr, (list, tuple)):
        arr = bytes(arr)
        size = len(arr)
        try:
            arr = arr.hex()
        except BaseException:  # noqa: B036
            arr = hexlify(arr).decode("ascii")
        return "[{}]".format(" ".join([arr[i * 2 : (i + 1) * 2] for i in range(size)]))
    else:
        return "[{}]".format(" ".join([f"{x:02x}" for x in arr]))


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
    return functools.reduce(operator.iconcat, args, [])


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
        timezone = pytz.timezone(self.timezone)
        dt = datetime.datetime.fromtimestamp(timestamp_ns / 1_000_000_000.0)
        self.utc_offset = int(timezone.utcoffset(dt).total_seconds() / 60)
        self.dst_offset = int(timezone.dst(dt).total_seconds() / 60)

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

    Example
    -------

    class Color(enum.IntEnum):
        RED = 0
        GREEN = 1
        BLUE = 2

    color: Color = enum_from_str(Color, "GREEN")


    """
    return enum_class(enum_class.__members__.get(enumerator))

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from binascii import hexlify
from time import get_clock_info
from time import perf_counter
from time import time

import chardet


def hexDump(arr):
    if isinstance(arr, (bytes, bytearray)):
        size = len(arr)
        try:
            arr = arr.hex()
        except BaseException:
            arr = hexlify(arr).decode("ascii")
        return "[{}]".format(" ".join([arr[i * 2 : (i + 1) * 2] for i in range(size)]))
    elif isinstance(arr, (list, tuple)):
        arr = bytes(arr)
        size = len(arr)
        try:
            arr = arr.hex()
        except BaseException:
            arr = hexlify(arr).decode("ascii")
        return "[{}]".format(" ".join([arr[i * 2 : (i + 1) * 2] for i in range(size)]))
    else:
        return "[{}]".format(" ".join(["{:02x}".format(x) for x in arr]))


def slicer(iterable, sliceLength, converter=None):
    if converter is None:
        converter = type(iterable)
    length = len(iterable)
    return [converter((iterable[item : item + sliceLength])) for item in range(0, length, sliceLength)]


def flatten(*args):
    result = []
    for arg in list(args):
        if hasattr(arg, "__iter__"):
            result.extend(flatten(*arg))
        else:
            result.append(arg)
    return result


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
SHORT_SLEEP = 0.0005


def delay(amount: float):
    """Performe a busy-wait delay, which is much more precise than `time.sleep`"""

    start = perf_counter()
    while perf_counter() < start + amount:
        pass

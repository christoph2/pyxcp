#!/usr/bin/env python
import functools
import operator
import sys
from binascii import hexlify
from time import perf_counter

import chardet


def hexDump(arr):
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
SHORT_SLEEP = 0.0005


def delay(amount: float):
    """Performe a busy-wait delay, which is much more precise than `time.sleep`"""

    start = perf_counter()
    while perf_counter() < start + amount:
        pass

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from binascii import hexlify
from time import get_clock_info
from time import perf_counter
from time import time


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


PYTHON_VERSION = getPythonVersion()


def time_perfcounter_correlation():
    """Get the `perf_counter` value nearest to when time.time() is updated if the `time.time` on
    this platform has a resolution higher than 10us. This is tipical for the Windows platform
    were the beste resolution is ~500us.

    On non Windows platforms the current time and perf_counter is directly returned since the
    resolution is tipical ~1us.

    Note this value is based on when `time.time()` is observed to update from Python, it is not
    directly returned by the operating system.

    :return:
        (t, performance_counter) time.time value and perf_counter value when the time.time
        is updated

    """

    # use this if the resolution is higher than 10us
    if get_clock_info("time").resolution > 1e-5:
        t0 = time()
        while True:
            t1, performance_counter = time(), perf_counter()
            if t1 != t0:
                break
    else:
        return time(), perf_counter()
    return t1, performance_counter


def delay(amount: float):
    """Performe a busy-wait delay, which is much more precise than `time.sleep`"""

    start = perf_counter()
    while perf_counter() < start + amount:
        pass

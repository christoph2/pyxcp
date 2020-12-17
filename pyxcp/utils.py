#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = """
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

import ctypes
import mmap
import os
import sys
#import subprocess
import threading
from time import time, perf_counter, get_clock_info
from binascii import hexlify

##
##try:
##    import win32api
##    import win32process
##    import win32con
##except ImportError:
##    WINAPI = False
##else:
##    WINAPI = True
##


def hexDump(arr):
    if isinstance(arr, (bytes, bytearray)):
        size = len(arr)
        try:
            arr = arr.hex()
        except:
            arr = hexlify(arr).decode('ascii')
        return "[{}]".format(' '.join([arr[i*2: (i+1)*2] for i in range(size)]))
    elif isinstance(arr, (list, tuple)):
        arr = bytes(arr)
        size = len(arr)
        try:
            arr = arr.hex()
        except:
            arr = hexlify(arr).decode('ascii')
        return "[{}]".format(' '.join([arr[i*2: (i+1)*2] for i in range(size)]))
    else:
        return "[{}]".format(' '.join(["{:02x}".format(x) for x in arr]))


def slicer(iterable, sliceLength, converter=None):
    if converter is None:
        converter = type(iterable)
    length = len(iterable)
    return [
        converter((iterable[item:item + sliceLength]))
        for item in range(0, length, sliceLength)]


def flatten(*args):
    result = []
    for arg in list(args):
        if hasattr(arg, '__iter__'):
            result.extend(flatten(*arg))
        else:
            result.append(arg)
    return result


##
##def intToArray(value):
##    result = []
##    while value:
##        result.append(value & 0xff)
##        value >>= 8
##    if result:
##        return list(reversed(result))
##    else:
##        return [0]
##
##
##class Curry:
##    def __init__(self, fun, *args, **kwargs):
##        self.fun = fun
##        self.pending = args[:]
##        self.kwargs = kwargs.copy()
##
##    def __call__(self, *args, **kwargs):
##        if kwargs and self.kwargs:
##            kw = self.kwargs.copy()
##            kw.update(kwargs)
##        else:
##            kw = kwargs or self.kwargs
##        return self.fun(*(self.pending + args), **kw)
##

def getPythonVersion():
    return sys.version_info


PYTHON_VERSION = getPythonVersion()

if PYTHON_VERSION.major == 3:
    from io import BytesIO as StringIO
else:
    try:
        from cStringIO import StringIO
    except ImportError:
        from StringIO import StringIO


def time_perfcounter_correlation():
    """ Get the `perf_counter` value nearest to when time.time() is updated if the `time.time` on
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



##
##def createStringBuffer(*args):
##    """Create a string with file-like behaviour (StringIO on Python 2.x).
##    """
##    return StringIO(*args)
##
##
##def binExtractor(fname, offset, length):
##    """Extract a junk of data from a file.
##    """
##    fp = open(fname)
##    fp.seek(offset)
##    data = fp.read(length)
##    return data
##


##
##CYG_PREFIX = "/cygdrive/"
##
##
##def cygpathToWin(path):
##    if path.startswith(CYG_PREFIX):
##        path = path[len(CYG_PREFIX):]
##        driveLetter = "{0}:\\".format(path[0])
##        path = path[2:].replace("/", "\\")
##        path = "{0}{1}".format(driveLetter, path)
##    return path
##
##
##class StructureWithEnums(ctypes.Structure):
##    """Add missing enum feature to ctypes Structures.
##    """
##    _map = {}
##
##    def __getattribute__(self, name):
##        _map = ctypes.Structure.__getattribute__(self, '_map')
##        value = ctypes.Structure.__getattribute__(self, name)
##        if name in _map:
##            EnumClass = _map[name]
##            if isinstance(value, ctypes.Array):
##                return [EnumClass(x) for x in value]
##            else:
##                return EnumClass(value)
##        else:
##            return value
##
##    def __str__(self):
##        result = []
##        result.append("struct {0} {{".format(self.__class__.__name__))
##        for field in self._fields_:
##            attr, attrType = field
##            if attr in self._map:
##                attrType = self._map[attr]
##            value = getattr(self, attr)
##            result.append("    {0} [{1}] = {2!r};".format(
##                attr, attrType.__name__, value))
##        result.append("};")
##        return '\n'.join(result)
##
##    __repr__ = __str__
##
##
##class CommandError(Exception):
##    pass
##
##
##def runCommand(cmd):
##    proc = subprocess.Popen(
##        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
##    result = proc.communicate()
##    proc.wait()
##    if proc.returncode:
##        raise CommandError("{0}".format(result[1]))
##    return result[0]
##
##
##class SingletonBase(object):
##    _lock = threading.Lock()
##
##    def __new__(cls, *args, **kws):
##        # Double-Checked Locking
##        if not hasattr(cls, '_instance'):
##            try:
##                cls._lock.acquire()
##                if not hasattr(cls, '_instance'):
##                    cls._instance = super(SingletonBase, cls).__new__(cls)
##            finally:
##                cls._lock.release()
##        return cls._instance
##


#  class RepresentationMixIn(object):
#
#      def __repr__(self):
#          keys = [k for k in self.__dict__ if not (k.startswith('__') and k.endswith('__'))]
#          result = []
#          result.append("{0!s} {{".format(self.__class__.__name__))
#          for key in keys:
#              value = getattr(self, key)
#              if isinstance(value, (int, )):
#                  line = "    {0!s} = 0x{1:X}".format(key, value)
#              elif isinstance(value, (float, types.NoneType)):
#                  line = "    {0!s} = {1!s}".format(key, value)
#              elif isinstance(value, array):
#                  line = "    {0!s} = {1!s}".format(key, hexDump(value))
#              else:
#                  line = "    {0!s} = '{1!s}'".format(key, value)
#              result.append(line)
#          result.append("}")
#          return '\n'.join(result)
#

##
##def memoryMap(filename, writeable=False):
##    size = os.path.getsize(filename)
##    fd = os.open(filename, os.O_RDWR if writeable else os.O_RDONLY)
##    return mmap.mmap(
##        fd, size, access=mmap.ACCESS_WRITE if writeable else mmap.ACCESS_READ)
##
##
##if sys.platform == "win32" and WINAPI:
##
##    # Code snippet taken from
##    # http://code.activestate.com/recipes/496767-set-process-priority-in-windows/
##    # Licenced under PSF.
##
##    def setpriority(pid=None, priority=1):
##        """ Set The Priority of a Windows Process.  Priority is a value
##            between 0-5 where 2 is normal priority.  Default sets the priority
##            of the current python process but can take any valid process ID."""
##        priorityclasses = [win32process.IDLE_PRIORITY_CLASS,
##                           win32process.BELOW_NORMAL_PRIORITY_CLASS,
##                           win32process.NORMAL_PRIORITY_CLASS,
##                           win32process.ABOVE_NORMAL_PRIORITY_CLASS,
##                           win32process.HIGH_PRIORITY_CLASS,
##                           win32process.REALTIME_PRIORITY_CLASS]
##        if pid is None:
##            # pid = win32api.GetCurrentProcessId()
##            pid = ctypes.windll.kernel32.GetCurrentProcessId()
##        handle = ctypes.windll.kernel32.OpenProcess(
##            win32con.PROCESS_ALL_ACCESS, True, pid)
##        win32process.SetPriorityClass(handle, priorityclasses[priority])
##        # Chris
##        win32process.SetProcessPriorityBoost(handle, False)
##        ct = ctypes.windll.kernel32.GetCurrentThread()
##        gle = win32api.GetLastError()
##        print("gct", win32api.FormatMessage(gle))
##        ctypes.windll.kernel32.SetThreadPriority(
##            ct, win32con.THREAD_BASE_PRIORITY_LOWRT)
##else:
##    def setpriority(pid=None, priority=1):
##        pass
##

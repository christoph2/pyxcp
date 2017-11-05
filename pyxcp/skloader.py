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

import ctypes
import platform
from pprint import pprint
import struct
import sys


CMD_GET_KEY = 0x20

ACK                         = 0 # o.k.
ERR_PRIVILEGE_NOT_AVAILABLE = 1 # the requested privilege can not be unlocked with this DLL
ERR_INVALID_SEED_LENGTH     = 2 # the seed length is wrong, key could not be computed
ERR_UNSUFFICIENT_KEY_LENGTH = 3 # the space for the key is too small

ERR_COULD_NOT_LOAD_DLL      = 16
ERR_COULD_NOT_LOAD_FUNC     = 17


bwidth, _ = platform.architecture()

if sys.platform == 'win32' and bwidth == '64bit':
    print('WIN64 !!!')

    import win32pipe
    import win32file


    DLL_NAME = b"SeedNKeyXcp.dll"
    dll = struct.pack("{}s".format(len(DLL_NAME)), DLL_NAME)

    def encode(dllName, privilege, seed):
        cmd = CMD_GET_KEY
        fmt = "BBB{}B{}s".format(len(seed), len(dllName))
        res = struct.pack(fmt, cmd, privilege, len(seed), *seed, dllName)
        return res

    def getKey(dllName, privilege, seed):
        try:
            handle = win32file.CreateFile(r"\\.\pipe\XcpSendNKey", win32file.GENERIC_READ | win32file.GENERIC_WRITE,
                0, None, win32file.OPEN_EXISTING, 0, None
            )
        except Exception as e:
            print("{} failed with [{}] - '{}' ".format(e.funcname, e.winerror, e.strerror))
            key = dstatus = None
        else:
            res = win32file.WriteFile(handle, encode(dllName, privilege, seed))
            #print("S - WriteFile: [{}]".format(res))
            wstatus, data = win32file.ReadFile(handle, 4096)
            print(data)
            # 1C F8 05 DF 00 00 00 00 00
            # 1e 0d af 33 00 00 00 00 00
            key = None
            dstatus = struct.unpack("<I", data[ : 4])[0]
            if dstatus == ACK:
                key = struct.unpack("{}B".format(len(data) - 4), data[4:])
            win32file.CloseHandle(handle)
        return (dstatus, key)
else:
    print("{} on {} not supported.".format(bwidth, sys.platform))
    #sys.exit(1)

#SEED = (0x61, 0x2b, 0x8d, 0xbb, 0x4d, 0x65, 0xdb, 0x78, 0x49, 0xb5)


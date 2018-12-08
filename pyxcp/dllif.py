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

import binascii
import platform
from pprint import pprint
import re
import subprocess
import sys


CMD_GET_KEY = 0x20
CMD_QUIT    = 0x30

ACK                         = 0 # o.k.
ERR_PRIVILEGE_NOT_AVAILABLE = 1 # the requested privilege can not be unlocked with this DLL
ERR_INVALID_SEED_LENGTH     = 2 # the seed length is wrong, key could not be computed
ERR_UNSUFFICIENT_KEY_LENGTH = 3 # the space for the key is too small

ERR_COULD_NOT_LOAD_DLL      = 16
ERR_COULD_NOT_LOAD_FUNC     = 17

bwidth, _ = platform.architecture()

if sys.platform == 'win32' and bwidth == '64bit':
  prgName = "asamkeydll64"
elif sys.platform == 'win32' and bwidth == '32bit':
  prgName = "asamkeydll32"
else:
  raise RuntimeError("Platform '{}' currently not supported.".format(sys.platform))
    
def getKey(dllName, privilege, seed):
    p0 = subprocess.Popen([prgName, dllName, str(privilege), binascii.hexlify(seed).decode("ascii")], stdout=subprocess.PIPE, shell = True)
    key = p0.stdout.read()
    res = re.split(b"\r?\n", key)
    returnCode = int(res[0])
    if len(res) < 2:
        return (returnCode, None)
    key = binascii.unhexlify(res[1])
    return (returnCode, key)
#elif sys.platform == 'win32' and bwidth == '32bit':
#  """
#  uint32_t XCP_ComputeKeyFromSeed (uint8_t resource, uint8_t seedLen, uint8_t const *seedPtr, uint8_t * keyLenPtr, uint8_t * keyPtr);
#                                                  
#  """
#  import ctypes
#  
#  def getKey(dllName, privilege, seed):
#    print("D: {} P: {} S: {}".format(dllName, privilege, seed))
#    dll = ctypes.cdll.LoadLibrary(dllName)
#    print(dll)
#    func = dll.XCP_ComputeKeyFromSeed
#    func.restype = ctypes.c_uint32
##    func.argtypes = [ctypes.c_uint8, ctypes.c_uint8, ctypes.c_char_p, ctypes.c_char_p, ctypes.c_char_p]
#    print(func)
#    
#    kb = ctypes.create_string_buffer(b'\000' * 128)
#    kl = ctypes.c_uint8(128)
#    
#    retCode = func(privilege, len(seed), ctypes.c_char_p(seed), ctypes.byref(kl), kb)
#    print("RES", retCode)
#    print("KEY", kl, kb.value)
#    return (retCode, kb.value)

#getKey("SeedNKeyXcp.dll", "1", b'\xa9\xe0\x7fSm;\xa3-;M')   # "a9e07f536d3ba32d3b4d"
#getKey("SeedNKeyXcp.dll", "1", bytes((0x61, 0x2b, 0x8d, 0xbb, 0x4d, 0x65, 0xdb, 0x78, 0x49, 0xb5)))


#!/usr/bin/env python
# -*- coding: utf-8 -*-
import binascii
import ctypes
import enum
import platform
import re
import subprocess
import sys
from pathlib import Path


class SeedNKeyResult(enum.IntEnum):
    ACK = 0  # o.k.
    ERR_PRIVILEGE_NOT_AVAILABLE = 1  # the requested privilege can not be unlocked with this DLL
    ERR_INVALID_SEED_LENGTH = 2  # the seed length is wrong, key could not be computed
    ERR_UNSUFFICIENT_KEY_LENGTH = 3  # the space for the key is too small

    ERR_COULD_NOT_LOAD_DLL = 16
    ERR_COULD_NOT_LOAD_FUNC = 17


class SeedNKeyError(Exception):
    """"""


LOADER = Path(sys.modules["pyxcp"].__file__).parent / "asamkeydll"  # Absolute path to DLL loader.

bwidth, _ = platform.architecture()

if sys.platform in ("win32", "linux"):
    if bwidth == "64bit":
        use_ctypes = False
    elif bwidth == "32bit":
        use_ctypes = True
else:
    raise RuntimeError("Platform '{}' currently not supported.".format(sys.platform))


def getKey(logger, dllName: str, privilege: int, seed: str, assume_same_bit_width: bool):

    dllName = str(Path(dllName).absolute())  # Fix loader issues.

    use_ctypes = False
    if assume_same_bit_width:
        use_ctypes = True
    if use_ctypes:
        try:
            lib = ctypes.cdll.LoadLibrary(dllName)
        except OSError:
            logger.error(f"Could not load DLL '{dllName}' -- Probably an 64bit vs 32bit issue?")
            return (SeedNKeyResult.ERR_COULD_NOT_LOAD_DLL, None)
        func = lib.XCP_ComputeKeyFromSeed
        func.restype = ctypes.c_uint32
        func.argtypes = [
            ctypes.c_uint8,
            ctypes.c_uint8,
            ctypes.c_char_p,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.c_char_p,
        ]
        key_buffer = ctypes.create_string_buffer(b"\000" * 128)
        key_length = ctypes.c_uint8(128)
        ret_code = func(
            privilege,
            len(seed),
            ctypes.c_char_p(seed),
            ctypes.byref(key_length),
            key_buffer,
        )
        return (ret_code, key_buffer.raw[0 : key_length.value])
    else:
        try:
            p0 = subprocess.Popen(
                [LOADER, dllName, str(privilege), binascii.hexlify(seed).decode("ascii")],
                stdout=subprocess.PIPE,
                shell=False,
            )
        except FileNotFoundError as exc:
            logger.error(f"Could not find executable '{LOADER}' -- {exc}")
            return (SeedNKeyResult.ERR_COULD_NOT_LOAD_DLL, None)
        except OSError as exc:
            logger.error(f"Cannot execute {LOADER} -- {exc}")
            return (SeedNKeyResult.ERR_COULD_NOT_LOAD_DLL, None)
        key = p0.stdout.read()
        if not key:
            logger.error(f"Something went wrong while calling seed-and-key-DLL '{dllName}'")
            return (SeedNKeyResult.ERR_COULD_NOT_LOAD_DLL, None)
        res = re.split(b"\r?\n", key)
        returnCode = int(res[0])
        key = binascii.unhexlify(res[1])
    return (returnCode, key)

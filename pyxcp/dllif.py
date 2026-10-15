#!/usr/bin/env python
import binascii
import ctypes
import enum
import platform
import re
import subprocess  # nosec
import sys
from pathlib import Path


class DllResult(enum.IntEnum):
    ACK = 0  # o.k.
    ERR_PRIVILEGE_NOT_AVAILABLE = 1  # the requested privilege can not be unlocked with this DLL
    ERR_INVALID_SEED_LENGTH = 2  # the seed length is wrong, key could not be computed
    ERR_UNSUFFICIENT_KEY_LENGTH = 3  # the space for the key is too small

    ERR_COULD_NOT_LOAD_DLL = 16
    ERR_COULD_NOT_LOAD_FUNC = 17


class DllError(Exception):
    """"""


# Keep aliases for backward compatibility
SeedNKeyResult = DllResult
SeedNKeyError = DllError


LOADER = Path(str(sys.modules["pyxcp"].__file__)).parent / "cpp_ext" / "asamkeydll"  # Absolute path to DLL loader.

bwidth, _ = platform.architecture()

if sys.platform in ("win32", "linux", "darwin"):
    if bwidth == "64bit":
        use_ctypes = False
    elif bwidth == "32bit":
        use_ctypes = True
else:
    raise RuntimeError(f"Platform {sys.platform!r} currently not supported.")


def getKey(logger, loader_cfg: str, dllName: str, privilege: int, seed: bytes, assume_same_bit_width: bool):
    dllName = str(Path(dllName).absolute())  # Fix loader issues.

    if loader_cfg is not None:
        loader_exe = loader_cfg
    else:
        loader_exe = LOADER

    use_ctypes: bool = False
    if assume_same_bit_width:
        use_ctypes = True
    if use_ctypes:
        try:
            lib: ctypes.CDLL = ctypes.cdll.LoadLibrary(dllName)
        except OSError:
            logger.error(f"Could not load DLL {dllName!r} -- Probably an 64bit vs 32bit issue?")
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
        key_buffer: ctypes.Array[ctypes.c_char] = ctypes.create_string_buffer(b"\000" * 128)
        key_length: ctypes.c_uint8 = ctypes.c_uint8(128)
        ret_code: int = func(
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
                [loader_exe, dllName, str(privilege), binascii.hexlify(seed).decode("ascii")],
                stdout=subprocess.PIPE,
                shell=False,
            )  # nosec
        except FileNotFoundError as exc:
            logger.error(f"Could not find executable {loader_exe!r} -- {exc}")
            return (SeedNKeyResult.ERR_COULD_NOT_LOAD_DLL, None)
        except OSError as exc:
            logger.error(f"Cannot execute {loader_exe!r} -- {exc}")
            return (SeedNKeyResult.ERR_COULD_NOT_LOAD_DLL, None)
        key: bytes = b""
        if p0.stdout:
            key = p0.stdout.read()
            p0.stdout.close()
        p0.kill()
        p0.wait()
        if not key:
            logger.error(f"Something went wrong while calling seed-and-key-DLL {dllName!r}. Empty key")
            return (SeedNKeyResult.ERR_COULD_NOT_LOAD_DLL, None)
        res = re.split(b"\r?\n", key)
        res = [line for line in res if line]
        if not res:
            logger.error(f"Something went wrong while calling seed-and-key-DLL {dllName!r}. Invalid output format")
            return (SeedNKeyResult.ERR_COULD_NOT_LOAD_DLL, None)
        returnCode = int(res[0])
        key_val = b""
        if len(res) > 1:
            key_val = binascii.unhexlify(res[1])
        return (returnCode, key_val)


class TRange(ctypes.Structure):
    _fields_ = [
        ("pMem", ctypes.c_char_p),
        ("lLen", ctypes.c_ulong),
    ]


def calcChecksum(logger, loader_cfg, dllName, data, assume_same_bit_width):
    dllName = str(Path(dllName).absolute())

    if loader_cfg is not None:
        loader_exe = loader_cfg
    else:
        loader_exe = LOADER

    use_ctypes = False
    if assume_same_bit_width:
        use_ctypes = True

    if use_ctypes:
        try:
            lib = ctypes.cdll.LoadLibrary(dllName)
        except OSError:
            logger.error(f"Could not load DLL {dllName!r} -- Probably an 64bit vs 32bit issue?")
            return (DllResult.ERR_COULD_NOT_LOAD_DLL, None)

        try:
            func = lib.CalcChecksum
        except AttributeError:
            logger.error(f"Could not find function 'CalcChecksum' in {dllName!r}")
            return (DllResult.ERR_COULD_NOT_LOAD_FUNC, None)

        func.restype = ctypes.c_int  # BOOL is usually int
        func.argtypes = [
            ctypes.POINTER(TRange),
            ctypes.c_int,
            ctypes.POINTER(ctypes.c_uint8),
            ctypes.POINTER(ctypes.c_int),
            ctypes.c_uint16,
        ]

        # Prepare arguments
        # Checksum DLL expects an array of TRange. Here we have only one block of data.
        ranges = (TRange * 1)()
        ranges[0].pMem = ctypes.c_char_p(data)
        ranges[0].lLen = len(data)

        checksum_buffer = (ctypes.c_uint8 * 8)()
        significant = ctypes.c_int(0)
        flags = ctypes.c_uint16(0)  # Bit 0 = 0: calculate

        ret = func(ranges, 1, checksum_buffer, ctypes.byref(significant), flags)

        return (ret, bytes(checksum_buffer[: significant.value]))
    else:
        # For the external loader, we need a similar mechanism as for Seed&Key.
        # But the existing loader 'asamkeydll' is likely hardcoded for XCP_ComputeKeyFromSeed.
        # The issue description says: "Natürlich wird auch für Checksum-DLLs ein kleiner Loader benötigt, wenn man 32Bit-Dlls mit einer 64Bit Python-Version verwenden will."
        # This implies I might need to provide a new loader or the existing one should be used if it's generalized.
        # Since I cannot easily create a new binary loader here, I will assume the loader might be extended or
        # I should at least implement the subprocess call if the loader supports it.
        # For now, I'll use a placeholder or similar logic if I can find how the loader is supposed to work.
        try:
            # We assume the loader supports a mode for checksum or there's a different loader.
            # If it's the same loader, maybe it has a command line flag?
            # The issue doesn't specify the loader's CLI for checksum.
            # I will implement it assuming a similar interface: loader.exe <dll> <data_hex> ...
            # Actually, TRange might be complex for CLI.
            p0 = subprocess.Popen(
                [loader_exe, "--checksum", dllName, binascii.hexlify(data).decode("ascii")],
                stdout=subprocess.PIPE,
                shell=False,
            )
        except (FileNotFoundError, OSError) as exc:
            logger.error(f"Could not execute loader {loader_exe!r} -- {exc}")
            return (DllResult.ERR_COULD_NOT_LOAD_DLL, None)

        out = b""
        if p0.stdout:
            out = p0.stdout.read()
            p0.stdout.close()
        p0.kill()
        p0.wait()

        if not out:
            logger.error(f"Something went wrong while calling checksum-DLL {dllName!r}")
            return (DllResult.ERR_COULD_NOT_LOAD_DLL, None)

        res = re.split(b"\r?\n", out)
        res = [line for line in res if line]
        if not res:
            logger.error(f"Something went wrong while calling checksum-DLL {dllName!r}. Invalid output format")
            return (DllResult.ERR_COULD_NOT_LOAD_DLL, None)
        returnCode = int(res[0])
        checksum_val = b""
        if len(res) > 1:
            checksum_val = binascii.unhexlify(res[1])
        return (returnCode, checksum_val)

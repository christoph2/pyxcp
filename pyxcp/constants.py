#!/usr/bin/env python
import struct
from typing import Any, Callable


PackerType = Callable[[int], bytes]
UnpackerType = Callable[[bytes], tuple[Any, ...]]


def makeBytePacker(byteorder: str = "@") -> PackerType:
    """"""
    return struct.Struct(f"{byteorder}B").pack


def makeByteUnpacker(byteorder: str = "@") -> UnpackerType:
    """"""
    return struct.Struct(f"{byteorder}B").unpack


def makeWordPacker(byteorder: str = "@") -> PackerType:
    """"""
    return struct.Struct(f"{byteorder}H").pack


def makeWordUnpacker(byteorder: str = "@") -> UnpackerType:
    """"""
    return struct.Struct(f"{byteorder}H").unpack


def makeDWordPacker(byteorder: str = "@") -> PackerType:
    """"""
    return struct.Struct(f"{byteorder}I").pack


def makeDWordUnpacker(byteorder: str = "@") -> UnpackerType:
    """"""
    return struct.Struct(f"{byteorder}I").unpack


def makeDLongPacker(byteorder: str = "@") -> PackerType:
    """"""
    return struct.Struct(f"{byteorder}Q").pack


def makeDLongUnpacker(byteorder: str = "@") -> UnpackerType:
    """"""
    return struct.Struct(f"{byteorder}Q").unpack

#!/usr/bin/env python
# -*- coding: utf-8 -*-
import struct
from typing import Callable
from typing import NewType

PackerType = NewType("PackerType", Callable[[int], bytes])
UnpackerType = NewType("UnpackerType", Callable[[bytes], int])


def makeBytePacker(byteorder: str = "@") -> PackerType:
    """"""
    return struct.Struct("{}B".format(byteorder)).pack


def makeByteUnpacker(byteorder: str = "@") -> UnpackerType:
    """"""
    return struct.Struct("{}B".format(byteorder)).unpack


def makeWordPacker(byteorder: str = "@") -> PackerType:
    """"""
    return struct.Struct("{}H".format(byteorder)).pack


def makeWordUnpacker(byteorder: str = "@") -> UnpackerType:
    """"""
    return struct.Struct("{}H".format(byteorder)).unpack


def makeDWordPacker(byteorder: str = "@") -> PackerType:
    """"""
    return struct.Struct("{}I".format(byteorder)).pack


def makeDWordUnpacker(byteorder: str = "@") -> UnpackerType:
    """"""
    return struct.Struct("{}I".format(byteorder)).unpack


def makeDLongPacker(byteorder: str = "@") -> PackerType:
    """"""
    return struct.Struct("{}Q".format(byteorder)).pack


def makeDLongUnpacker(byteorder: str = "@") -> UnpackerType:
    """"""
    return struct.Struct("{}Q".format(byteorder)).unpack

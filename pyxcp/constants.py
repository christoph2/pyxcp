#!/usr/bin/env python
# -*- coding: utf-8 -*-
import struct


def makeBytePacker(byteorder="@"):
    """"""
    return struct.Struct("{}B".format(byteorder)).pack


def makeByteUnpacker(byteorder="@"):
    """"""
    return struct.Struct("{}B".format(byteorder)).unpack


def makeWordPacker(byteorder="@"):
    """"""
    return struct.Struct("{}H".format(byteorder)).pack


def makeWordUnpacker(byteorder="@"):
    """"""
    return struct.Struct("{}H".format(byteorder)).unpack


def makeDWordPacker(byteorder="@"):
    """"""
    return struct.Struct("{}I".format(byteorder)).pack


def makeDWordUnpacker(byteorder="@"):
    """"""
    return struct.Struct("{}I".format(byteorder)).unpack


def makeDLongPacker(byteorder="@"):
    """"""
    return struct.Struct("{}Q".format(byteorder)).pack


def makeDLongUnpacker(byteorder="@"):
    """"""
    return struct.Struct("{}Q".format(byteorder)).unpack

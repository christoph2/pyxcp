#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__="""
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2019 by Christoph Schueler <cpu12.gems@googlemail.com>

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

import json
import pytest

from pyxcp.config import Config

SxI_Parameters = {
    "port": "COM27",
    "baudrate": 115200,
    "mode": "ASYNCH_FULL_DUPLEX_MODE",
    "parity": "PARITY_NONE",    # PARITY_NONE | PARITY_ODD | PARITY_EVEN
    "stopbits": "ONE_STOP_BIT", # ONE_STOP_BIT | TWO_STOP_BITS
    "header": "HEADER_LEN_CTR_WORD",   # HEADER_LEN_BYTE | HEADER_LEN_CTR_BYTE | HEADER_LEN_FILL_BYTE | HEADER_LEN_WORD | HEADER_LEN_CTR_WORD | HEADER_LEN_FILL_WORD
    "checksum": "NO_CHECKSUM", #NO_CHECKSUM | CHECKSUM_BYTE | CHECKSUM_WORD
    "nested": {
        "RED": 1,
        "GREEN": 2,
        "BLUE": 3,
    }
}

def testCreation():
    cfg = Config(SxI_Parameters)
    assert cfg.port == "COM27"
    assert cfg.baudrate == 115200
    assert cfg.mode == "ASYNCH_FULL_DUPLEX_MODE"
    assert cfg.parity == "PARITY_NONE"
    assert cfg.stopbits == "ONE_STOP_BIT"
    assert cfg.header == "HEADER_LEN_CTR_WORD"
    assert cfg.checksum == "NO_CHECKSUM"
    assert cfg.nested.RED == 1
    assert cfg.nested.GREEN == 2
    assert cfg.nested.BLUE == 3

def testCopy():
    cfg = Config(SxI_Parameters)
    cfg2 = cfg.copy()
    assert cfg == cfg2

def testModifiedCopy():
    cfg = Config(SxI_Parameters)
    cfg2 = cfg.copy()
    cfg2.baudrate = 38400
    assert cfg != cfg2

def testComparesEqualToDict():
    cfg = Config(SxI_Parameters)
    di = cfg.asdict()
    assert cfg == di

def testComparesNotEqualToDict():
    cfg = Config(SxI_Parameters)
    di = cfg.asdict()
    di['baudrate'] = 38400
    assert cfg != di


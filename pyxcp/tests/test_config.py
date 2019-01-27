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

import json
import unittest

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

class TestConfig(unittest.TestCase):

    def testCreation(self):
        cfg = Config(SxI_Parameters)
        self.assertEqual(cfg.port , "COM27")
        self.assertEqual(cfg.baudrate , 115200)
        self.assertEqual(cfg.mode , "ASYNCH_FULL_DUPLEX_MODE")
        self.assertEqual(cfg.parity , "PARITY_NONE")
        self.assertEqual(cfg.stopbits , "ONE_STOP_BIT")
        self.assertEqual(cfg.header , "HEADER_LEN_CTR_WORD")
        self.assertEqual(cfg.checksum , "NO_CHECKSUM")
        self.assertEqual(cfg.nested.RED , 1)
        self.assertEqual(cfg.nested.GREEN , 2)
        self.assertEqual(cfg.nested.BLUE , 3)

    def testCopy(self):
        cfg = Config(SxI_Parameters)
        cfg2 = cfg.copy()
        self.assertEqual(cfg, cfg2)

    def testModifiedCopy(self):
        cfg = Config(SxI_Parameters)
        cfg2 = cfg.copy()
        cfg2.baudrate = 38400
        self.assertNotEqual(cfg, cfg2)

    def testComparesEqualToDict(self):
        cfg = Config(SxI_Parameters)
        di = cfg.asdict()
        self.assertEqual(cfg, di)

    def testComparesNotEqualToDict(self):
        cfg = Config(SxI_Parameters)
        di = cfg.asdict()
        di['baudrate'] = 38400
        self.assertNotEqual(cfg, di)


def main():
    unittest.main()

if __name__ == '__main__':
    main()


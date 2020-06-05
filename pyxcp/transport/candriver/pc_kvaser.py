#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
python-can driver for Kvaser interfaces.
"""

__copyright__="""
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2020 by Christoph Schueler <cpu12.gems@googlemail.com>

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

from can import Bus, CanError, Message

import pyxcp.transport.can as can

import pyxcp.transport.candriver.python_can as python_can


class Kvaser(python_can.PythonCAN, can.CanInterfaceBase):
    """
    """

    PARAMETER_MAP = {
        #                        Type    Req'd   Default
        "ACCEPT_VIRTUAL":       (bool,   False,  True),
        "DRIVER_MODE":          (bool,   False,  True),
        "NO_SAMP":              (int,    False,  1),
        "SJW":                  (int,    False,  2),
        "TSEG1":                (int,    False,  5),
        "TSEG2":                (int,    False,  2),
        "SINGLE_HANDLE":        (bool,   False,  True),
        "FD":                   (bool,   False,  False),
        "DATA_BITRATE":         (int,    False,  None),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "ACCEPT_VIRTUAL":         "accept_virtual",
        "TSEG1":                  "tseg1",
        "TSEG2":                  "tseg2",
        "SJW":                    "sjw",
        "NO_SAMP":                "no_samp",
        "DRIVER_MODE":            "driver_mode",
        "SINGLE_HANDLE":          "single_handle",
        "FD":                     "fd",
        "DATA_BITRATE":           "data_bitrate",
    }

    def __init__(self):
        super(Kvaser, self).__init__(bustype = "kvaser")

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
python-can driver for Vector Informatik interfaces.
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


class Vector(python_can.PythonCAN, can.CanInterfaceBase):
    """
    """

    PARAMETER_MAP = {
        #                        Type    Req'd   Default
        "POLL_INTERVAL":        (float,  False,  0.01),
        "APP_NAME":             (str,    False,  ""),
        "SERIAL":               (int,    False,  None),
        "RX_QUEUE_SIZE":        (int,    False, 16384),
        "FD":                   (bool,   False,  False),
        "DATA_BITRATE":         (int,    False,  None),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "POLL_INTERVAL":          "poll_interval",
        "RX_QUEUE_SIZE":          "rx_queue_size",
        "FD":                     "fd",
        "DATA_BITRATE":           "data_bitrate",
        "APP_NAME":               "app_name",
        "SERIAL":                 "serial",
    }

    def __init__(self):
        super(Vector, self).__init__(bustype = "vector")

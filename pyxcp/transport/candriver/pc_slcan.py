#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
python-can driver for CAN over Serial (like Lawicel)  interfaces.
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


class SlCan(python_can.PythonCAN, can.CanInterfaceBase):
    """
    """

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "TTY_BAUDRATE":             (int,   False,  115200),
        "POLL_INTERVAL":            (float, False,  0.01),
        "SLEEP_AFTER_OPEN":         (float, False,  2.0),
        "RTSCTS":                   (bool,  False,  False),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "TTY_BAUDRATE":                 "ttyBaudrate",
        "POLL_INTERVAL":                "poll_interval",
        "SLEEP_AFTER_OPEN":             "sleep_after_open",
        "RTSCTS":                       "rtscts",
    }

    def __init__(self):
        super(SlCan, self).__init__(bustype = "slcan")

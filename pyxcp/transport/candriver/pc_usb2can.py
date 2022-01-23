#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for 8devices USB2CAN interfaces.
"""

__copyright__ = """
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

import pyxcp.transport.can as can

import pyxcp.transport.candriver.python_can as python_can


class Usb2Can(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "FLAGS": (int, False, 0),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "FLAGS": "flags",
    }

    """

    :param int flags:
        Flags to directly pass to open function of the usb2can abstraction layer.

    """

    def __init__(self):
        super(Usb2Can, self).__init__(bustype="usb2can")

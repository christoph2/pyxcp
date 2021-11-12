#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
python-can driver for ICS NeoVi interfaces.
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


class Neovi(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "FD": (bool, False, False),
        "DATA_BITRATE": (int, False, None),
        "USE_SYSTEM_TIMESTAMP": (bool, False, False),
        "SERIAL": (str, False, None),
        "OVERRIDE_LIBRARY_NAME": (str, False, None),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "FD": "fd",
        "DATA_BITRATE": "data_bitrate",
        "USE_SYSTEM_TIMESTAMP": "use_system_timestamp",
        "SERIAL": "serial",
        "OVERRIDE_LIBRARY_NAME": "override_library_name",
    }

    def __init__(self):
        super(Neovi, self).__init__(bustype="neovi")

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Top-level package file.
"""

import sys

from .master import Master
from .transport import Eth, SxI, Usb


__copyright__ = """
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
from .version import __version__

VERSION = sys.version_info
PY36_OR_HIGHER = VERSION.major >= 3 and VERSION.minor >= 6

if PY36_OR_HIGHER:
    # only import can transport with Python 3.6 or higher because it uses
    # variable annotations (introduced in 3.6 - PEP526)
    from .transport import Can

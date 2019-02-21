#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

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

import inspect
import functools

from pyxcp.types import XcpResponseError, XcpTimeoutError


def wrapped(fun):
    """WIP: This decorator will do XCP error-handling.
    """
    @functools.wraps(fun)
    def inner(*args, **kwargs):
        try:
            inst = args[0] # First parameter is 'self'.
            res = fun(*args, **kwargs)
        except XcpResponseError as e:
            #print("SERV", inst.service)
            raise
        except XcpTimeoutError as e:
            #print("SERV", inst.service)
            raise
        except Exception:
            raise
        else:
            return res
    return inner

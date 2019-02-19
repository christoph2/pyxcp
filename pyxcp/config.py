#!/usr/bin/env python
# -*- coding: utf-8 -*-

__copyright__ = """
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

import copy
import json


class ConfigBase:

    _header = ""
    _footer = ""

    def __str__(self):
        indent = " " * (4 * self._level)
        result = []
        for attr in self._attrs:
            value = getattr(self, attr)
            if not isinstance(value, (int, float, Attribute)):
                value = '"{}"'.format(value)
            result.append('{}"{}": {}'.format(indent, attr, value))
        indent = " " * (4 * (self._level - 1))
        return "{}{{\n{}\n{}}}{}".format(
            self._header, ',\n'.join(result), indent, self._footer)

    def asdict(self):
        return json.loads(str(self))


class Attribute(ConfigBase):
    pass


class Config(ConfigBase):
    """
    """

    def __init__(self, params):
        self._addAttrs(params, self)

    def _addAttrs(self, attrs, obj, level=1):
        obj._attrs = []
        obj._nested = []
        obj._level = level
        for attr, value in attrs.items():
            if isinstance(value, dict):
                obj._nested.append(attr)
                target = Attribute()
                setattr(obj, attr, target)
                self._addAttrs(value, target, level + 1)
            else:
                setattr(obj, attr, value)
            obj._attrs.append(attr)

    def __eq__(self, other):
        if isinstance(other, dict):
            return self.asdict() == other
        else:
            return self.asdict() == other.asdict()

    def copy(self):
        return copy.copy(self)

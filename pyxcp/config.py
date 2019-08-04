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
import pathlib

try:
    import toml
except ImportError:
    HAS_TOML = False
else:
    HAS_TOML = True

def readConfiguration(conf):
    """Read a configuration file, either in JSON or TOML format.
    """
    if conf:
        pth = pathlib.Path(conf.name)
        suffix = pth.suffix.lower()
        if suffix == '.json':
            reader = json
        elif suffix == '.toml' and HAS_TOML:
            reader = toml
        else:
            reader = None
        if reader:
            return reader.loads(conf.read())
        else:
            return {}
    else:
        return {}


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


class Configuration:

    def __init__(self, parameters, config):
        self.parameters = parameters
        self.config = config
        print(self.config)

        for key, (attr, tp, required, default) in self.parameters.items():
            print(key, attr, tp)
            if key in self.config:
            #if hasattr(self.config, key):
                if not isinstance(getattr(self.config, key), tp):
                    raise TypeError("Parameter {} {} required".format(attr, tp))
                #setattr(self, attr, getattr(obj.config, key))
                print("Setting {} to {}".format(attr, getattr(self.config, key)))
            else:
                if required:
                    raise AttributeError("{} must be specified in config!".format(key))
                else:
                    #setattr(obj, attr, default)
                    print("Using default {} for {}".format(attr, default))


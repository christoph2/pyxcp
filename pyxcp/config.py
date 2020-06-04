#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

import json
import pathlib

try:
    import toml
except ImportError:
    HAS_TOML = False
else:
    HAS_TOML = True


def readConfiguration(conf):
    """Read a configuration file either in JSON or TOML format.
    """
    if conf:
        if isinstance(conf, dict):
            return dict(conf)
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


class Configuration:
    """

    """

    def __init__(self, parameters, config):
        self.parameters = parameters
        self.config = config
        for key, (tp, required, default) in self.parameters.items():
            if key in self.config:
                if not isinstance(self.config[key], tp):
                    raise TypeError(
                        "Parameter {} requires {}".format(key, tp))
            else:
                if required:
                    raise AttributeError(
                        "{} must be specified in config!".format(key))
                else:
                    self.config[key] = default

    def get(self, key):
        return self.config.get(key)

    def __repr__(self):
        return "{}".format(self.config)

    __str__ = __repr__

#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parse (transport-layer specific) command line parameters
and create a XCP master instance.
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

import argparse

from pyxcp.config import readConfiguration
from pyxcp.master import Master
from pyxcp.transport.can import (try_to_install_system_supplied_drivers, registered_drivers)

try_to_install_system_supplied_drivers()

CAN_DRIVERS = registered_drivers()


class ArgumentParser:
    """

    Parameter
    ---------
    callout: callable
        Process user-supplied arguments.
    """

    def __init__(self, callout = None, *args, **kws):
        self.callout = callout
        kws.update(formatter_class = argparse.RawDescriptionHelpFormatter, add_help = True)
        self._parser = argparse.ArgumentParser(*args, **kws)
        self._parser.add_argument('-c', '--config-file', type=argparse.FileType('r'), dest = "conf",
            help = 'File to read (extended) parameters from.')
        self._parser.add_argument('-l', '--loglevel', choices = ["ERROR", "WARN", "INFO", "DEBUG"], default = "INFO")
        self._parser.epilog = "To get specific help on transport layers\nuse <layer> -h, e.g. {} eth -h".format(self._parser.prog)
        self._args = []

    @property
    def args(self):
        return self._args

    def run(self):
        """

        """
        self._args = self.parser.parse_args()
        args = self.args
        config = readConfiguration(args.conf)
        config["LOGLEVEL"] = args.loglevel
        if not "TRANSPORT" in config:
            raise AttributeError("TRANSPORT must be specified in config!")
        transport = config['TRANSPORT'].lower()
        master = Master(transport, config = config)
        if self.callout:
            self.callout(master, args)
        return master

    @property
    def parser(self):
        return self._parser

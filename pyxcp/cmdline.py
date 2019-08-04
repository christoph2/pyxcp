#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
Parse (transport-layer specific) command line parameters
and create a XCP master instance.

.. note::
    There is currently no interface for further customization.

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


import argparse
import json
import pathlib

from pprint import pprint

try:
    import toml
except ImportError:
    HAS_TOML = False
else:
    HAS_TOML = True

from pyxcp.master import Master
from pyxcp.transport.can import CanInterfaceBase, Can, register_drivers
from pyxcp.transport import Eth
from pyxcp.transport import SxI


CAN_DRIVERS = register_drivers()


ARGUMENTS = {
    "can": ("canInterface", "loglevel"),
    "eth": ("host", "port", "protocol", "ipv6", "loglevel"),
    "sxi": ("port", "baudrate", "bytesize", "parity", "stopbits", "loglevel"),
}


def makeNonNullValuesDict(**params):
    """Only add items with non-None values.
    """
    return {k: v for k, v in params.items() if not v is None}


def readConfiguration(conf):
    """

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


def mergeParameters(transport, config, params):
    """Merge parameters from config-file and command-line.
    The latter have precedence.
    """
    args = ARGUMENTS.get(transport)
    result = {}
    for arg in args:
        cvalue = config.get(arg.upper())
        if cvalue:
            result[arg] = cvalue
        pvalue = params.get(arg)
        if pvalue:
            result[arg] = pvalue
    return result


def removeParameters(transport, config):
    """Remove constructor parameters from configuration.

    """
    stoplist = [arg.upper() for arg in ARGUMENTS.get(transport)]
    return {k: v for k, v in config.items() if not k in stoplist}


class ArgumentParser:
    """

    """

    def __init__(self, *args, **kws):
        kws.update(formatter_class = argparse.RawDescriptionHelpFormatter)
        self.parser = argparse.ArgumentParser(*args, **kws)
        subparsers = self.parser.add_subparsers(dest = "transport")
        subparsers.help = "Transport layer"
        self.parser.add_argument('-c', '--config-file', type=argparse.FileType('r'), dest = "conf",
            help = 'File to read (extended) parameters from.')
        self.parser.add_argument('-l', '--loglevel', choices = ["ERROR", "WARN", "INFO", "DEBUG"])
        self.parser.epilog = "To get specific help on transport layers\nuse <layer> -h, e.g. {} eth -h".format(self.parser.prog)

        eth = subparsers.add_parser("eth", description = "XCPonEth specific options:")
        eth.set_defaults(eth = True)
        sxi = subparsers.add_parser("sxi", description = "XCPonSxI specific options:")
        sxi.set_defaults(sxi = True)
        # TODO: conditionally add CAN options (only if at least one driver available")
        can = subparsers.add_parser("can", description = "XCPonCAN specific options:")
        can.set_defaults(can = True)

        can.add_argument('-d', '--driver', choices = CAN_DRIVERS.keys())

        eth.add_argument('-p', '--port', type = int, metavar = "port")
        proto = eth.add_mutually_exclusive_group()
        proto.add_argument('-t', '--tcp', default = True, const = True, metavar = "tcp", action = "store_const")
        proto.add_argument('-u', '--udp', default = False, const = True, metavar = "udp", action = "store_const")

        eth.add_argument('-6', '--ipv6', const = True, metavar = "ipv6", action = "store_const")
        eth.add_argument('-H', '--host', help = "Host name or IP.")

        sxi.add_argument('-p', '--port', help = "Name or number of your serial interface.")
        sxi.add_argument('-b', '--baudrate', type = int)
        sxi.add_argument('--bytesize', type = int)
        sxi.add_argument('--parity', choices = ['N', 'E', 'O'])
        sxi.add_argument('--stopbits', type = int, choices = [1, 2])
        self._args = []


    def run(self):
        """

        """
        self._args = self.parser.parse_args()
        args = self.args
        config = readConfiguration(args.conf)
        transport = args.transport
        if not transport:
            print("missing argument transport: choose from {}".format(['can', 'eth', 'sxi']))
            exit(1)
        if transport == "eth":
            params = makeNonNullValuesDict(
                host = args.host,
                port = args.port,
                protocol = "UDP" if args.udp else "TCP",
                ipv6 = args.ipv6,
                loglevel = args.loglevel)
            Klass = Eth
        elif transport == "sxi":
            params = makeNonNullValuesDict(
                port = args.port,
                baudrate = args.baudrate,
                bytesize = args.bytesize,
                parity = args.parity,
                stopbits = args.stopbits,
                loglevel = args.loglevel)
            klass = SxI
        elif transport == "can":
            if not args.driver in CAN_DRIVERS:
                print("missing argument CAN driver: choose from {}".format([x for x in CAN_DRIVERS.keys()]))
                exit(1)
            driver = CAN_DRIVERS[args.driver]
            params = dict(
                loglevel = args.loglevel,
                canInterface = driver
            )
            Klass = Can
        params = mergeParameters(transport, config, params)
        config = removeParameters(transport, config)
        params.update(config = config)
        tr = Klass(**params)
        return Master(tr)

    @property
    def args(self):
        return self._args

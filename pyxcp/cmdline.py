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

from pyxcp.master import Master
from pyxcp.transport import Eth
from pyxcp.transport import SxI


class ArgumentParser:
    """

    """

    def __init__(self, *args, **kws):
        kws.update(formatter_class = argparse.RawDescriptionHelpFormatter)
        self.parser = argparse.ArgumentParser(*args, **kws)
        subparsers = self.parser.add_subparsers(dest = "transport")
        subparsers.help = "Transport layer"
        self.parser.add_argument('-l', '--loglevel', default = "WARN", choices = ["ERROR", "WARN", "INFO", "DEBUG"])
        self.parser.epilog = "To get specific help on transport layers\nuse <layer> -h, e.g. {} eth -h".format(self.parser.prog)

        eth = subparsers.add_parser("eth", description = "XCPonEth specific options:")
        eth.set_defaults(eth = True)
        sxi = subparsers.add_parser("sxi", description = "XCPonSxI specific options:")
        sxi.set_defaults(sxi = True)
        can = subparsers.add_parser("can", description = "XCPonCAN specific options:")
        can.set_defaults(can = True)

        eth.add_argument('-p', '--port', default = 5555, type = int, metavar = "port")
        proto = eth.add_mutually_exclusive_group()
        proto.add_argument('-t', '--tcp', default = True, const = True, metavar = "tcp", action = "store_const")
        proto.add_argument('-u', '--udp', default = False, const = True, metavar = "udp", action = "store_const")
        eth.add_argument('-6', '--ipv6', default = False, const = True, metavar = "ipv6", action = "store_const")
        eth.add_argument('-H', '--host', default = "localhost", help = "Host name or IP.")

        sxi.add_argument('-p', '--port', required = True, help = "Name or number of your serial interface.")
        sxi.add_argument('-b', '--baudrate', default = 9600, type = int)
        sxi.add_argument('--bytesize', default = 8, type = int)
        sxi.add_argument('--parity', default = "N", choices = ['N', 'E', 'O'])
        sxi.add_argument('--stopbits', default = 1, type = int, choices = [1, 2])
        self._args = []

    def run(self):
        self._args = self.parser.parse_args()
        args = self.args
        transport = args.transport
        if not transport:
            print("missing argument transport: choose from {}".format(['can', 'eth', 'sxi']))
            exit(1)
        if transport == "eth":
            if args.host.lower() == "localhost":
                ipAddress = "::1" if args.ipv6 else "localhost"
            else:
                ipAddress = args.host
            params = dict(
                ipAddress = ipAddress,
                port = args.port,
                loglevel = args.loglevel,
                ipv6 = args.ipv6,
                protocol = "UDP" if args.udp else "TCP")
            tr = Eth(**params)
        elif transport == "sxi":
            params = dict(
                portName = args.port,
                baudrate = args.baudrate,
                bytesize = args.bytesize,
                parity = args.parity,
                stopbits = args.stopbits
                )
            tr = SxI(**params)
        elif transport == "can":
            raise NotImplementedError("No CAN support for now.")
        return Master(tr)

    @property
    def args(self):
        return self._args

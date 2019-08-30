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


from pyxcp.config import readConfiguration
from pyxcp.master import Master
from pyxcp.transport.can import (try_to_install_system_supplied_drivers, registered_drivers)

try_to_install_system_supplied_drivers()

CAN_DRIVERS = registered_drivers()


CMD_LINE_ARGUMENTS = {
    "can": ("CAN_DRIVER", "LOGLEVEL"),
    "eth": ("HOST", "PORT", "PROTOCOL", "IPV6", "LOGLEVEL"),
    "sxi": ("PORT", "BAUDRATE", "BYTESIZE", "PARITY", "STOPBITS", "LOGLEVEL"),
}

def merge_parameters(transport, params_from_cfg_file, params_from_cmd_line):
    """Merge parameters from config-file and command-line.
    The latter have precedence.

    Parameters
    ----------
    params_from_cfg_file: dict

    params_from_cmd_line: dict

    Returns
    -------
    dict
    """
    args = CMD_LINE_ARGUMENTS.get(transport)
    params_from_cmd_line = {k.upper(): v for k, v in params_from_cmd_line.items()}
    result = {}
    for arg in args:
        cvalue = params_from_cfg_file.get(arg)
        if cvalue:
            result[arg] = cvalue
        pvalue = params_from_cmd_line.get(arg)
        if pvalue:
            result[arg] = pvalue
    return result



def makeNonNullValuesDict(**params):
    """Only add items with non-None values.
    """
    return {k: v for k, v in params.items() if not v is None}


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

        can.add_argument('-d', '--driver', choices = CAN_DRIVERS.keys(), dest = "can_driver")

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
        elif transport == "sxi":
            params = makeNonNullValuesDict(
                port = args.port,
                baudrate = args.baudrate,
                bytesize = args.bytesize,
                parity = args.parity,
                stopbits = args.stopbits,
                loglevel = args.loglevel)
        elif transport == "can":
            if not args.can_driver in CAN_DRIVERS:
                print("missing argument CAN driver (-d <driver>): choose from {}".format([x for x in CAN_DRIVERS.keys()]))
                exit(1)
            params = dict(
                loglevel = args.loglevel,
                can_driver = args.can_driver
            )

        params = merge_parameters(transport, config, params)
        config.update(params)
        return Master(transport, config = config)

    @property
    def args(self):
        return self._args


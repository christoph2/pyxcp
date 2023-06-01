#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
Parse (transport-layer specific) command line parameters
and create a XCP master instance.
"""
import argparse

from pyxcp.config import readConfiguration
from pyxcp.master import Master
from pyxcp.transport.can import registered_drivers
from pyxcp.transport.can import try_to_install_system_supplied_drivers

try_to_install_system_supplied_drivers()

CAN_DRIVERS = registered_drivers()


class ArgumentParser:
    """

    Parameter
    ---------
    callout: callable
        Process user-supplied arguments.
    """

    def __init__(self, callout=None, *args, **kws):
        self.callout = callout
        kws.update(formatter_class=argparse.RawDescriptionHelpFormatter, add_help=True)
        self._parser = argparse.ArgumentParser(*args, **kws)
        self._parser.add_argument(
            "-c",
            "--config-file",
            type=argparse.FileType("r"),
            dest="conf",
            help="File to read (extended) parameters from.",
        )
        self._parser.add_argument(
            "-l",
            "--loglevel",
            choices=["ERROR", "WARN", "INFO", "DEBUG"],
            default="INFO",
        )
        self._parser.epilog = "To get specific help on transport layers\nuse <layer> -h, e.g. {} eth -h".format(self._parser.prog)
        self._args = []

    @property
    def args(self):
        return self._args

    def run(self, policy=None):
        """"""
        self._args = self.parser.parse_args()
        args = self.args
        if args.conf is None:
            raise RuntimeError("Configuration file must be specified! (option: -c <file>)")
        config = readConfiguration(args.conf)
        config["LOGLEVEL"] = args.loglevel
        if "TRANSPORT" not in config:
            raise AttributeError("TRANSPORT must be specified in config!")
        transport = config["TRANSPORT"].lower()
        master = Master(transport, config=config, policy=policy)
        if self.callout:
            self.callout(master, args)
        return master

    @property
    def parser(self):
        return self._parser

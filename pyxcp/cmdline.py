#!/usr/bin/env python
"""
Parse (transport-layer specific) command line parameters
and create a XCP master instance.
"""

import warnings
from dataclasses import dataclass
from typing import List

from pyxcp.config import create_application
from pyxcp.master import Master


warnings.simplefilter("always")


@dataclass
class Option:
    short_opt: str
    long_opt: str = ""
    dest: str = ""
    help: str = ""
    type: str = ""
    default: str = ""


class FakeParser:

    options: List[Option] = []

    def add_argument(self, short_opt: str, long_opt: str = "", dest: str = "", help: str = "", type: str = "", default: str = ""):
        warnings.warn("Argument parser extension is currently not supported.", DeprecationWarning, 2)
        self.options.append(Option(short_opt, long_opt, dest, help, type, default))


class ArgumentParser:
    def __init__(self, callout=None, *args, **kws):
        self._parser = FakeParser()
        if callout is not None:
            warnings.warn("callout  argument is currently not supported.", DeprecationWarning, 2)

    def run(self, policy=None, transport_layer_interface=None):
        application = create_application(self.parser.options)
        master = Master(
            application.transport.layer, config=application, policy=policy, transport_layer_interface=transport_layer_interface
        )
        return master

    @property
    def parser(self):
        return self._parser

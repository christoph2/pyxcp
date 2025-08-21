#!/usr/bin/env python
"""
Parse (transport-layer specific) command line parameters
and create a XCP master instance.
"""

import warnings
from dataclasses import dataclass
from typing import List

from pyxcp.config import (  # noqa: F401
    create_application,
    get_application,
    reset_application,
)
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
    action: str = ""


class FakeParser:
    """Parser that collects arguments for later processing."""

    def __init__(self):
        self.options = []

    def add_argument(self, short_opt, long_opt="", dest="", help="", type=None, default=None, action=None):
        """Collect argument definitions without issuing warnings."""
        self.options.append(Option(short_opt, long_opt, dest, help, type, default, action))


class ArgumentParser:
    """Argument parser for pyXCP applications.

    This class provides a way to add custom command-line arguments to pyXCP applications.
    It also supports a callout function that will be called with the master instance and
    the parsed arguments.
    """

    def __init__(self, callout=None, description=None, *args, **kws):
        self._parser = FakeParser()
        self._callout = callout
        self._description = description

    def run(self, policy=None, transport_layer_interface=None):
        """Create and configure a master instance.

        Args:
            policy: Optional policy to use for the master
            transport_layer_interface: Optional transport layer interface to use

        Returns:
            A configured master instance
        """
        # Create the application with custom arguments and callout
        application = get_application(self.parser.options, self._callout)

        # Create the master instance
        master = Master(
            application.transport.layer, config=application, policy=policy, transport_layer_interface=transport_layer_interface
        )

        # If there's a callout function, call it with the master and args
        if application.callout is not None and hasattr(application, "custom_args"):
            args = application.custom_args.get_args()
            application.callout(master, args)

        return master

    @property
    def parser(self):
        return self._parser

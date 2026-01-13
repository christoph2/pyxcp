#!/usr/bin/env python
"""
Parse (transport-layer specific) command line parameters
and create a XCP master instance.
"""

import argparse
import warnings

from pyxcp.config import (  # noqa: F401
    create_application,
    get_application,
    reset_application,
)
from pyxcp.master import Master
from pyxcp.utils.cli import StrippingParser


warnings.simplefilter("always")


class ArgumentParser:
    """Argument parser for pyXCP applications.

    This class provides a way to add custom command-line arguments to pyXCP applications.
    It also supports a callout function that will be called with the master instance and
    the parsed arguments.
    """

    def __init__(self, user_parser=None, description=None, *args, **kws):
        if isinstance(user_parser, argparse.ArgumentParser):
            self._parser = StrippingParser(user_parser)
            self._callout = None
        else:
            # Create a default parser. user_parser might be a callout function or None.
            parser = argparse.ArgumentParser(description=description)
            self._parser = StrippingParser(parser)
            self._callout = user_parser
        self._description = description
        self.args = self._parser.parse_and_strip()

    def run(self, policy=None, transport_layer_interface=None):
        """Create and configure a synchronous master instance.

        Args:
            policy: Optional policy to use for the master
            transport_layer_interface: Optional transport layer interface to use

        Returns:
            A configured master instance
        """
        # Create the application with custom arguments and callout
        application = get_application(options=[], callout=self._callout)

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
        return self._parser.parser

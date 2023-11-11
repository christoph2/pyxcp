#!/usr/bin/env python
"""
Parse (transport-layer specific) command line parameters
and create a XCP master instance.
"""
import warnings

from pyxcp.config import create_application
from pyxcp.master import Master


warnings.simplefilter("always")


class FakeParser:
    def __getattr__(self, key):
        if key == "add_argument":
            warnings.warn("Argument parser extension is currently not supported.", DeprecationWarning)
        return lambda *args, **kws: None


class ArgumentParser:
    def __init__(self, callout=None, *args, **kws):
        self._parser = FakeParser()
        if callout is not None:
            warnings.warn("callout  argument is not supported anymore", DeprecationWarning)

    def run(self, policy=None):
        application = create_application()
        transport = application.transport.layer
        master = Master(transport, config=application, policy=policy)
        return master

    @property
    def parser(self):
        return self._parser

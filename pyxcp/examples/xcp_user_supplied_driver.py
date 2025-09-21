#!/usr/bin/env python

from typing import Dict, List, Optional

import can

from pyxcp.cmdline import ArgumentParser
from pyxcp.transport.can import CanInterfaceBase


class CustomCANInterface(CanInterfaceBase):

    def init(self):
        """Initialize the CAN interface here."""

    def set_filters(self, filters):
        print(f"set_filters({filters})")
        self._filters = filters

    def recv(self, timeout: Optional[float] = None) -> Optional[can.message.Message]:
        """Receive CAN frames."""
        return can.message.Message()

    def send(self, msg: can.message.Message):
        """Send CAN frames."""
        print(f"send({msg})")

    @property
    def filters(self):
        """Return the current CAN filters."""
        return self._filters

    @property
    def state(self):
        """Return the current state of the CAN interface."""
        return can.BusState.ACTIVE


custom_interface = CustomCANInterface()

ap = ArgumentParser(description="User supplied CAN driver.")
with ap.run(transport_layer_interface=custom_interface) as x:
    x.connect()
    x.disconnect()

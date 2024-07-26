#!/usr/bin/env python
"""User supplied CAN driver.

Run as:

.. code-block:: shell

    python xcp_user_supplied_driver.py -c conf_can_user.toml
"""
from pyxcp.cmdline import ArgumentParser
from pyxcp.transport.can import CanInterfaceBase


class MyCI(CanInterfaceBase):
    """

    Relevant options in your configuration file (e.g. conf_can_user.toml):

    TRANSPORT = "CAN"
    CAN_DRIVER = "MyCI"     # The name of your custom driver class.

    """

    def init(self, parent, receive_callback):
        self.parent = parent

    def connect(self):
        pass

    def close(self):
        pass

    def get_timestamp_resolution(self):
        pass

    def read(self):
        pass

    def transmit(self, payload: bytes):
        print("\tTX-PAYLOAD", payload)


ap = ArgumentParser(description="User supplied CAN driver.")
with ap.run() as x:
    x.connect()
    x.disconnect()

"""
This do-nothing example will output

    TX-PAYLOAD b'\xff\x00'

and then timeout (0xff is the service code for CONNECT_REQ).
"""

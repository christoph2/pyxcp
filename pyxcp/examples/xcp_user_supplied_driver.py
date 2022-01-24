#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""User supplied CAN driver.

Run as:

.. code-block:: shell

    python xcp_user_supplied_driver.py -c conf_can_user.toml
"""
from pyxcp.cmdline import ArgumentParser

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2020 by Christoph Schueler <cpu12.gems@googlemail.com>

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

    def getTimestampResolution(self):
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

#!/usr/bin/env python
"""
python-can driver for Linux SocketCAN interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class SocketCAN(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                      Type    Req'd   Default
        "FD": (bool, False, False),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "FD": "fd",
    }

    def __init__(self):
        super().__init__(bustype="socketcan")

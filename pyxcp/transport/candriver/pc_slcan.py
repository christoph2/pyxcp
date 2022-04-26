#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for CAN over Serial (like Lawicel)  interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class SlCan(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "TTY_BAUDRATE": (int, False, 115200),
        "POLL_INTERVAL": (float, False, 0.01),
        "SLEEP_AFTER_OPEN": (float, False, 2.0),
        "RTSCTS": (bool, False, False),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "TTY_BAUDRATE": "ttyBaudrate",
        "POLL_INTERVAL": "poll_interval",
        "SLEEP_AFTER_OPEN": "sleep_after_open",
        "RTSCTS": "rtscts",
    }

    def __init__(self):
        super(SlCan, self).__init__(bustype="slcan")

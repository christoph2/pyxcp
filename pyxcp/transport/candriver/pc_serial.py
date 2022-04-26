#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver serial port connected interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Serial(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "BAUDRATE": (int, False, 115200),
        "TIMEOUT": (float, False, 0.1),
        "RTSCTS": (bool, False, False),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "BAUDRATE": "baudrate",
        "TIMEOUT": "timeout",
        "RTSCTS": "rtscts",
    }

    def __init__(self):
        super(Serial, self).__init__(bustype="serial")

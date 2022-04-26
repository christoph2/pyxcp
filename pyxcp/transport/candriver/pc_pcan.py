#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for Peak System interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can

from can import BusState


class PCan(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "STATE": (BusState, False, BusState.ACTIVE),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "STATE": "state",
    }

    def __init__(self):
        super(PCan, self).__init__(bustype="pcan")

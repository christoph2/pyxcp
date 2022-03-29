#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for Systec interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Systec(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                      Type    Req'd   Default
        "DEVICE_NUMBER": (int, False, 255),
        "RX_BUFFER_ENTRIES": (int, False, 4096),
        "TX_BUFFER_ENTRIES": (int, False, 4096),
        "STATE": (str, False, "ACTIVE"),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "DEVICE_NUMBER": "device_number",
        "RX_BUFFER_ENTRIES": "rx_buffer_entries",
        "TX_BUFFER_ENTRIES": "tx_buffer_entries",
        "STATE": "state",
    }

    def __init__(self):
        super(Systec, self).__init__(bustype="systec")

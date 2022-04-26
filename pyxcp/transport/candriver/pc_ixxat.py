#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for Ixxat interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Ixxat(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "UNIQUE_HARDWARE_ID": (str, False, None),
        "RX_FIFO_SIZE": (int, False, 16),
        "TX_FIFO_SIZE": (int, False, 16),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "UNIQUE_HARDWARE_ID": "UniqueHardwareId",
        "RX_FIFO_SIZE": "rxFifoSize",
        "TX_FIFO_SIZE": "txFifoSize",
    }

    def __init__(self):
        super(Ixxat, self).__init__(bustype="ixxat")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for Vector Informatik interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Vector(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                        Type    Req'd   Default
        "POLL_INTERVAL": (float, False, 0.01),
        "APP_NAME": (str, False, ""),
        "SERIAL": (int, False, None),
        "RX_QUEUE_SIZE": (int, False, 16384),
        "FD": (bool, False, False),
        "DATA_BITRATE": (int, False, 0),
        "DATA_SAMPLE_POINT": (float, False, 0),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "POLL_INTERVAL": "poll_interval",
        "RX_QUEUE_SIZE": "rx_queue_size",
        "FD": "fd",
        "DATA_BITRATE": "data_bitrate",
        "APP_NAME": "app_name",
        "SERIAL": "serial",
    }

    def __init__(self):
        super(Vector, self).__init__(bustype="vector")

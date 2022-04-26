#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for Kvaser interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Kvaser(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                        Type    Req'd   Default
        "ACCEPT_VIRTUAL": (bool, False, True),
        "DRIVER_MODE": (bool, False, True),
        "NO_SAMP": (int, False, 1),
        "SJW": (int, False, 2),
        "TSEG1": (int, False, 5),
        "TSEG2": (int, False, 2),
        "SINGLE_HANDLE": (bool, False, True),
        "FD": (bool, False, False),
        "DATA_BITRATE": (int, False, None),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "ACCEPT_VIRTUAL": "accept_virtual",
        "TSEG1": "tseg1",
        "TSEG2": "tseg2",
        "SJW": "sjw",
        "NO_SAMP": "no_samp",
        "DRIVER_MODE": "driver_mode",
        "SINGLE_HANDLE": "single_handle",
        "FD": "fd",
        "DATA_BITRATE": "data_bitrate",
    }

    def __init__(self):
        super(Kvaser, self).__init__(bustype="kvaser")

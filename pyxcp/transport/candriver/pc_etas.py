#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for ETAS BOA interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Etas(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "FD": (bool, False, False),
        "DATA_BITRATE": (int, False, None),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "FD": "fd",
        "DATA_BITRATE": "data_bitrate",
    }

    def __init__(self):
        super(Etas, self).__init__(bustype="etas")

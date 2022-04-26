#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for CANalyst-II(+) by ZLG ZHIYUAN Electronics interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Canalystii(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "BAUD  ": (int, False, None),
        "TIMING0": (int, False, None),
        "TIMING1": (int, False, None),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "BAUD": "baud",
        "TIMING0": "Timing0",
        "TIMING1": "Timing1",
    }

    def __init__(self):
        super(Canalystii, self).__init__(bustype="canalystii")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for National Instruments xnet interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class NiXnet(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "LOG_ERRORS": (bool, False, False),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "LOG_ERRORS": "log_errors",
    }

    def __init__(self):
        super(NiXnet, self).__init__(bustype="nixnet")

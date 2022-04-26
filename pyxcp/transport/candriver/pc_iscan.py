#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for isCAN from Thorsis Technologies GmbH.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class IsCAN(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "POLL_INTERVAL": (float, False, 0.01),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "POLL_INTERVAL": "poll_interval",
    }

    def __init__(self):
        super(IsCAN, self).__init__(bustype="iscan")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for ICS NeoVi interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Neovi(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "FD": (bool, False, False),
        "DATA_BITRATE": (int, False, None),
        "USE_SYSTEM_TIMESTAMP": (bool, False, False),
        "SERIAL": (str, False, None),
        "OVERRIDE_LIBRARY_NAME": (str, False, None),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "FD": "fd",
        "DATA_BITRATE": "data_bitrate",
        "USE_SYSTEM_TIMESTAMP": "use_system_timestamp",
        "SERIAL": "serial",
        "OVERRIDE_LIBRARY_NAME": "override_library_name",
    }

    def __init__(self):
        super(Neovi, self).__init__(bustype="neovi")

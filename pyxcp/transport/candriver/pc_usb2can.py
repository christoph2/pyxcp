#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for 8devices USB2CAN interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class Usb2Can(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "FLAGS": (int, False, 0),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "FLAGS": "flags",
    }

    """

    :param int flags:
        Flags to directly pass to open function of the usb2can abstraction layer.

    """

    def __init__(self):
        super(Usb2Can, self).__init__(bustype="usb2can")

#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
python-can driver for CAN driver for Geschwister Schneider USB/CAN devices and bytewerk.org candleLight USB CAN interfaces.
"""
import pyxcp.transport.can as can
import pyxcp.transport.candriver.python_can as python_can


class GsUsb(python_can.PythonCAN, can.CanInterfaceBase):
    """"""

    """
    PARAMETER_MAP = {
        #                           Type    Req'd   Default
    }

    PARAMETER_TO_KW_ARG_MAP = {
    }
    """

    def __init__(self):
        super(GsUsb, self).__init__(bustype="gs_usb")

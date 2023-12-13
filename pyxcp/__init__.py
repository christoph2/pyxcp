#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Universal Calibration Protocol for Python"""
import sys

if sys.platform == "win32" and sys.version_info[:2] < (3, 11):
    # patch the time module with the high resolution alternatives
    try:
        from win_precise_time import sleep as wpsleep
        from win_precise_time import time as wptime

        import time

        time.sleep = wpsleep
        time.time = wptime

    except ImportError:
        pass


from .master import Master
from .transport import Can
from .transport import Eth
from .transport import SxI
from .transport import Usb

# if you update this manually, do not forget to update .bumpversion.cfg and pyproject.toml
__version__ = "0.21.9"

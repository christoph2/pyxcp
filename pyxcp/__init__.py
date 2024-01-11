#!/usr/bin/env python
"""Universal Calibration Protocol for Python"""
import sys

from rich import pretty
from rich.console import Console
from rich.traceback import install as tb_install


pretty.install()

from .master import Master  # noqa: F401, E402
from .transport import Can, Eth, SxI, Usb  # noqa: F401, E402


console = Console()
tb_install(show_locals=True, max_frames=3)  # Install custom exception handler.

if sys.platform == "win32" and sys.version_info[:2] < (3, 11):
    # patch the time module with the high resolution alternatives
    try:
        import time

        from win_precise_time import sleep as wpsleep
        from win_precise_time import time as wptime

        time.sleep = wpsleep
        time.time = wptime

    except ImportError:
        pass

# if you update this manually, do not forget to update .bumpversion.cfg
__version__ = "0.21.6"

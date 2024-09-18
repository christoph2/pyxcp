#!/usr/bin/env python
"""Universal Calibration Protocol for Python."""

from rich import pretty
from rich.console import Console
from rich.traceback import install as tb_install


pretty.install()

from .master import Master  # noqa: F401, E402
from .transport import Can, Eth, SxI, Usb  # noqa: F401, E402


console = Console()
tb_install(show_locals=True, max_frames=3)  # Install custom exception handler.

# if you update this manually, do not forget to update
# .bumpversion.cfg and pyproject.toml.
__version__ = "0.22.5"

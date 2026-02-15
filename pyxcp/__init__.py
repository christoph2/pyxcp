#!/usr/bin/env python
"""Universal Calibration Protocol for Python."""

import warnings

from rich import pretty
from rich.console import Console
from rich.traceback import install as tb_install


pretty.install()

from .master import Master  # noqa: F401, E402
from .transport import Can, Eth, SxI, Usb  # noqa: F401, E402


console = Console()
tb_install(show_locals=True, max_frames=3)  # Install custom exception handler.

# if you update this manually, do not forget to update
# pyproject.toml.
__version__ = "0.27.0"


# Deprecation warning for TOML config
def _check_toml_usage():
    """Check if TOML config is being used and warn."""
    import sys
    import os

    # Check if any .toml config files are being loaded
    toml_files = []
    for arg in sys.argv:
        if arg.endswith(".toml") or "config.toml" in arg.lower():
            toml_files.append(arg)

    # Check common config file locations
    common_paths = [
        "pyxcp_config.toml",
        "config.toml",
        "xcp_config.toml",
    ]
    for path in common_paths:
        if os.path.exists(path):
            toml_files.append(path)

    if toml_files:
        warnings.warn(
            "TOML configuration is deprecated and will be removed in pyxcp v1.0. "
            "Please migrate to the Traitlets-based configuration system. "
            f"Detected TOML files: {', '.join(toml_files)}\n"
            "See https://github.com/christoph2/pyxcp/blob/master/docs/configuration.rst for migration guide.",
            DeprecationWarning,
            stacklevel=2,
        )


# Only check once at import time, not on every use
try:
    _check_toml_usage()
except Exception:  # nosec B110
    # Don't crash if check fails - this is non-critical warning functionality
    pass

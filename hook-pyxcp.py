"""
PyInstaller hook for pyxcp

This hook ensures that all native extensions and data files are included
when bundling pyxcp with PyInstaller.

Usage:
    Place this file in the same directory as your main script, or in a
    hooks directory, and run:

    pyinstaller --additional-hooks-dir=. your_script.py

    Or specify in your .spec file:

    a = Analysis(
        ...
        hookspath=['path/to/hooks'],
        ...
    )
"""

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_data_files
import os
import sys

# Collect all native extensions (.pyd on Windows, .so on Unix)
binaries = collect_dynamic_libs("pyxcp")

# Collect data files if any
datas = collect_data_files("pyxcp", include_py_files=True)

# Hidden imports - these modules are loaded dynamically
hiddenimports = [
    # Core extensions
    "pyxcp.transport.transport_ext",
    "pyxcp.cpp_ext.cpp_ext",
    "pyxcp.daq_stim.stim",
    "pyxcp.recorder.rekorder",
    # Transport layers
    "pyxcp.transport.can",
    "pyxcp.transport.eth",
    "pyxcp.transport.sxi",
    "pyxcp.transport.usb_transport",
    "pyxcp.transport.base",
    # Config system
    "pyxcp.config",
    "pyxcp.config.models",
    "pyxcp.config.legacy",
    # Dependencies that might be missed
    "construct",
    "python_can",
    "serial",
    "usb",
    "traitlets",
    "pydantic",
]

# Additional excludes to reduce bundle size
excludes = [
    # Development tools
    "pytest",
    "IPython",
    "jupyter",
    # Documentation
    "sphinx",
    # Unused standard library modules
    "tkinter",
    "unittest",
    "distutils",
]

# Platform-specific handling
if sys.platform == "win32":
    # Windows: Include asamkeydll.exe if it exists
    try:
        import pyxcp

        pyxcp_dir = os.path.dirname(pyxcp.__file__)
        asamkeydll = os.path.join(pyxcp_dir, "asamkeydll.exe")
        if os.path.exists(asamkeydll):
            datas.append((asamkeydll, "pyxcp"))
    except ImportError:
        pass

# Print hook info for debugging
print(f"[pyxcp hook] Found {len(binaries)} native binaries")
print(f"[pyxcp hook] Found {len(datas)} data files")
print(f"[pyxcp hook] Added {len(hiddenimports)} hidden imports")

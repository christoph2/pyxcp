Platform Setup Guide
====================

pyXCP runs on Windows, Linux, and macOS. This guide covers platform-specific installation, C++ extension compilation, CAN driver setup, and common issues.

Quick Start by Platform
-----------------------

Windows::

   # Install Python 3.10+
   pip install pyxcp
   # For CAN: install vendor driver
   # For source builds: install Visual Studio Build Tools
   pip install pyxcp --no-binary pyxcp  # to force build

Linux (Ubuntu/Debian)::

   sudo apt update
   sudo apt install python3-pip python3-dev build-essential cmake
   pip install pyxcp
   sudo apt install can-utils
   sudo ip link set can0 up type can bitrate 500000

macOS::

   xcode-select --install
   brew install python@3.12
   pip3 install pyxcp
   # CAN options are limited; see CAN section

Windows Setup
-------------

Python installation: use Python 3.10+ from python.org; add to PATH; enable pip; consider disabling path length limit.

Verify::

   python --version
   pip --version

Install pyXCP (binary wheel recommended)::

   pip install pyxcp

Build from source::

   pip install pyxcp --no-binary pyxcp

C++ build tools:

1. Visual Studio Build Tools (workload "Desktop development with C++")
2. Includes MSVC, CMake, Windows SDK

Verify::

   where cl
   cmake --version

CAN drivers on Windows
~~~~~~~~~~~~~~~~~~~~~~

pyXCP uses python-can backends.

- Vector: install Vector drivers, then ``pip install python-can[vector]``; verify with ``pyxcp-probe-can-drivers``.
- PEAK PCAN: install driver + PCAN-View; ``pip install python-can[pcan]``.
- Kvaser: install CANlib SDK; ``pip install python-can[kvaser]``.
- IXXAT: install VCI; ``pip install python-can[ixxat]``.
- Virtual CAN: use python-can virtual backend.

Example config factory::

   def create_transport(parent):
       from pyxcp.transport.can import Can
       return Can(parent, can_interface="vector", can_channel=0,
                  can_id_master=0x700, can_id_slave=0x701, can_bitrate=500000)

Seed/Key DLLs (32→64-bit bridge)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Problem: OEM seed/key DLLs are often 32-bit while Python is 64-bit.

Solution: pyXCP includes ``asamkeydll.exe`` bridge. Ensure MinGW-w64 is installed if rebuilding is needed; configure ``SEED_KEY_DLL = "SeedNKeyXcp.dll"``.

Linux Setup
-----------

Dependencies::

   sudo apt update
   sudo apt install python3-pip python3-dev build-essential cmake libpython3-dev
   pip install pyxcp

SocketCAN example::

   sudo ip link set can0 up type can bitrate 500000
   pyxcp-probe-can-drivers

macOS Setup
-----------

Install Xcode Command Line Tools and Homebrew Python. Build tools (CMake) come with Homebrew. CAN support depends on vendor hardware; consult vendor docs.

Docker and CI/CD
----------------

- Use manylinux wheels on Linux where possible.
- For source builds in CI: install build-essential, cmake, python3-dev (Linux) or MSVC tools (Windows).

Troubleshooting
---------------

- Missing compiler: install platform build tools (MSVC, Xcode CLT, GCC/CMake).
- CAN not working: verify driver installation and interface name; use ``pyxcp-probe-can-drivers``.
- Firewall (Ethernet): allow Python on required ports or test on trusted network.

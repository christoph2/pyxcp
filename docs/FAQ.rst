FAQ - Frequently Asked Questions
================================

New to pyXCP? See :doc:`quickstart` for a 15-minute introduction.

Installation & Build Issues
---------------------------

``ModuleNotFoundError: No module named 'pyxcp.transport.transport_ext'``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This is a build issue where the C++ extensions weren't compiled correctly. Try these solutions in order:

1. Install from PyPI with pre-built wheels (recommended)::

     pip install --upgrade pip
     pip install pyxcp

2. If that fails, install build dependencies first:

   Ubuntu/Debian::

     sudo apt update
     sudo apt install build-essential cmake python3-dev libpython3-dev pybind11-dev
     pip install pyxcp

   Windows:

   - Install Visual Studio Build Tools (workload "Desktop development with C++")

     ``pip install pyxcp``

   macOS::

     brew install cmake pybind11
     pip install pyxcp

3. Build from source manually::

     git clone https://github.com/christoph2/pyxcp.git
     cd pyxcp
     python build_ext.py
     pip install -e .

Related issues: #240, #188, #199, #169

``FileNotFoundError: 'cmake'`` on Ubuntu 24.04
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

CMake is not installed. Install required build tools::

   sudo apt update
   sudo apt install build-essential cmake python3-dev libpython3-dev pybind11-dev
   cmake --version
   python3-config --libs

Then install pyxcp::

   pip install pyxcp

Related issues: #169

``UnboundLocalError: cannot access local variable 'libdir'`` during build
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The build system cannot find the Python development libraries. Install them::

   sudo apt install python3-dev libpython3-dev
   find /usr -name "libpython*.so"
   find /usr -name "libpython*.a"

If the second command returns nothing, the Python link library is missing. Install the appropriate ``python3.X-dev`` package for your Python version.

Related issues: #169

PyInstaller/py2exe: pyxcp module not found after bundling
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

PyInstaller needs to be told about the native extensions.

Option 1: hook file (recommended)::

   from PyInstaller.utils.hooks import collect_dynamic_libs

   binaries = collect_dynamic_libs('pyxcp')
   datas = [
       ('path/to/site-packages/pyxcp/*.pyd', 'pyxcp'),  # Windows
       ('path/to/site-packages/pyxcp/*.so', 'pyxcp'),   # Linux/macOS
   ]
   hiddenimports = [
       'pyxcp.transport.transport_ext',
       'pyxcp.cpp_ext.cpp_ext',
       'pyxcp.daq_stim.stim',
       'pyxcp.recorder.rekorder',
   ]

Build::

   pyinstaller --additional-hooks-dir=. your_script.py

Option 2: specify in ``.spec``::

   a = Analysis(
       ...
       hiddenimports=[
           'pyxcp.transport.transport_ext',
           'pyxcp.cpp_ext.cpp_ext',
           'pyxcp.daq_stim.stim',
           'pyxcp.recorder.rekorder',
       ],
       ...
   )

Related issues: #261, #203

Configuration
-------------

``getDaqInfo()`` fails or returns empty event channels
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

As of v0.26.x, ``getDaqInfo()`` treats optional DAQ services (e.g., ``GET_DAQ_PROCESSOR_INFO``, ``GET_DAQ_RESOLUTION_INFO``, ``GET_DAQ_EVENT_INFO``) defensively (Issue #253). The returned dict now includes ``valid`` flags for ``processor``, ``resolution``, and ``events`` to indicate whether data came from the slave or safe defaults. If ``processor``/``resolution`` are ``False``, supply trusted values via ``DaqProcessor.setup(daq_info_override=...)`` or abort—relying on defaults can lead to incomplete DAQ setup. If ``events`` is ``False``, the event list will be empty; you can still run DAQ if your configuration uses predefined events.

Related issues: #253

DaqToCsv fails with FileNotFoundError when running from Robot Framework
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

**Fixed in v0.26.4+.** ``DaqToCsv`` and other DAQ classes now work without requiring a configuration file.

Common causes:

- Different working directory in test runners
- Missing logger/config

Solutions:

1. Pass a logger explicitly (recommended)::

     import logging
     from pyxcp.daq_stim import DaqToCsv

     logger = logging.getLogger("my_daq_logger")
     logger.addHandler(logging.StreamHandler())
     logger.setLevel(logging.INFO)
     daq_policy = DaqToCsv(daq_lists, logger=logger)

2. Robot Framework::

     *** Settings ***
     Library  pyxcp.daq_stim

     *** Test Cases ***
     My DAQ Test
         ${logger} =  Get Logger  my_robot_logger
         ${daq_policy} =  Create DaqToCsv  ${daq_lists}  logger=${logger}

3. Set ``PYXCP_CONFIG`` (v0.26.5+)::

     export PYXCP_CONFIG=/absolute/path/to/pyxcp_conf.py

4. Programmatic configuration (v0.26.5+)::

     from pyxcp.config import create_application_from_config

     config = {"Transport": {"CAN": {"device": "socketcan", "channel": "can0", "bitrate": 500000}}}
     app = create_application_from_config(config)

Config file search order (v0.26.5+):

1. ``PYXCP_CONFIG`` env var (absolute path)
2. Current working directory
3. Script directory
4. User home ``~/.pyxcp/pyxcp_conf.py``

Related issues: #260

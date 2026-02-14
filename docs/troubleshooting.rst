Troubleshooting Guide
=====================

This guide helps diagnose and fix common pyXCP issues using a symptom-based approach. Start with the symptom you're experiencing and follow the decision tree.

**Quick Links:**

- :doc:`FAQ <FAQ>` - Specific questions and answers
- :doc:`platform_setup` - Platform-specific installation issues
- :doc:`cli_tools` - CLI tool troubleshooting
- :doc:`quickstart` - Getting started guide

Table of Contents
-----------------

1. `Connection Issues`_
2. `Import/Build Errors`_
3. `Configuration Problems`_
4. `DAQ Issues`_
5. `CAN Problems`_
6. `Performance Issues`_
7. `Error Messages Reference`_

----

Connection Issues
-----------------

Symptom: "Connection timeout" or "No response"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Decision Tree:**

1. **Check Transport Layer**

   **For Ethernet (TCP/UDP):**

   .. code:: bash

      # Can you ping the ECU?
      ping <ECU_IP>

   - ✅ **Yes** → Firewall issue (see below)
   - ❌ **No** → Network/ECU problem

     - Check ECU power and network cable
     - Verify IP address and subnet
     - Check network switch/router configuration

   **For CAN:**

   .. code:: bash

      # Linux: Is CAN interface up?
      ip link show can0

      # Windows: Can you see CAN traffic in vendor tool?
      # (Vector CANoe, PCAN-View, etc.)

   - ✅ **Yes** → Check CAN configuration (see `CAN Problems`_)
   - ❌ **No** → CAN interface not configured

     - Linux: ``sudo ip link set can0 up type can bitrate 500000``
     - Windows: Check driver installation with ``pyxcp-probe-can-drivers``

   **For USB:**

   .. code:: bash

      # Linux
      lsusb | grep -i <vendor>

      # Windows
      # Check Device Manager → Universal Serial Bus devices

   - ✅ **Visible** → Check permissions (Linux: see `USB Permissions`_)
   - ❌ **Not visible** → Hardware/driver issue

2. **Firewall Check** (Ethernet only)

   .. code:: bash

      # Linux: Temporarily disable firewall
      sudo ufw disable  # Ubuntu
      sudo systemctl stop firewalld  # RHEL/Fedora

      # Windows: Add Python to firewall exceptions
      netsh advfirewall firewall add rule name="Python XCP" dir=in action=allow program="C:\Path\To\python.exe" enable=yes

   - ✅ **Works after disabling** → Add permanent exception
   - ❌ **Still fails** → Check ECU XCP server

3. **Verify ECU XCP Server**

   - Is XCP running on the ECU?
   - Is XCP server on the correct port/channel?
   - Try different timeout: ``transport.timeout = 5.0``

**Common Solutions:**

.. code:: python

   # Increase timeout
   from pyxcp.transport.eth import Eth
   transport = Eth(parent, host="192.168.1.100", port=5555, protocol="TCP")
   transport.timeout = 5.0  # Default is 2.0

   # For CAN: Verify IDs
   from pyxcp.transport.can import Can
   transport = Can(parent,
                   can_interface="socketcan",
                   can_channel="can0",
                   can_id_master=0x700,  # Try scanning with xcp-id-scanner
                   can_id_slave=0x701)

**Related Issues:** #188, #262, #179

----

Symptom: "Protection status error" or "Access denied"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Resource (CAL/DAQ/STIM/PGM) is protected by seed/key.

**Solution:**

1. **Check protection status:**

   .. code:: bash

      xcp-info -t eth --config my_config.py --no-daq --no-pag

2. **Add seed/key DLL to configuration:**

   .. code:: python

      # pyxcp_conf.py
      def create_transport(parent):
          # ... transport config ...

      SEED_KEY_DLL = "path/to/SeedNKeyXcp.dll"

3. **For Windows 64-bit Python with 32-bit DLL:**

   - pyXCP automatically uses ``asamkeydll.exe`` bridge
   - Ensure ``asamkeydll.exe`` is in pyxcp installation directory
   - If missing, rebuild: ``gcc -m32 -o asamkeydll.exe asamkeydll.c``

**Related Issues:** #200, #212

----

Import/Build Errors
-------------------

Symptom: "ModuleNotFoundError: No module named 'pyxcp.transport.transport_ext'"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** C++ extensions not compiled or incompatible.

**Solution by Platform:**

**Windows:**

.. code:: powershell

   # Option 1: Install pre-built wheel (recommended)
   pip install --upgrade pip
   pip install pyxcp

   # Option 2: Build from source (requires MSVC)
   # Install Visual Studio Build Tools first
   pip install pyxcp --no-binary pyxcp

**Linux:**

.. code:: bash

   # Install build dependencies
   sudo apt install build-essential cmake python3-dev pybind11-dev

   # Reinstall
   pip uninstall pyxcp
   pip install pyxcp

**macOS:**

.. code:: bash

   # Install Xcode Command Line Tools
   xcode-select --install

   # Install dependencies via Homebrew
   brew install cmake pybind11

   # Reinstall
   pip install pyxcp

**Manual Build:**

.. code:: bash

   git clone https://github.com/christoph2/pyxcp.git
   cd pyxcp
   python build_ext.py

   # Verify extensions built
   ls -la pyxcp/transport/transport_ext*.so  # Linux/macOS
   dir pyxcp\transport\transport_ext*.pyd    # Windows

**Related Issues:** #240, #188, #199, #169

----

Symptom: "error: Microsoft Visual C++ 14.0 or greater is required"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** No C++ compiler on Windows.

**Solution:**

1. **Use pre-built wheel** (no compiler needed):

   .. code:: powershell

      pip install --upgrade pip
      pip install pyxcp

2. **Or install Visual Studio Build Tools:**

   - Download: https://visualstudio.microsoft.com/downloads/
   - Select: "Build Tools for Visual Studio 2022"
   - Workload: "Desktop development with C++"
   - Then: ``pip install pyxcp``

**Related Issues:** #253, #262

----

Symptom: "UnboundLocalError: cannot access local variable 'libdir'" (Linux)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Python development libraries not found.

**Solution:**

.. code:: bash

   # Install Python dev package
   sudo apt install python3-dev libpython3-dev

   # Verify Python library exists
   find /usr -name "libpython*.so"
   find /usr -name "libpython*.a"

   # If missing, install specific version
   sudo apt install python3.12-dev  # Replace with your Python version

   # Then rebuild
   pip install --no-binary pyxcp pyxcp

**Note:** pyXCP v0.26.3+ handles this gracefully by falling back to CMake auto-detection.

**Related Issues:** #169

----

Configuration Problems
----------------------

Symptom: "FileNotFoundError: Configuration file 'pyxcp_conf.py' does not exist"
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Config file not found when expected.

**Solutions (pick one):**

1. **Use environment variable** (v0.26.5+):

   .. code:: bash

      export PYXCP_CONFIG=/absolute/path/to/pyxcp_conf.py
      python my_script.py

2. **Pass logger explicitly** (v0.26.4+):

   .. code:: python

      import logging
      from pyxcp.daq_stim import DaqToCsv

      logger = logging.getLogger('my_daq')
      logger.setLevel(logging.INFO)
      daq_policy = DaqToCsv(daq_lists, logger=logger)

3. **Create config file in one of search locations:**

   - Current working directory: ``./pyxcp_conf.py``
   - Script directory: ``<script_dir>/pyxcp_conf.py``
   - User home: ``~/.pyxcp/pyxcp_conf.py``

4. **Use programmatic config** (v0.26.5+):

   .. code:: python

      from pyxcp.config import create_application_from_config

      config = {"Transport": {"CAN": {"device": "socketcan", "channel": "can0"}}}
      app = create_application_from_config(config)

**Config File Search Order:**

1. ``PYXCP_CONFIG`` environment variable
2. ``--config`` command-line argument
3. ``./pyxcp_conf.py`` (current directory)
4. ``<script_dir>/pyxcp_conf.py``
5. ``~/.pyxcp/pyxcp_conf.py``

**Related Issues:** #260, #211

----

Symptom: PyInstaller/py2exe bundles fail with import errors
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** PyInstaller doesn't auto-detect native extensions.

**Solution:**

Create ``hook-pyxcp.py`` next to your script:

.. code:: python

   from PyInstaller.utils.hooks import collect_dynamic_libs

   binaries = collect_dynamic_libs('pyxcp')
   hiddenimports = [
       'pyxcp.transport.transport_ext',
       'pyxcp.cpp_ext.cpp_ext',
       'pyxcp.daq_stim.stim',
       'pyxcp.recorder.rekorder',
   ]

Build with:

.. code:: bash

   pyinstaller --additional-hooks-dir=. your_script.py

**Related Issues:** #261, #203

----

DAQ Issues
----------

Symptom: DAQ recording produces no data or empty CSV
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Diagnostic Steps:**

1. **Check ECU DAQ support:**

   .. code:: bash

      xcp-info -t eth --config my_config.py
      # Look for "DAQ Info" section

2. **Verify DAQ processor info:**

   .. code:: python

      with ap.run() as x:
          x.connect()
          if x.slaveProperties.supportsDaq:
              daq_info = x.getDaqInfo()
              print(f"Max DAQ: {daq_info['processor']['maxDaq']}")
              print(f"Max ODT: {daq_info['processor']['maxOdt']}")
          else:
              print("ERROR: ECU does not support DAQ!")

3. **Check DAQ list configuration:**

   .. code:: python

      # Verify measurements have correct addresses
      daq_lists = [
          DaqList(
              name="test",
              event_num=0,  # Event 0 usually exists
              measurements=[
                  ("var1", 0x12345678, 0, "F32"),  # Check address!
              ]
          )
      ]

4. **Enable debug logging:**

   .. code:: python

      import logging
      logging.basicConfig(level=logging.DEBUG)
      # Look for "DAQ" messages

**Common Problems:**

- **Wrong addresses:** Use A2L file or ``xcp-info`` to verify
- **Wrong event:** Event channel doesn't exist or isn't triggered
- **Protection:** DAQ resource locked (see seed/key)
- **Max DAQ exceeded:** Too many DAQ lists configured

**Related Issues:** #223, #226, #260

----

Symptom: "GET_DAQ_PROCESSOR_INFO failed" or hangs
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Some ECUs don't implement this optional command or respond slowly.

**Solution:**

1. **Skip with --no-daq flag:**

   .. code:: bash

      xcp-info -t eth --config my_config.py --no-daq

2. **In code, use try_command:**

   .. code:: python

      from pyxcp.types import TryCommandResult

      status, daq_info = x.try_command(x.getDaqProcessorInfo)
      if status == TryCommandResult.OK:
          # Use daq_info
      else:
          # Fall back: manually configure DAQ

3. **Increase timeout:**

   .. code:: python

      transport.timeout = 10.0  # Some ECUs are slow

**Note:** pyXCP v0.26.3+ handles missing GET_DAQ_PROCESSOR_INFO gracefully.

**Related Issues:** #247, #263

----

Symptom: DAQ timestamps are wrong or overflow
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** Timestamp size mismatch or overflow not handled.

**Solution:**

1. **Check timestamp size in DAQ configuration:**

   .. code:: python

      # If ECU uses 16-bit timestamps:
      daq_list = DaqList(
          name="test",
          enable_timestamps=True,
          timestamp_size=2,  # 1, 2, or 4 bytes
          ...
      )

2. **Enable timestamp overflow handling** (default in pyXCP):

   - pyXCP automatically linearizes timestamps
   - Both ``timestamp0`` (host) and ``timestamp1`` (ECU) are normalized to nanoseconds

3. **Use PTP hardware timestamps** (Linux Ethernet):

   .. code:: python

      # In config file
      c.Transport.Eth.ptp_timestamping = True

**Related Issues:** #219

----

CAN Problems
------------

Symptom: "No backend available" or CAN driver not found
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Diagnostic:**

.. code:: bash

   # Check available CAN drivers
   pyxcp-probe-can-drivers

**Solutions by Platform:**

**Linux (SocketCAN):**

.. code:: bash

   # Install can-utils
   sudo apt install can-utils

   # Bring up CAN interface
   sudo ip link set can0 up type can bitrate 500000

   # Verify
   ip -details link show can0

**Windows (Vector):**

.. code:: powershell

   # Install python-can Vector backend
   pip install python-can[vector]

   # Verify Vector DLL exists
   where vxlapi64.dll
   # Should be in C:\Windows\System32 or Vector folder

**Windows (PCAN):**

.. code:: powershell

   # Install PCAN driver from PEAK website
   # Install python-can PCAN backend
   pip install python-can[pcan]

   # Test with PCAN-View first

**macOS:**

- Limited CAN support
- Install vendor driver (PEAK, Kvaser)
- Or use virtual CAN: ``can_interface="virtual"``

**Related Issues:** #188, #227

----

Symptom: CAN bus errors (BUSOFF, ERROR_PASSIVE)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Causes:**

1. **Wrong bitrate:** CAN interface bitrate doesn't match bus
2. **Missing termination:** 120Ω termination resistors not connected
3. **Hardware issue:** Bad cable, loose connector, defective adapter

**Solution:**

1. **Verify bitrate matches:**

   .. code:: bash

      # Linux: Check current bitrate
      ip -details link show can0
      # Should match ECU bitrate (typically 500000 or 1000000)

      # Change if wrong
      sudo ip link set can0 down
      sudo ip link set can0 type can bitrate 500000
      sudo ip link set can0 up

2. **Check termination:**

   - CAN bus needs 120Ω resistor at each end
   - Measure resistance: should be ~60Ω between CAN_H and CAN_L

3. **Test with cansend/candump:**

   .. code:: bash

      # Terminal 1
      candump can0

      # Terminal 2
      cansend can0 123#DEADBEEF

      # If this fails, hardware/bus issue, not pyXCP

**Related Issues:** #227

----

Symptom: Wrong CAN ID - ECU not responding
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Cause:** ``can_id_master`` doesn't match ECU's expected ID.

**Solution:**

1. **Scan for XCP slaves:**

   .. code:: bash

      xcp-id-scanner -t can --config can_config.py
      # Reports all responding IDs

2. **Check A2L file** (if available):

   - Look for XCP_ON_CAN section
   - ``CAN_ID_MASTER`` = ID ECU expects from tool
   - ``CAN_ID_SLAVE`` = ID ECU uses for responses

3. **Try common IDs:**

   .. code:: python

      # Common XCP CAN IDs
      can_id_master = 0x700  # or 0x640, 0x300, 0x123
      can_id_slave = 0x701   # usually master + 1

4. **Enable CAN tracing:**

   .. code:: bash

      # Linux: Capture CAN traffic while running pyXCP
      candump can0 -L
      # Look for XCP response frames (RES/ERR)

**Related Issues:** #188, #227

----

Performance Issues
------------------

Symptom: DAQ recording is slow or drops samples
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Causes:**

1. **High CPU load:** Python overhead at high frequencies
2. **Disk I/O:** Writing to slow storage
3. **Network latency:** Ethernet buffer too small

**Solutions:**

1. **Use XMRAW format** (faster than CSV):

   .. code:: python

      from pyxcp.daq_stim import DaqRecorder
      recorder = DaqRecorder(daq_lists, "measurement", 8)
      # Convert to CSV later: xmraw-converter measurement.xmraw -o csv

2. **Increase OS priority** (Linux):

   .. code:: bash

      # Real-time scheduling
      sudo chrt -f 50 python3 daq_script.py

      # Or nice priority
      sudo nice -n -10 python3 daq_script.py

3. **Tune network buffers** (Linux Ethernet):

   .. code:: bash

      sudo sysctl -w net.core.rmem_max=26214400
      sudo sysctl -w net.core.wmem_max=26214400

4. **Use C++ extensions** (verify installed):

   .. code:: python

      # Should work without error:
      from pyxcp.transport import transport_ext
      from pyxcp.daq_stim import stim

5. **Reduce DAQ rate:**

   - Lower event frequency
   - Record fewer variables
   - Use decimation (record every Nth sample)

**Related Issues:** #219

----

Symptom: Slow connection establishment
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

**Causes:**

1. **Seed/key unlock slow:** DLL taking time
2. **Optional commands timing out:** ECU doesn't support them

**Solutions:**

1. **Skip optional commands:**

   .. code:: bash

      xcp-info --no-daq --no-pag --no-pgm --no-ids

2. **Reduce timeout for optional commands:**

   .. code:: python

      from pyxcp.types import TryCommandResult

      # Use try_command for optional features
      status, result = x.try_command(x.getDaqProcessorInfo)
      if status != TryCommandResult.OK:
          # Skip DAQ info

3. **Pre-unlock before measurement:**

   .. code:: python

      # Unlock once at start
      x.connect()
      x.cond_unlock()  # Uses seed/key DLL
      # ... then do multiple measurements without reconnecting

**Related Issues:** #247

----

Error Messages Reference
-------------------------

Common XCP Error Codes
~~~~~~~~~~~~~~~~~~~~~~

When you see ``XcpError: <code> - <message>``, refer to this table:

.. list-table::
   :header-rows: 1
   :widths: 15 30 55

   * - Code
     - Message
     - Meaning / Solution

   * - 0x00
     - CMD_SYNCH
     - Command mismatch. Disconnect and reconnect.

   * - 0x10
     - CMD_BUSY
     - ECU busy. Retry after delay or increase timeout.

   * - 0x20
     - DAQ_ACTIVE
     - DAQ already running. Stop DAQ first.

   * - 0x21
     - PGM_ACTIVE
     - Programming active. Wait for completion.

   * - 0x22
     - CMD_UNKNOWN
     - Command not supported. Check ECU capabilities.

   * - 0x23
     - CMD_SYNTAX
     - Wrong parameters. Check XCP spec.

   * - 0x30
     - OUT_OF_RANGE
     - Address/size invalid. Check A2L file.

   * - 0x31
     - WRITE_PROTECTED
     - Resource locked. Use seed/key unlock.

   * - 0x32
     - ACCESS_DENIED
     - Seed/key required. Configure SEED_KEY_DLL.

   * - 0x33
     - ACCESS_LOCKED
     - Session locked. Disconnect other tools.

   * - 0x34
     - PAGE_NOT_VALID
     - Calibration page not active. Check paging.

   * - 0x40
     - MODE_NOT_VALID
     - DAQ mode invalid. Check DAQ configuration.

   * - 0x41
     - SEGMENT_NOT_VALID
     - Memory segment doesn't exist.

   * - 0x42
     - SEQUENCE_ERROR
     - Command sequence wrong. E.g., ALLOC_DAQ before FREE_DAQ.

   * - 0x43
     - DAQ_CONFIG
     - DAQ config error. Check event channels, ODT count.

**Related:** XCP specification ASAM MCD-1 XCP

----

Common Python Exceptions
~~~~~~~~~~~~~~~~~~~~~~~~

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Exception
     - Common Causes & Solutions

   * - ``TimeoutError``
     - Connection timeout. See `Connection Issues`_.

   * - ``XcpTimeoutError``
     - ECU not responding. Check timeout, network, ECU status.

   * - ``FileNotFoundError``
     - Config file missing. See `Configuration Problems`_.

   * - ``ModuleNotFoundError``
     - Build issue. See `Import/Build Errors`_.

   * - ``PermissionError``
     - USB/CAN access denied. See `USB Permissions`_ or run as sudo (not recommended).

   * - ``OSError: [Errno 48] Address already in use``
     - Port conflict (Ethernet). Kill other process or change port.

   * - ``OSError: [Errno 19] No such device``
     - CAN interface down. Run: ``sudo ip link set can0 up type can bitrate 500000``

   * - ``ValueError: could not convert...``
     - Wrong data type in config. Check config syntax.

----

Platform-Specific Issues
~~~~~~~~~~~~~~~~~~~~~~~~

**Linux:**

- **Permissions:** Add user to ``dialout`` and ``can`` groups
- **SocketCAN:** Interface must be UP before use
- **USB:** Create udev rules for non-root access

  See: :doc:`platform_setup` → Linux Setup → USB Permissions

**Windows:**

- **MSVC required:** For building from source (or use pre-built wheels)
- **DLL bridging:** 32-bit seed/key DLLs need ``asamkeydll.exe``
- **Firewall:** Add Python to exceptions for Ethernet XCP

  See: :doc:`platform_setup` → Windows Setup

**macOS:**

- **Xcode tools:** Required for building
- **Limited CAN:** Few native drivers; consider Linux VM

  See: :doc:`platform_setup` → macOS Setup

----

USB Permissions
~~~~~~~~~~~~~~~

**Linux only** - Required for USB XCP or USB-CAN adapters.

**Symptom:** ``PermissionError: [Errno 13] Permission denied``

**Solution:** Create udev rule.

1. **Find device IDs:**

   .. code:: bash

      lsusb
      # Look for your device, note idVendor:idProduct

2. **Create udev rule:** ``/etc/udev/rules.d/99-pyxcp-usb.rules``

   .. code::

      # Replace XXXX and YYYY with your vendor/product IDs
      SUBSYSTEM=="usb", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", MODE="0666"

3. **Reload rules:**

   .. code:: bash

      sudo udevadm control --reload-rules
      sudo udevadm trigger

4. **Alternative:** Add user to dialout group

   .. code:: bash

      sudo usermod -a -G dialout $USER
      # Log out and back in

----

Getting Help
------------

If your issue isn't covered here:

1. **Search existing resources:**

   - :doc:`FAQ <FAQ>` - Specific Q&A
   - :doc:`quickstart` - Getting started guide
   - :doc:`cli_tools` - CLI tool documentation
   - :doc:`platform_setup` - Platform-specific setup
   - `GitHub Issues <https://github.com/christoph2/pyxcp/issues>`_ - Known issues

2. **Enable debug logging:**

   .. code:: bash

      # Environment variable
      export PYXCP_LOGLEVEL=DEBUG
      python your_script.py

      # Or programmatically
      import logging
      logging.basicConfig(level=logging.DEBUG)

3. **Report an issue:**

   Include:

   - pyXCP version: ``python -c "import pyxcp; print(pyxcp.__version__)"``
   - Python version: ``python --version``
   - Operating system: ``uname -a`` (Linux/macOS) or ``ver`` (Windows)
   - Transport: CAN/Ethernet/USB/Serial
   - Minimal reproducible code
   - Full error traceback
   - Debug log output

4. **Ask in discussions:**

   - `GitHub Discussions <https://github.com/christoph2/pyxcp/discussions>`_
   - Provide context and what you've tried

----

Quick Diagnostic Checklist
---------------------------

Run these commands to quickly diagnose your setup:

.. code:: bash

   # 1. Verify pyXCP installed
   python -c "import pyxcp; print(f'pyXCP {pyxcp.__version__} OK')"

   # 2. Check C++ extensions
   python -c "from pyxcp.transport import transport_ext; print('Extensions OK')"

   # 3. Check CAN drivers
   pyxcp-probe-can-drivers

   # 4. Test network (Ethernet XCP)
   ping <ECU_IP>

   # 5. Test CAN interface (Linux)
   ip link show can0
   candump can0 &
   cansend can0 123#DEADBEEF

   # 6. Check config discovery
   python -c "import os; print('PYXCP_CONFIG:', os.getenv('PYXCP_CONFIG', 'Not set'))"

   # 7. Test simple connection
   xcp-info -t eth --host <ECU_IP> --port 5555 --no-daq --no-pag

If all 7 succeed, your setup is correct. Issues are likely ECU-side or configuration.

----

**Last updated:** 2026-02-14
**pyXCP version:** 0.26.5+

pyXCP Tutorial
==============

This tutorial will guide you through the basics of using the pyXCP
library to communicate with XCP-enabled devices.

Introduction
------------

pyXCP is a Python library for communicating with devices that support
the XCP (Universal Measurement and Calibration Protocol) protocol. XCP
is commonly used in automotive applications for calibration,
measurement, and flashing of ECUs (Electronic Control Units).

Installation
------------

Install pyXCP from PyPI:

.. code:: shell

   pip install pyxcp

For building from source and development details, see the project
README.

Basic Usage
-----------

Before you start
~~~~~~~~~~~~~~~~

- Prerequisites: An XCP slave (ECU, device, or simulator), and ideally
  its A2L file (ASAM MCD‑2 MC). The A2L maps symbolic names to
  addresses, data types, and conversions used for
  calibration/measurement. Without an A2L you can still work with raw
  addresses.
- Safety: XCP is for development and testing. Avoid enabling
  measurement/calibration on safety‑critical systems unless your safety
  case covers it. Prefer a lab setup for first steps.
- Transport choice: pyXCP supports Ethernet, CAN, USB, and Serial (SxI).
  Ethernet usually offers the highest throughput; CAN is ubiquitous and
  robust but has limited payload. See also docs/howto_can_driver.md for
  CAN setup.

Choose your transport (quick guide)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- Ethernet (TCP): If your device exposes XCP on TCP, you’ll typically
  specify host/port.
- CAN: Requires a python‑can compatible driver and correct CAN
  IDs/filters. Use pyxcp‑probe‑can‑drivers to list available interfaces.
  See docs/howto_can_driver.md.
- USB/Serial: Device‑specific; consult your device documentation.

You can configure transports either by command line via the built‑in
ArgumentParser or via the traitlets configuration system (see
Configuration below).

CLI quick wins
~~~~~~~~~~~~~~

Try these before writing code:

.. code:: bash

   # Discover basic capabilities and negotiated options
   xcp-info -t eth --host 127.0.0.1 --port 5555

   # Scan for identifier packets (e.g., on CAN)
   xcp-id-scanner -t can --driver kvaser --channel 0 --bitrate 500000

   # Attempt to fetch A2L from the target if supported
   xcp-fetch-a2l -t eth --host 127.0.0.1 --port 5555 -o my_ecu.a2l

   # See available demos
   xcp-examples -h

Connecting to an XCP Slave
~~~~~~~~~~~~~~~~~~~~~~~~~~

The most basic operation is to connect to an XCP slave device and
retrieve information about it:

.. code:: python

   from pyxcp.cmdline import ArgumentParser

   # Create an argument parser that handles common XCP connection parameters
   ap = ArgumentParser(description="pyXCP hello world example")

   # Use a context manager to ensure proper cleanup
   with ap.run() as x:
       # Connect to the XCP slave
       x.connect()

       # Get the slave identifier
       identifier = x.identifier(0x01)
       print(f"ID: {identifier!r}")

       # Print slave properties
       print(x.slaveProperties)

       # Disconnect when done
       x.disconnect()

The ``ArgumentParser`` class handles command-line arguments for
specifying the transport layer (CAN, Ethernet, USB, etc.) and connection
parameters. It can also wrap an existing ``argparse.ArgumentParser`` to
support custom application-specific arguments:

.. code:: python

   import argparse
   from pyxcp.cmdline import ArgumentParser

   # 1. Create a standard argparse parser for your custom options
   parser = argparse.ArgumentParser(description="My custom tool")
   parser.add_argument("--my-option", action="store_true", help="Custom flag")

   # 2. Wrap it with pyXCP's ArgumentParser
   ap = ArgumentParser(parser)

   # 3. Access both pyXCP and custom arguments
   with ap.run() as x:
       if ap.args.my_option:
           print("Custom option enabled!")
       # ... use the master instance x ...


Examples: Ethernet and CAN invocations
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

- Ethernet (TCP):

.. code:: bash

   python your_script.py -t eth --host 127.0.0.1 --port 5555 --protocol TCP

- CAN (Kvaser example):

.. code:: bash

   python your_script.py -t can --driver kvaser --channel 0 --bitrate 500000 \
     --can-id-master 0x300 --can-id-slave 0x301

Tip: If you prefer config files, you can omit many CLI flags and specify
them in a traitlets config (see Configuration below). Use
``xcp-profile create -o my_config.py`` to generate a template.

Configuration
~~~~~~~~~~~~~

pyXCP supports two configuration systems:

Traitlets-based Configuration (Recommended)
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The recommended way to configure pyXCP is using the traitlets-based
configuration system with Python configuration files:

.. code:: bash

   # Connect using a Python configuration file
   python your_script.py -t eth --config path/to/config.py

Example Python configuration file (config.py):

.. code:: python

   # Configuration file for pyXCP
   c = get_config()  # noqa

   # Transport configuration
   c.Transport.layer = "ETH"

   # Ethernet configuration
   c.Transport.Eth.host = "localhost"
   c.Transport.Eth.port = 5555
   c.Transport.Eth.protocol = "TCP"

You can generate a template configuration file with all available
options:

.. code:: bash

   xcp-profile create -o my_config.py

Legacy TOML Configuration
^^^^^^^^^^^^^^^^^^^^^^^^^

The older TOML-based configuration is still supported but is now
considered legacy:

.. code:: bash

   # Connect using legacy TOML configuration
   python your_script.py -t eth --config path/to/config.toml

Example legacy configuration file for Ethernet (conf_eth.toml):

.. code:: toml

   [XCP]
   TRANSPORT = "ETH"

   [ETH]
   HOST = "localhost"
   PORT = 5555
   PROTOCOL = "TCP"

Example legacy configuration file for CAN (conf_can.toml):

.. code:: toml

   [XCP]
   TRANSPORT = "CAN"

   [CAN]
   CHANNEL = 0
   BITRATE = 500000

You can convert a legacy configuration file to the new format:

.. code:: bash

   xcp-profile convert -c old_config.toml -o new_config.py

Data Acquisition (DAQ)
----------------------

XCP supports data acquisition for collecting measurement data from the
slave device.

Concepts recap: The slave exposes events (e.g., “1 ms task”) that drive
sampling. You configure one or more DAQ lists and ODTs, assign them to
events, and optionally enable timestamps for precise correlation. DTO
size and bandwidth depend on the negotiated transport parameters.

Note: For a higher-level DAQ workflow using Policies (online CSV and
offline .xmraw recording) and post-processing, see the Recorder page:
`Recorder <recorder.md>`__. The snippet below demonstrates a low-level
DAQ setup directly with the master API:

.. code:: python

   from pyxcp.cmdline import ArgumentParser
   from pyxcp.recorder import XcpLogFileWriter

   ap = ArgumentParser(description="pyXCP DAQ example")

   with ap.run() as x:
       x.connect()

       # Configure DAQ
       x.cond_unlock()

       # Get DAQ information
       daq_info = x.getDaqInfo()

       # Set up a DAQ list
       x.setDaqPtr(0, 0, 0)
       x.writeDaq(0x1234)  # Address to measure

       # Start DAQ
       x.startStopDaqList(0, 1)
       x.startStopSynch(1)

       # Create a recorder to save data
       recorder = XcpLogFileWriter("measurement.xmraw")
       x.set_recorder(recorder)

       # Wait for data
       import time
       time.sleep(5)

       # Stop DAQ
       x.startStopSynch(0)
       recorder.close()

       x.disconnect()

Calibration
-----------

XCP allows you to read and write parameters in the slave device:

.. code:: python

   from pyxcp.cmdline import ArgumentParser

   ap = ArgumentParser(description="pyXCP calibration example")

   with ap.run() as x:
       x.connect()

       # Unlock the slave for calibration
       x.cond_unlock()

       # Read a value
       address = 0x1234
       size = 4  # bytes
       data = x.upload(size, address)
       print(f"Value at 0x{address:X}: {int.from_bytes(data, byteorder='little')}")

       # Write a value
       new_value = 42
       x.download(address, new_value.to_bytes(size, byteorder='little'))

       x.disconnect()

Advanced Features
-----------------

Using Custom Transport Layers
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

pyXCP supports various transport layers, and you can also create custom
ones:

.. code:: python

   from pyxcp.cmdline import ArgumentParser
   from pyxcp.transport.can import CanInterfaceBase

   # Create a custom CAN interface
   class MyCanInterface(CanInterfaceBase):
       def __init__(self, config):
           super().__init__(config)
           # Initialize your custom CAN hardware

       def transmit(self, payload):
           # Implement sending data
           pass

       def receive(self, timeout=None):
           # Implement receiving data
           pass

       def close(self):
           # Clean up resources
           pass

   # Register your custom interface
   from pyxcp.transport.can import register_can_interface
   register_can_interface("my_can", MyCanInterface)

   # Now you can use it in your configuration
   # [CAN]
   # DRIVER = "my_can"

Upgrading an Existing Configuration
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

You can convert a legacy configuration file (TOML/JSON) to the new
Python/traitlets format using the xcp-profile tool:

.. code:: shell

   xcp-profile convert -c old_config.toml -o new_config.py

Note on CAN identifier parameters (issue #130): The new configuration
system interprets CAN IDs via

.. code:: python

   c.Transport.Can.can_id_master = 47
   c.Transport.Can.can_id_slave = 11

correctly. For compatibility, existing legacy files continue to behave
as before; when you convert a legacy file, ID roles are normalized in
the generated Python config. The logger illustrates the resolved IDs at
runtime, for example:

.. code:: text

   2024-08-06 16:25:54 INFO     XCPonCAN - Interface-Type: 'kvaser' Parameters: [('channel', '0'), ('fd', False), ('bitrate', 500000),
                                ('receive_own_messages', False), ('sjw', 2), ('tseg1', 5), ('tseg2', 2)]
                       INFO     XCPonCAN - Master-ID (Tx): 0x00000300S -- Slave-ID (Rx): 0x00000301S
   2024-08-06 16:25:55 INFO     XCPonCAN - Filters used: [{'can_id': 769, 'can_mask': 2047, 'extended': False}]
                       INFO     XCPonCAN - State: BusState.ACTIVE

Unlocking via Seed & Key (Python)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Instead of a DLL, you can provide a Python function for Seed & Key
handling:

.. code:: python

   def SeedKeyXCP(resource: int, seed: bytes) -> bytes:
       temp0, temp1, temp2, temp3 = seed[0], seed[1], seed[2], seed[3]
       temp = (temp3 << 24) | (temp2 << 16) | (temp1 << 8) | temp0
       temp = (temp >> 5) | (temp << 23)
       temp = (temp * 7) ^ 0x26031961

       key = bytearray(9)
       key[0] = (temp >> 0) & 0xFF
       key[1] = (temp >> 8) & 0xFF
       key[2] = (temp >> 16) & 0xFF
       key[3] = (temp >> 24) & 0xFF
       return bytes(key)

   # c.General.seed_n_key_dll = 'SeedNKeyXcp.dll'  # alternative
   c.General.seed_n_key_function = SeedKeyXCP

Re‑using an existing CAN interface
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you already manage a CAN bus object externally, you can pass it into
pyXCP. See HOW‑TO: How to build your own CAN drivers
(howto_can_driver.md) for a full example and caveats.

Timestamping note
~~~~~~~~~~~~~~~~~

Timestamps are generated by a C++ extension. The application start
timestamp (including timezone and offsets) is available on the context:

.. code:: python

   with ap.run() as x:
       print("Start DT:", x.start_datetime)

Flashing / Programming (overview)
---------------------------------

Flashing support depends on the slave’s programming algorithm and the
A2L description. pyXCP provides the building blocks (CONNECT,
PROGRAM_RESET, ERASE, DOWNLOAD, VERIFY, checksums), but the exact
sequence and memory layout are slave‑specific.

- Always back up calibration data where applicable.
- Verify negotiated options (e.g., checksum type, max DTO) with
  ``xcp-info`` before large transfers.
- Consult your A2L for programming sections and address granularity.
- For safety, test on a simulator or development device first.

Troubleshooting
---------------

- Timeouts on connect: Check transport parameters (host/port for ETH;
  channel/bitrate and filters for CAN). Use ``xcp-info`` or
  ``xcp-id-scanner`` to validate connectivity.
- Seed & Key fails: Confirm you provided the correct DLL or Python
  function. On Windows with 32‑bit only DLLs, use the provided 32↔64
  bridge (asamkeydll.exe). See README and docs/configuration.md.
- Wrong or swapped CAN IDs: Ensure ``can_id_master`` and
  ``can_id_slave`` are set correctly (see Configuration). The logger
  prints resolved IDs.
- DTO too large: Reduce number/size of signals in DAQ lists or increase
  event period; confirm max DTO via ``xcp-info``.
- A2L mismatch: Ensure the A2L matches the firmware build; symbolic
  access depends on correct addresses and conversions.

Next Steps
----------

- Explore the examples directory for more advanced usage patterns
- Check the API documentation for detailed information about available
  functions
- Join the community to get help and contribute to the project

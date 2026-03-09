pyXCP Quickstart Guide
======================

Get started with pyXCP in 15 minutes: installation, first connection, parameter read/write, and basic DAQ recording.

Prerequisites
-------------
- Python 3.8+ (64-bit recommended)
- XCP slave device (ECU, simulator, or test tool)
- Transport interface: CAN adapter, Ethernet, USB, or serial
- Optional: A2L file (ASAM MCD-2 MC) for symbolic access

Safety: XCP is for development/testing—avoid safety-critical systems without proper analysis.

Installation
------------

Basic installation::

   pip install pyxcp
   python -c "import pyxcp; print(pyxcp.__version__)"

Optional dependencies::

   # A2L support
   pip install pyxcp pya2ldb

   # CAN drivers
   pip install pyxcp python-can[pcan]
   pip install pyxcp python-can[vector]
   pip install pyxcp python-can[ixxat]

Your First XCP Connection
-------------------------

Minimal CAN example::

   from pyxcp import Master

   with Master("can") as xcp:
       xcp.connect()
       ecu_id = xcp.getId(0x01)
       print(f"Connected to ECU: {ecu_id}")
       xcp.disconnect()

Run with CLI args::

   python your_script.py --transport CAN --device socketcan --channel can0 --bitrate 500000

Ethernet example (TCP)::

   from pyxcp import Master

   with Master("eth") as xcp:
       xcp.connect()
       props = xcp.slaveProperties
       print(f"Protocol Layer: {props.protocolLayerVersion}")
       print(f"Max CTO/DTO: {props.maxCto}/{props.maxDto}")
       xcp.disconnect()

No config file required (programmatic)::

   from pyxcp import Master
   from pyxcp.config import create_application_from_config, set_application

   config = {"Transport": {"CAN": {"device": "socketcan", "channel": "can0", "bitrate": 500000, "max_dlc": 8}}}
   app = create_application_from_config(config)
   set_application(app)

   with Master("can") as xcp:
       xcp.connect()
       print(f"ECU ID: {xcp.getId(0x01)}")
       xcp.disconnect()

Reading and Writing Parameters
------------------------------

Upload (read)::

   from pyxcp import Master
   import struct

   with Master("can") as xcp:
       xcp.connect()
       data = xcp.upload(address=0x1A2000, length=4)
       value = struct.unpack("<I", data)[0]
       print(f"Value: {value}")
       xcp.disconnect()

Download (write)::

   from pyxcp import Master
   import struct

   with Master("can") as xcp:
       xcp.connect()
       new_value = 42
       xcp.download(address=0x1A2000, data=struct.pack("<I", new_value))
       readback = struct.unpack("<I", xcp.upload(address=0x1A2000, length=4))[0]
       print(f"Written: {new_value}, Read back: {readback}")
       xcp.disconnect()

Basic DAQ Recording
-------------------

Heads-up (Issue #253): Some slaves lack optional DAQ services. ``getDaqInfo()`` returns ``valid`` flags (``processor``, ``resolution``, ``events``). If processor/resolution are ``False``, supply trusted DAQ info via ``DaqProcessor.setup(daq_info_override=...)`` or abort.

Simple DAQ example::

   from pyxcp import Master
   from pyxcp.daq_stim import DaqList, DaqToCsv
   import time

   with Master("can") as xcp:
       xcp.connect()
       daq_info = xcp.getDaqInfo()
       if not daq_info["valid"]["processor"] or not daq_info["valid"]["resolution"]:
           raise RuntimeError("Slave did not provide DAQ capabilities; supply overrides before proceeding.")

       daq_list = DaqList(
           name="Engine",
           event=0,
           measurements=[
               {"address": 0x1A2000, "ext": 0, "size": 4},
               {"address": 0x1A2004, "ext": 0, "size": 4},
               {"address": 0x1A2008, "ext": 0, "size": 2},
           ],
       )

       policy = DaqToCsv([daq_list])
       xcp.setupDaq([daq_list], policy)
       xcp.startDaq()
       time.sleep(10)
       xcp.stopDaq()
       xcp.disconnect()

DAQ with data conversion::

   import struct
   from pyxcp.daq_stim import DaqList

   def convert_engine_speed(raw_bytes):
       return struct.unpack("<I", raw_bytes)[0] * 0.25

   def convert_temperature(raw_bytes):
       return (struct.unpack("<I", raw_bytes)[0] * 0.1) - 40.0

   measurements = [
       {"address": 0x1A2000, "ext": 0, "size": 4, "name": "EngineSpeed_RPM", "conversion": convert_engine_speed},
       {"address": 0x1A2004, "ext": 0, "size": 4, "name": "EngineTemp_C", "conversion": convert_temperature},
   ]

Configuration Options
---------------------

Method 1: Command-line (recommended)::

   from pyxcp.cmdline import ArgumentParser

   ap = ArgumentParser(description="My XCP Tool")
   with ap.run() as xcp:
       xcp.connect()
       # ...
       xcp.disconnect()

Run with::

   python tool.py --transport CAN --device socketcan --channel can0 --bitrate 500000

Method 2: Config file (``pyxcp_conf.py``):: 

   c = get_config()
   c.Transport.CAN.device = "socketcan"
   c.Transport.CAN.channel = "can0"
   c.Transport.CAN.bitrate = 500000

Config search order: ``PYXCP_CONFIG`` env var → CWD → script dir → ``~/.pyxcp/pyxcp_conf.py``.

Method 3: Programmatic (embedding)::

   from pyxcp.config import create_application_from_config, set_application
   config = {"Transport": {"CAN": {"device": "socketcan", "channel": "can0", "bitrate": 500000}}}
   app = create_application_from_config(config)
   set_application(app)

Next Steps
----------

- :doc:`tutorial` – comprehensive guide with advanced topics
- :doc:`FAQ` – common questions and solutions
- Examples: ``pyxcp/examples`` directory
- API Reference: ``pyxcp.rst``

Example usage::

   python xcphello.py --transport CAN --device socketcan --channel can0
   python run_daq.py --transport CAN --device socketcan --channel can0

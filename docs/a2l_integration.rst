XCP + A2L Integration Guide
===========================

Overview
--------

This guide demonstrates how to use **ASAM MCD-2 MC (A2L)** files with **pyXCP** for symbolic access to ECU parameters. A2L files describe the memory layout, data types, and conversion formulas of ECU variables, enabling human-readable measurement and calibration workflows.

**What you'll learn:**

1. Load A2L files with ``pya2ldb``
2. Read measurements by symbolic name
3. Write calibration parameters by name
4. Set up DAQ with A2L metadata
5. Convert raw values to engineering units
6. Export data with symbolic labels

For **production-grade workflows** with advanced features, see the `asamint project`_.

.. _asamint project: https://github.com/christoph2/asamint


Tools Overview
--------------

pyXCP Ecosystem
~~~~~~~~~~~~~~~

============  ========================================================  ====================
Tool          Purpose                                                   Use When
============  ========================================================  ====================
**pyxcp**     XCP protocol implementation (CAN/Ethernet/USB/Serial)    Core communication
**pya2ldb**   A2L file parser and database                             Symbolic access
**asamint**   High-level MCS (Measurement & Calibration System)        Production workflows
**asammdf**   MDF file handling (ASAM MCD-3 MC)                        Data export
**objutils**  Binary file formats (Intel Hex, S-records, ELF)          Flashing
============  ========================================================  ====================

When to Use What?
~~~~~~~~~~~~~~~~~

**Use pyxcp directly when:**

- Building custom calibration tools
- Integrating XCP into test automation
- Low-level protocol debugging
- Learning XCP fundamentals
- Embedded in larger applications

**Use asamint when:**

- Need command-line MCS functionality
- Orchestrating multiple ASAM standards (A2L + MDF + XCP)
- Creating calibration data files (ASAM CDF)
- High-level batch operations
- Production measurement campaigns

**Example decision tree:**

.. code-block:: text

   Need XCP communication?
   └── YES
       ├── Simple script / learning? → Use pyxcp examples
       ├── Custom tool / integration? → Use pyxcp API directly
       └── Production MCS? → Use asamint (built on pyxcp)


Prerequisites
-------------

Install required packages:

.. code-block:: bash

   pip install pyxcp pya2ldb

**Optional (for asamint):**

.. code-block:: bash

   git clone https://github.com/christoph2/asamint
   cd asamint
   python setup.py develop


Quick Start: Read Parameter by Name
------------------------------------

**Scenario:** Read ECU software version string using A2L symbolic name.

.. code-block:: python

   from pyxcp.cmdline import ArgumentParser
   from pya2ldb import DB

   # Load A2L file
   db = DB()
   db.import_a2l("my_ecu.a2l")

   # Get measurement metadata
   version_var = db.query_measurement("SwVersion")
   address = version_var.address
   datatype = version_var.datatype  # e.g., "UBYTE[16]"

   # Connect to ECU
   ap = ArgumentParser(description="Read SW version")
   with ap.run() as xcp:
       xcp.connect()

       # Read by address (from A2L)
       raw_data = xcp.fetch(address, length=16)
       version = raw_data.decode('utf-8').rstrip('\x00')

       print(f"Software Version: {version}")

       xcp.disconnect()


Complete Workflow: Calibration with A2L
----------------------------------------

This example demonstrates a full calibration cycle:

1. Load A2L database
2. Query characteristics (calibration parameters)
3. Read current values
4. Modify parameters
5. Write back to ECU
6. Verify changes

.. code-block:: python

   #!/usr/bin/env python
   """Complete A2L-based calibration workflow."""

   from pyxcp.cmdline import ArgumentParser
   from pya2ldb import DB
   import struct

   # === Configuration ===
   A2L_FILE = "my_ecu.a2l"
   PARAM_NAME = "InjectionTiming"  # Characteristic to calibrate

   # Load A2L
   db = DB()
   db.import_a2l(A2L_FILE)

   # Get parameter metadata
   param = db.query_characteristic(PARAM_NAME)
   address = param.address
   conversion = param.conversion  # e.g., RAT_FUNC with formula

   # Connect to ECU
   ap = ArgumentParser(description=f"Calibrate {PARAM_NAME}")
   with ap.run() as xcp:
       xcp.connect()

       # 1. Read current value (raw)
       raw_bytes = xcp.fetch(address, length=param.size)
       raw_value = struct.unpack(param.format_string, raw_bytes)[0]

       # 2. Convert to physical value (engineering units)
       if conversion:
           physical_value = conversion.raw_to_phys(raw_value)
       else:
           physical_value = raw_value

       print(f"Current {PARAM_NAME}: {physical_value} {param.unit}")

       # 3. Modify parameter
       new_physical = physical_value * 1.05  # 5% increase

       # 4. Convert back to raw value
       if conversion:
           new_raw = conversion.phys_to_raw(new_physical)
       else:
           new_raw = new_physical

       new_bytes = struct.pack(param.format_string, int(new_raw))

       # 5. Write to ECU
       xcp.download(address, new_bytes)
       print(f"Updated {PARAM_NAME}: {new_physical} {param.unit}")

       # 6. Verify
       verify_bytes = xcp.fetch(address, length=param.size)
       verify_raw = struct.unpack(param.format_string, verify_bytes)[0]
       verify_phys = conversion.raw_to_phys(verify_raw) if conversion else verify_raw

       assert abs(verify_phys - new_physical) < 0.01, "Verification failed!"
       print("✓ Verification passed")

       xcp.disconnect()


DAQ Setup with A2L Metadata
----------------------------

Use A2L file to automatically configure DAQ lists with symbolic names:

.. code-block:: python

   from pyxcp.cmdline import ArgumentParser
   from pyxcp.daq_stim import DaqList, DaqToCsv
   from pya2ldb import DB

   # Load A2L
   db = DB()
   db.import_a2l("my_ecu.a2l")

   # Define measurements to record
   measurements = ["EngineSpeed", "VehicleSpeed", "Throttle", "CoolantTemp"]

   # Build ODT entries from A2L
   odt_entries = []
   for name in measurements:
       meas = db.query_measurement(name)
       odt_entries.append({
           "address": meas.address,
           "size": meas.size,
           "name": name,
           "unit": meas.unit,
           "datatype": meas.datatype
       })

   # Connect and setup DAQ
   ap = ArgumentParser(description="DAQ from A2L")
   with ap.run() as xcp:
       xcp.connect()

       # Allocate DAQ list
       daq = DaqList(xcp, 0, event_channel=0)

       # Add ODTs from A2L metadata
       for entry in odt_entries:
           daq.add_odt_entry(
               address=entry["address"],
               size=entry["size"]
           )

       # Start recording
       csv_writer = DaqToCsv("recording.csv", header=[e["name"] for e in odt_entries])

       xcp.startDaq(daq.daq_list_number)

       # Collect 100 samples
       for _ in range(100):
           data = xcp.daqQueue.get(timeout=1.0)
           csv_writer.write_row(data)

       xcp.stopDaq()
       csv_writer.close()

       print("✓ Recording saved to recording.csv with symbolic names")

       xcp.disconnect()


See the complete example at: ``pyxcp/examples/daq_from_a2l.py``


A2L File Structure
-------------------

Understanding A2L structure helps troubleshoot issues:

.. code-block:: text

   /begin PROJECT MyProject
     /begin MODULE ECU_Controller

       /begin MEASUREMENT EngineSpeed  "Engine RPM"
         UWORD 0x4000  /* address */
         RAT_FUNC 1.0 0.0  /* factor, offset */
         0.0 8000.0  /* min, max */
         "rpm"  /* unit */
       /end MEASUREMENT

       /begin CHARACTERISTIC InjectionTiming  "Fuel injection timing"
         VALUE 0x5000  /* address */
         SWORD  /* datatype */
         RAT_FUNC 0.01 0.0  /* factor, offset */
         -50.0 50.0  /* min, max */
         "deg"  /* unit */
       /end CHARACTERISTIC

     /end MODULE
   /end PROJECT

**Key sections:**

- **MEASUREMENT**: Read-only variables (sensors, status)
- **CHARACTERISTIC**: Calibration parameters (maps, curves, scalars)
- **COMPU_METHOD**: Conversion formulas (RAT_FUNC, TAB_VERB, etc.)
- **IF_DATA XCP**: XCP-specific configuration (addresses, DAQ setup)


Data Type Conversion
---------------------

A2L defines conversion methods for raw ↔ physical values:

RAT_FUNC (Rational Function)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Most common conversion:

.. code-block:: text

   physical = (raw_value * factor) + offset

Example:

.. code-block:: python

   # A2L: RAT_FUNC 0.1 -40.0
   raw_value = 250
   physical = (250 * 0.1) + (-40.0)  # = -15.0 °C


TAB_VERB (Table Interpolation)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

For non-linear conversions:

.. code-block:: text

   /begin COMPU_METHOD LookupTable
     TAB_VERB "Lookup table"
     /begin COMPU_TAB_REF
       DEFAULT_VALUE "N/A"
       /begin VALUES
         0   0.0
         50  12.5
         100 25.0
         255 100.0
       /end VALUES
     /end COMPU_TAB_REF
   /end COMPU_METHOD


Working Example
---------------

Complete working example is available at:

**pyxcp/examples/a2l_integration.py**

Features:

- Loading A2L files
- Querying measurements and characteristics
- Reading parameters by name
- Writing calibration values
- DAQ setup with symbolic names
- CSV export with headers

Run it:

.. code-block:: bash

   python pyxcp/examples/a2l_integration.py --transport CAN --channel 0


Advanced: Production Workflows with asamint
--------------------------------------------

For production-grade measurement and calibration, use **asamint**:

**Key features:**

1. **Command-line MCS**: No GUI needed
2. **Batch operations**: Automate calibration campaigns
3. **MDF export**: Industry-standard format (ASAM MCD-3 MC)
4. **CDF creation**: Generate calibration data files
5. **Multiple projects**: Orchestrate pyxcp, pya2ldb, asammdf, objutils

**Example: Create CDF from XCP slave**

.. code-block:: bash

   # asamint example (command-line MCS)
   asamint create-cdf my_ecu.a2l --output calibration.cdf

**Example: Setup dynamic DAQ with MDF output**

.. code-block:: python

   # Using asamint API
   from asamint import Session

   session = Session("my_ecu.a2l")
   session.connect("CAN", channel=0)

   # High-level API
   session.setup_daq(["Speed", "Torque", "Temp"])
   session.record_mdf("recording.mdf", duration=60)

   session.disconnect()

**Learn more:**

- Repository: https://github.com/christoph2/asamint
- Examples: ``asamint/examples/`` directory
- Documentation: ``asamint/docs/``


Troubleshooting
---------------

Common A2L Issues
~~~~~~~~~~~~~~~~~

**"Measurement not found"**

- Check symbolic name spelling (case-sensitive!)
- Verify A2L file version matches ECU firmware
- Use ``db.list_measurements()`` to list all available

**"Address access error"**

- A2L address might be incorrect (wrong firmware version)
- ECU might require SEED/KEY unlock first
- Memory protection: use ``xcp.setCalPage()`` if needed

**"Conversion failed"**

- A2L might have invalid COMPU_METHOD
- Raw value out of bounds (check min/max)
- Use ``meas.conversion`` to inspect formula

**"DAQ configuration error"**

- ODT size exceeds max_dto (check A2L IF_DATA)
- Event channel not supported (query with ``xcp.getDaqEventInfo()``)
- Too many ODT entries (check DAQ limits)


Performance Tips
~~~~~~~~~~~~~~~~

1. **Batch reads**: Use ``xcp.upload(address, size)`` for multiple variables
2. **DAQ for monitoring**: Prefer DAQ over polling for high-rate signals
3. **Cache A2L database**: Don't reload A2L on every operation
4. **XCP master lock**: Use locking for multi-threaded calibration


FAQ
---

**Q: Can I use pyxcp without A2L files?**

Yes! pyxcp works with raw addresses. A2L provides symbolic access convenience.

**Q: What's the difference between pya2ldb and pya2l?**

- ``pya2l``: Legacy parser (deprecated)
- ``pya2ldb``: Modern database-backed parser (recommended)

**Q: Does pyxcp generate A2L files?**

No. A2L files are generated by ECU development tools (INCA, CANape, etc.).

**Q: When should I use asamint instead of pyxcp?**

Use asamint for:

- Command-line batch operations
- MDF output (industry standard)
- Orchestrating multiple ASAM tools
- Production measurement campaigns

Use pyxcp for:

- Custom Python applications
- Test automation
- Embedded in larger systems
- Learning XCP protocol

**Q: Can I edit A2L files?**

Technically yes (they're text files), but **not recommended**. A2L files are
generated from ECU source code and should stay in sync with firmware.

**Q: What if my ECU doesn't have an A2L file?**

You'll need to:

1. Get A2L from ECU supplier
2. Reverse-engineer memory layout (advanced!)
3. Use XCP with raw addresses only


Related Examples
----------------

See ``pyxcp/examples/`` directory:

- ``a2l_integration.py``: Complete A2L workflow
- ``daq_from_a2l.py``: DAQ setup from A2L
- ``calibration_workflow.py``: Raw address calibration
- ``daq_recording.py``: DAQ recording basics


References
----------

- **ASAM MCD-2 MC (A2L) Standard**: https://www.asam.net/standards/detail/mcd-2-mc/
- **pya2ldb Repository**: https://github.com/christoph2/pya2l
- **asamint Repository**: https://github.com/christoph2/asamint
- **pyxcp Repository**: https://github.com/christoph2/pyxcp
- **ASAM Standards**: https://www.asam.net/standards/

**Next steps:**

- Read :doc:`tutorial` for pyxcp basics
- Check :doc:`configuration` for advanced XCP setup
- Try :doc:`../examples/a2l_integration` for hands-on practice

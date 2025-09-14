# pyXCP

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/85f774708b2542d98d02df55c743d24a)](https://app.codacy.com/app/christoph2/pyxcp?utm_source=github.com&utm_medium=referral&utm_content=christoph2/pyxcp&utm_campaign=Badge_Grade_Settings)
[![Maintainability](https://api.codeclimate.com/v1/badges/4c639f3695f2725e392a/maintainability)](https://codeclimate.com/github/christoph2/pyxcp/maintainability)
[![Build Status](https://github.com/christoph2/pyxcp/workflows/Python%20application/badge.svg)](https://github.com/christoph2/pyxcp/actions)
[![Build status](https://ci.appveyor.com/api/projects/status/r00l4i4co095e9ht?svg=true)](https://ci.appveyor.com/project/christoph2/pyxcp)
[![Coverage Status](https://coveralls.io/repos/github/christoph2/pyxcp/badge.svg?branch=master)](https://coveralls.io/github/christoph2/pyxcp?branch=master)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)
[![GPL License](http://img.shields.io/badge/license-GPL-blue.svg)](http://opensource.org/licenses/GPL-2.0)

pyXCP is a lightweight Python library which talks to ASAM MCD-1 XCP enabled devices.
These are mainly, but not only, automotive ECUs (Electronic Control Units).

XCP (Universal Measurement and Calibration Protocol) is used to take measurements, to adjust parameters, and to flash during the development process.

XCP also replaces the older CCP (CAN Calibration Protocol).

---

## Installation

pyXCP is hosted on Github, get the latest release: [https://github.com/christoph2/pyxcp](https://github.com/christoph2/pyxcp)

You can install pyxcp from PyPI:

```
pip install pyxcp
```

Alternatively, you can install pyxcp from source with pip:

```
pip install git+https://github.com/christoph2/pyxcp.git
```

Or install from source:

```
pip install -e .
```

### Requirements

- Python >= 3.8
- Dependencies (automatically installed):
  - construct
  - mako
  - pyserial
  - pyusb
  - python-can
  - rich
  - toml
  - tomlkit
  - pytz
- A running XCP slave (of course).
- If you are using a 64bit Windows version and want to use seed-and-key .dlls (to unlock resources), a GCC compiler capable of creating 32bit
  executables is required:

  These .dlls almost always ship as 32bit versions, but you can't load a 32bit .dll into a 64bit process, so a small bridging program (asamkeydll.exe) is
  required.

## Features

- Support for multiple transport layers:
  - CAN (Controller Area Network)
  - Ethernet
  - SxI (Serial/UART)
  - USB
- Data Acquisition (DAQ) functionality:
  - Online mode: collect and process data while DAQ measurement is running
  - Offline mode: record data to .xmraw files for later processing
  - Support for various data types including 16-bit floating-point variables
  - Export to multiple formats: CSV, Parquet, MDF, SQLite, etc.
- Parameter adjustment
- Flashing capabilities
- Resource unlocking with seed-and-key mechanisms
- Command-line tools:
  - xcp-info: Display information about connected XCP slaves
  - xcp-profile: Create and convert configuration files
  - xcp-id-scanner: Scan for XCP slaves
  - xcp-fetch-a2l: Fetch A2L files from XCP slaves
  - xmraw-converter: Convert .xmraw files to other formats
- Python-based configuration system
- Timestamping with nanosecond resolution
- Ability to reuse existing communication links

## First steps

Here's a simple example to connect to an XCP slave and get basic information:

```python
from pyxcp.cmdline import ArgumentParser

# Create an argument parser with default options
ap = ArgumentParser(description="pyXCP hello world")

# Connect to the XCP slave
with ap.run() as x:
    x.connect()

    # Get slave identifier
    identifier = x.identifier(0x01)
    print(f"ID: {identifier!r}")

    # Print slave properties
    print(x.slaveProperties)

    # Conditionally unlock resources
    x.cond_unlock()

    # Get protection status
    cps = x.getCurrentProtectionStatus()
    print("Protection Status:")
    for k, v in cps.items():
        print(f"    {k:6s}: {v}")

    # Disconnect
    x.disconnect()
```

For DAQ (Data Acquisition) functionality:

```python
from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqRecorder

# Define DAQ lists with measurements
DAQ_LISTS = [
    DaqList(
        name="measurements",
        event_num=0,
        stim=False,
        enable_timestamps=True,
        measurements=[
            ("parameter1", 0x12345678, 0, "U16"),
            ("parameter2", 0x12345680, 0, "F32"),
        ],
        priority=0,
        prescaler=1,
    ),
]

# Create a recorder to save data to .xmraw file
daq_parser = DaqRecorder(DAQ_LISTS, "recording", 2)

# Connect and start DAQ
with ap.run(policy=daq_parser) as x:
    x.connect()
    x.cond_unlock("DAQ")  # Unlock DAQ resource

    # Setup and start DAQ
    daq_parser.setup()
    daq_parser.start()

    # Run for some time
    time.sleep(10.0)

    # Stop DAQ
    daq_parser.stop()
    x.disconnect()
```

## Configuration

pyXCP uses Python-based configuration files. You can create a default configuration with:

```shell
xcp-profile create -o pyxcp_conf.py
```

Example configuration for CAN transport:

```python
c.Transport.layer = 'CAN'
c.Transport.Can.can_driver = 'kvaser'
c.Transport.Can.channel = '0'
c.Transport.Can.bitrate = 500000
c.Transport.Can.can_id_master = 0x300
c.Transport.Can.can_id_slave = 0x301
```

## Documentation

For more detailed documentation and examples, see:

- [Tutorial](docs/tutorial2.md)
- [Examples directory](pyxcp/examples/)
- [Command-line tools](docs/howto_cli_tools.rst)

## References

- [Official home of XCP](https://www.asam.net/standards/detail/mcd-1-xcp/)

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

GNU Lesser General Public License v3 or later (LGPLv3+)

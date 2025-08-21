# pyXCP

Reliable Python tooling for the ASAM MCD‑1 XCP protocol (measurement, calibration, flashing) with multiple transports (CAN, Ethernet, USB, Serial) and handy CLI utilities.

[![CI](https://github.com/christoph2/pyxcp/workflows/Python%20application/badge.svg)](https://github.com/christoph2/pyxcp/actions)
[![PyPI](https://img.shields.io/pypi/v/pyxcp.svg)](https://pypi.org/project/pyxcp/)
[![Python Versions](https://img.shields.io/pypi/pyversions/pyxcp.svg)](https://pypi.org/project/pyxcp/)
[![License: LGPL v3+](https://img.shields.io/badge/License-LGPL%20v3%2B-blue.svg)](https://www.gnu.org/licenses/lgpl-3.0)
[![Code style: black](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

pyXCP is a production-ready Python library for communicating with XCP-enabled devices, most commonly automotive ECUs. Use it to take measurements, adjust parameters (calibration), stream DAQ/STIM, and program devices during development.

Highlights:
- Transports: Ethernet (TCP/IP), CAN, USB, Serial (SxI)
- Cross‑platform: Windows, Linux, macOS
- Rich CLI tools for common XCP tasks
- Extensible architecture and layered design

---

## Installation

The easiest way is from PyPI:

```shell
pip install pyxcp
```

To install from the main branch:

```shell
pip install git+https://github.com/christoph2/pyxcp.git
```


### Requirements
- Python >= 3.10
- Building from source requires a working C/C++ toolchain (native extensions are used for performance). Wheels are provided for common platforms and Python versions; if a wheel is not available, pip will build from source.
- An XCP slave device (or simulator)

## Quick start

The tutorial walks you through typical tasks end‑to‑end: see docs/tutorial.md.

Minimal example using the built‑in argument parser and context manager:

```python
from pyxcp.cmdline import ArgumentParser

ap = ArgumentParser(description="pyXCP hello world")

with ap.run() as x:
    x.connect()
    identifier = x.identifier(0x01)
    print(f"ID: {identifier!r}")
    print(x.slaveProperties)
    x.disconnect()
```

### Configuration
pyXCP supports a [traitlets](https://github.com/ipython/traitlets)‑based configuration system.
- Recommended Python config example and generator: docs/tutorial.md and docs/configuration.md
- Legacy TOML examples remain available for compatibility.

### Command‑line tools
Installed entry points (see pyproject.toml):
- xcp-info — print capabilities and properties
- xcp-id-scanner — scan for slave identifiers
- xcp-fetch-a2l — retrieve A2L from target (if supported)
- xcp-profile — generate/convert config files
- xcp-examples — launch assorted demos/examples
- xmraw-converter — convert recorder .xmraw data
- pyxcp-probe-can-drivers — list available CAN interfaces

Run any tool with -h for options.

## Features
- Multiple transport layers: Ethernet (TCP), CAN, USB, SxI (serial/UART)
- Data Acquisition (DAQ) and Stimulation (STIM)
- Calibration (read/write parameters)
- Flashing/programming workflows
- A2L (ASAM MCD‑2 MC) support
- Recorder utilities and converters (see docs/recorder.md)
- Extensible architecture for custom transports

## Documentation
- Getting started tutorial: docs/tutorial.md
- Configuration: docs/configuration.md
- CAN driver setup and troubleshooting: docs/howto_can_driver.md
- Recorder: docs/recorder.md

To build the Sphinx documentation locally:
1. Install doc requirements: `pip install -r docs/requirements.txt`
2. Build: `sphinx-build -b html docs docs/_build/html`
3. Open `docs/_build/html/index.html`

## Compatibility
- Operating systems: Windows, Linux, macOS
- Python: 3.10 - 3.14, CPython wheels where available
- CAN backends: python-can compatible drivers (see docs/howto_can_driver.md)

## Contributing
Contributions are welcome! Please:
- Read CODE_OF_CONDUCT.md
- Open an issue or discussion before large changes
- Use [pre-commit](https://github.com/pre-commit/pre-commit) to run linters and tests locally

## License
GNU Lesser General Public License v3 or later (LGPLv3+). See LICENSE for details.

## References
- ASAM MCD‑1 XCP standard: https://www.asam.net/standards/detail/mcd-1-xcp/


## About ASAM MCD‑1 XCP
XCP (Universal Measurement and Calibration Protocol) is an ASAM standard defining a vendor‑neutral protocol to access internal data of electronic control units (ECUs) for measurement, calibration (parameter tuning), and programming. XCP decouples the protocol from the physical transport, so the same command set can be carried over different buses such as CAN, FlexRay, Ethernet, USB, or Serial.

- Roles: An XCP Master (this library) communicates with an XCP Slave (your device/ECU or simulator).
- Layered concept: XCP defines an application layer and transport layers. pyXCP implements the application layer and multiple transport bindings.
- Use cases:
  - Measurement: Read variables from the ECU in real‑time, including high‑rate DAQ streaming.
  - Calibration: Read/write parameters (calibration data) in RAM/flash.
  - Programming: Download new program/data to flash (where the slave supports it).

For the authoritative description, see the ASAM page: https://www.asam.net/standards/detail/mcd-1-xcp/

## XCP in a nutshell
- Connect/Session: The master establishes a connection, negotiates capabilities/features, and optionally unlocks protected functions via seed & key.
- Addressing: Memory is accessed via absolute or segment‑relative addresses. Addressing modes are described in the associated A2L file (ASAM MCD‑2 MC), which maps symbolic names to addresses, data types, and conversion rules.
- Events: The slave exposes events (e.g., “1 ms task”, “Combustion cycle”), which trigger DAQ sampling. The master assigns signals (ODTs) to these events for time‑aligned acquisition.
- DAQ/STIM: DAQ = Data Acquisition (slave → master), STIM = Stimulation (master → slave). Both use event‑driven lists for deterministic timing.
- Timestamps: DAQ may carry timestamps from the slave for precise time correlation.
- Security: Access to sensitive commands (e.g., programming, calibration) can be protected by a seed & key algorithm negotiated at runtime.
- Checksums: XCP defines checksum services useful for verifying memory regions (e.g., after flashing).

## Relation to A2L (ASAM MCD‑2 MC)
While XCP defines the protocol, the A2L file describes the measurement and calibration objects (characteristics, measurements), data types, conversion rules, and memory layout. In practice, you use pyXCP together with an A2L to:
- Resolve symbolic names to addresses and data types.
- Configure DAQ lists from human‑readable signal names.
- Interpret raw values using the appropriate conversion methods.

pyXCP provides utilities to fetch A2L data when supported by the slave and to work with A2L‑described objects.
See also [pya2ldb](https://github.com/christoph2/pya2l)!

## Transports and addressing
XCP is transport‑agnostic. pyXCP supports multiple transports and addressing schemes:
- CAN (XCP on CAN): Robust and ubiquitous in vehicles; limited payload and bandwidth; suited for many calibration tasks and moderate DAQ rates.
- Ethernet (XCP on TCP/UDP): High bandwidth with low latency; well suited for rich DAQ and programming workflows.
- USB: High throughput for lab setups; requires device support.
- Serial/SxI: Simple point‑to‑point links for embedded targets and simulators.

The exact capabilities (e.g., max CTO/DTO, checksum types, timestamping) are negotiated at connect time and depend on the slave and transport.

## Supported features (overview)
The scope of features depends on the connected slave. At the library level, pyXCP provides:
- Session management: CONNECT/DISCONNECT, GET_STATUS/SLAVE_PROPERTIES, communication mode setup, error handling.
- Memory access: Upload/short upload, Download/Download Next, verifications, optional paged memory where supported.
- DAQ/STIM: Configuration of DAQ lists/ODTs, event assignment, data streaming, timestamp handling when available.
- Programming helpers: Building blocks for program/erase/write flows (exact sequence per slave’s flash algorithm and A2L description).
- Security/Seed & Key: Pluggable seed‑to‑key resolution including 32↔64‑bit bridge on Windows.
- Utilities: Identifier scanning, A2L helpers, recorder and converters.

Refer to docs/tutorial.md and docs/configuration.md for feature usage, and xcp-info for a capability dump of your target.

## Compliance and versions
pyXCP aims to be compatible with commonly used parts of ASAM MCD‑1 XCP. Specific optional features are enabled when a slave advertises them during CONNECT. Because implementations vary across vendors and ECU projects, always consult your A2L and use xcp-info to confirm negotiated options (e.g., checksum type, timestamp unit, max DTO size, address granularity).

If you rely on a particular XCP feature/profile not mentioned here, please open an issue with details about your slave and A2L so we can clarify support and—if feasible—add coverage.

## Safety, performance, and limitations
- Safety‑critical systems: XCP is a development and testing protocol. Do not enable measurement/calibration on safety‑critical systems in the field unless your system‑level safety case covers it.
- Performance: Achievable DAQ rates depend on transport bandwidth, ECU event rates, DTO sizes, and host processing. Ethernet typically yields the highest throughput.
- Latency/jitter: Event scheduling in the slave and OS scheduling on the host can affect determinism. Use timestamps to correlate data precisely.
- Access control: Seed & key protects sensitive functions; your organization’s policy should govern algorithm distribution and access.

## Further resources
- ASAM MCD‑1 XCP standard (overview and membership): https://www.asam.net/standards/detail/mcd-1-xcp/
- ASAM MCD‑2 MC (A2L) for object descriptions: https://www.asam.net/standards/detail/mcd-2-mc/
- Introduction to DAQ/STIM concepts (ASAM publications and vendor docs)
- Related: CCP (legacy predecessor to XCP), ASAM MDF for measurement data storage

# pyXCP Development Guide

pyXCP is a production-ready Python library implementing the ASAM MCD-1 XCP protocol for automotive measurement, calibration, and flashing. The library includes Python code, native C++ extensions (via pybind11), and comprehensive transport layer support (CAN, Ethernet, USB, Serial).

## Build and Test Commands

### Building from Source

```bash
# Install dependencies (uses Poetry)
poetry install

# Build C++ extensions
python build_ext.py

# Alternative: full wheel build with cibuildwheel
pip install cibuildwheel
cibuildwheel --platform linux  # or macos, windows
```

The build process:
- Uses Poetry as the build backend (`poetry.core.masonry.api`)
- Compiles pybind11 C++ extensions for performance-critical components
- Requires a working C/C++ toolchain (MSVC on Windows, GCC/Clang on Unix)
- See `build_ext.py` for platform-specific Python library detection logic

**Platform-specific notes:**
- **Windows**: Requires Visual Studio Build Tools or Visual Studio (MSVC compiler)
- **macOS**: Uses `MACOSX_DEPLOYMENT_TARGET=10.13` (set in `build_ext.py`)
- **Linux**: Requires GCC or Clang with C++23 support
- C++ standard: C++23 (see `CMakeLists.txt` line 15)
- Build artifacts go to `dist/` directory

### Testing

```bash
# Run all tests
pytest

# Run a specific test file
pytest pyxcp/tests/test_can.py

# Run a single test function
pytest pyxcp/tests/test_can.py::testSet0

# Run with coverage
pytest --cov=pyxcp --cov-report=html

# Tests output to result.xml (JUnit format)
```

Test organization:
- Tests are in `pyxcp/tests/`
- Test files use `test_*.py` naming
- Individual tests use `def test*()` or `def testCamelCase()` naming (mixed convention)

### Linting and Formatting

```bash
# Run pre-commit hooks (recommended - runs all checks)
pre-commit run --all-files

# Install pre-commit hooks (one-time setup)
pre-commit install

# Format code with ruff
ruff format .

# Lint with ruff
ruff check . --fix

# Security scanning with bandit
bandit -c bandit.yml -r pyxcp/

# Type checking with mypy
mypy pyxcp/
```

Code style:
- Line length: 132 characters
- Formatter: ruff (replaces black)
- Linter: ruff with custom config in `pyproject.toml`
- Pre-commit hooks enforce format, lint, and security checks
- Pre-commit config in `.pre-commit-config.yaml` includes:
  - File checks (large files, TOML/JSON/YAML syntax, merge conflicts)
  - Line ending normalization (LF)
  - Ruff formatting and linting
  - Bandit security scanning

## Architecture Overview

### Core Components

1. **Master Layer** (`pyxcp/master/`)
   - `Master` class: Main API for XCP communication
   - `calibration.py`: Parameter read/write operations
   - `errorhandler.py`: XCP error code handling

2. **Transport Layer** (`pyxcp/transport/`)
   - Abstract base: `base.py` defines transport interface
   - Implementations: `can.py`, `eth.py`, `sxi.py`, `usb_transport.py`
   - C++ extensions: `transport_ext.*.pyd` for performance-critical paths
   - Each transport handles framing, addressing, and protocol-specific details

3. **DAQ/STIM** (`pyxcp/daq_stim/`)
   - Data Acquisition and Stimulation logic
   - High-performance streaming support
   - Timestamp correlation (including IEEE 1588/PTP hardware timestamps)

4. **Recorder** (`pyxcp/recorder/`)
   - Recording utilities for XCP sessions
   - Includes vendored C++ libraries (simdjson, lz4) for performance
   - Converter: `xmraw-converter` CLI tool

5. **Configuration** (`pyxcp/config/`)
   - Traitlets-based configuration system (modern approach)
   - Legacy TOML support in `legacy.py`
   - Pydantic models in `models.py`

6. **CLI Scripts** (`pyxcp/scripts/`)
   - Entry points defined in `pyproject.toml` under `[tool.poetry.scripts]`
   - Use `ArgumentParser` from `pyxcp/cmdline.py` for consistent argument handling
   - Available tools:
     - `xcp-info`: Print slave capabilities and properties
     - `xcp-id-scanner`: Scan for XCP slave identifiers on the bus
     - `xcp-fetch-a2l`: Retrieve A2L file from target (if supported)
     - `xcp-profile`: Generate/convert configuration files
     - `xcp-examples`: Launch demo examples
     - `xmraw-converter`: Convert recorder .xmraw data files
     - `pyxcp-probe-can-drivers`: List available CAN interfaces

### Native Extensions

The project compiles C++ modules for performance:
- Built with CMake (see `CMakeLists.txt`) via `build_ext.py`
- pybind11 bindings connect C++ to Python
- Extensions are in: `cpp_ext/`, `daq_stim/`, `recorder/`, `transport/`
- Distributed as platform-specific wheels (`.pyd` on Windows, `.so` on Unix)

When modifying C++ code:
- C++ source files use `.cpp` and `.hpp` extensions
- Header files have corresponding implementation files
- Rebuild with `python build_ext.py` after changes
- CMake configuration in `CMakeLists.txt` sets compiler flags:
  - Debug mode: AddressSanitizer enabled on all platforms
  - Release mode: O3 optimization
  - Windows: `/std:c++latest /permissive- /EHsc`
  - Unix: `-std=c++23 -Wall -Wextra -Wpedantic`
- Extensions are named: `<module>_ext.cp3XX-<platform>.pyd/so`
- Each major module has a wrapper file (e.g., `transport_wrapper.cpp`, `stim_wrapper.cpp`)

### Transport Layer Details

Each transport inherits from `base.BaseTransport`:
- **CAN** (`can.py`): Uses python-can, supports extended IDs and CAN-FD
  - Identifier calculation: see `calculate_filter()` and `Identifier` class
  - Frame padding: `pad_frame()` and `set_DLC()` functions
- **Ethernet** (`eth.py`, `eth_block.py`): TCP and UDP with optional IEEE 1588
- **USB** (`usb_transport.py`): Via pyusb
- **Serial** (`sxi.py`): UART/SxI protocol

## Key Conventions

### Project-Specific Patterns

1. **Context Manager Usage**
   ```python
   from pyxcp.cmdline import ArgumentParser

   ap = ArgumentParser(description="...")
   with ap.run() as x:
       x.connect()
       # ... XCP operations
       x.disconnect()
   ```
   Always use the context manager pattern for Master connections.

2. **Configuration via Traitlets**
   Modern configuration uses traitlets (not TOML):
   ```python
   from pyxcp.config.models import XcpConfig
   config = XcpConfig(...)
   ```

3. **Error Handling**
   XCP protocol errors are handled via `errorhandler.py`. Check error matrices in `errormatrix.py` for troubleshooting.

4. **Versioning**
   Version is managed by bumpver:
   - Update with: `bumpver update --patch` (or --minor/--major)
   - Auto-updates `pyproject.toml` and `pyxcp/__init__.py`

5. **C++ Extension Naming**
   Extension modules follow the pattern: `<module>_ext.cp3XX-<platform>.pyd/so`
   - Import in Python as: `from pyxcp.transport import transport_ext`

### Testing Patterns

- Tests use pytest fixtures sparingly; most use direct instantiation
- Mock transport available: `pyxcp.transport.mock`
- Some tests may require hardware (CAN adapters, ECUs) and are skipped in CI
- Test naming uses mixed conventions: both `test_*()` and `testCamelCase()` formats exist
- Coverage reports can be generated to HTML for detailed analysis

### Documentation

- Main docs in `docs/` (ReStructuredText for Sphinx)
- README is `docs/README.rst` (symlinked as package readme)
- Build docs:
  1. Install requirements: `pip install -r docs/requirements.txt`
  2. Build: `sphinx-build -b html docs docs/_build/html`
  3. Open: `docs/_build/html/index.html`
- Key documentation files:
  - `tutorial.rst`: Getting started guide
  - `configuration.rst`: Traitlets-based config system
  - `howto_can_driver.rst`: CAN driver setup and troubleshooting
  - `recorder.rst`: Recording utilities
  - `troubleshooting.rst` and `troubleshooting_matrix.rst`: Error diagnosis

## ASAM Standards Context

pyXCP implements ASAM MCD-1 (XCP) protocol:
- XCP = Universal Calibration Protocol
- Used for ECU measurement and calibration in automotive development
- Supports A2L files (ASAM MCD-2 MC) for variable descriptions
- Protocol details: see ASAM specifications (not included)

Common XCP terminology:
- **Master**: Tool/PC initiating communication (this library)
- **Slave**: Target device (ECU) responding to commands
- **DAQ**: Data Acquisition (streaming measurements from slave)
- **STIM**: Stimulation (streaming data to slave)
- **ODT**: Object Descriptor Table (DAQ configuration unit)
- **A2L**: ASAP2 file describing ECU memory layout

## Dependencies

Key runtime dependencies:
- `construct`: Binary data parsing (XCP protocol frames)
- `python-can`: CAN bus support (multiple backend drivers)
- `pyserial`: Serial port communication
- `pyusb`: USB transport
- `pydantic`: Configuration validation
- `rich`: CLI output formatting

Development dependencies are extensive (see `pyproject.toml`). Use Poetry's lock file for reproducible builds.

## Related Projects

This codebase is part of a suite:
- **pya2ldb**: A2L file parser (used by pyxcp for calibration)
- **cxcp**: C implementation of XCP
- **objutils**: Binary file format utilities (Intel Hex, S-records, etc.)

These may be referenced in documentation or as optional dependencies.

## Development Workflow

### Making Changes

1. **Before coding**: Install pre-commit hooks with `pre-commit install`
2. **While coding**:
   - Follow the 132-character line length limit
   - Use the context manager pattern for XCP connections (see Key Conventions)
   - For C++ changes, rebuild extensions after modifications
3. **Before committing**:
   - Run `pre-commit run --all-files` to catch issues
   - Run relevant tests: `pytest pyxcp/tests/test_<module>.py`
   - For significant changes, run full test suite: `pytest`
4. **Version bumping**: Use `bumpver update --patch/--minor/--major` (updates both `pyproject.toml` and `pyxcp/__init__.py`)

### Common Tasks

- **Adding a new transport**: Inherit from `base.BaseTransport` and implement required methods
- **Adding CLI tools**: Add entry point in `[tool.poetry.scripts]` section of `pyproject.toml`
- **Debugging C++ extensions**: Build with Debug mode, AddressSanitizer is automatically enabled
- **Testing with real hardware**: Some tests are hardware-dependent; use mock transport for CI

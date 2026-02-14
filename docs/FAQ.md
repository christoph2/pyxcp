# FAQ - Frequently Asked Questions

## Installation & Build Issues

### Q: `ModuleNotFoundError: No module named 'pyxcp.transport.transport_ext'`

**A:** This is a build issue where the C++ extensions weren't compiled correctly. Try these solutions in order:

1. **Install from PyPI with pre-built wheels (recommended):**
   ```bash
   pip install --upgrade pip
   pip install pyxcp
   ```

2. **If that fails, install build dependencies first:**

   **Ubuntu/Debian:**
   ```bash
   sudo apt update
   sudo apt install build-essential cmake python3-dev libpython3-dev pybind11-dev
   pip install pyxcp
   ```

   **Windows:**
   - Install [Visual Studio Build Tools](https://visualstudio.microsoft.com/downloads/#build-tools-for-visual-studio-2022)
   - Select "Desktop development with C++"
   ```cmd
   pip install pyxcp
   ```

   **macOS:**
   ```bash
   brew install cmake pybind11
   pip install pyxcp
   ```

3. **Build from source manually:**
   ```bash
   git clone https://github.com/christoph2/pyxcp.git
   cd pyxcp
   python build_ext.py
   pip install -e .
   ```

**Related issues:** #240, #188, #199, #169

---

### Q: Cannot build pyxcp on Ubuntu 24.04 - `FileNotFoundError: 'cmake'`

**A:** CMake is not installed. Install required build tools:

```bash
# Ubuntu/Debian
sudo apt update
sudo apt install build-essential cmake python3-dev libpython3-dev pybind11-dev

# Verify installation
cmake --version
python3-config --libs
```

Then install pyxcp:
```bash
pip install pyxcp
```

**Related issues:** #169

---

### Q: `UnboundLocalError: cannot access local variable 'libdir'` during build

**A:** The build system cannot find the Python development libraries. Install them:

```bash
# Ubuntu/Debian
sudo apt install python3-dev libpython3-dev

# Verify Python library exists
find /usr -name "libpython*.so"
find /usr -name "libpython*.a"
```

If the second command returns nothing, the Python link library is missing. Install the appropriate `python3.X-dev` package for your Python version.

**Related issues:** #169

---

### Q: PyInstaller/py2exe: pyxcp module not found after bundling

**A:** PyInstaller needs to be told about the native extensions. Create a hook file:

**Option 1: Use hook file (recommended)**

Create `hook-pyxcp.py` next to your script:
```python
from PyInstaller.utils.hooks import collect_dynamic_libs

# Collect all native extensions
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
```

Build with:
```bash
pyinstaller --additional-hooks-dir=. your_script.py
```

**Option 2: Specify in .spec file**

Add to your `.spec` file:
```python
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
```

**Related issues:** #261, #203

---

## Configuration

### Q: DaqToCsv fails with FileNotFoundError when running from Robot Framework

**A:** **FIXED in v0.26.4+**. `DaqToCsv` and other DAQ classes now work without requiring a configuration file.

**The Problem:**
When running from test frameworks like Robot Framework or pytest, the current working directory
is different from your project root, causing `FileNotFoundError: Configuration file 'pyxcp_conf.py' does not exist`.

**Solution 1: Pass a logger explicitly** (recommended):
```python
import logging
from pyxcp.daq_stim import DaqToCsv

# Create your own logger
logger = logging.getLogger('my_daq_logger')
logger.addHandler(logging.StreamHandler())
logger.setLevel(logging.INFO)

# Pass logger to DaqToCsv
daq_policy = DaqToCsv(daq_lists, logger=logger)
```

**Solution 2: Use in Robot Framework**:
```robot
*** Settings ***
Library  pyxcp.daq_stim

*** Test Cases ***
My DAQ Test
    ${logger} =  Get Logger  my_robot_logger
    ${daq_policy} =  Create DaqToCsv  ${daq_lists}  logger=${logger}
```

**Solution 3: Set PYXCP_CONFIG environment variable** (future enhancement):
```bash
export PYXCP_CONFIG=/absolute/path/to/pyxcp_conf.py
# Or in Robot Framework:
Set Environment Variable  PYXCP_CONFIG  ${PROJECT_ROOT}/config/pyxcp_conf.py
```

**Note:** As of v0.26.4, DAQ classes automatically use a fallback logger when no configuration
is available, so you can also just create `DaqToCsv(daq_lists)` without any logger parameter.

**Related issues:** #260

---

## DAQ (Data Acquisition)

### Q: How do I get DAQ data from the slave?

**A:** Use the DAQ recording policy. Here's a complete example:

```python
from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqListEntry

# Setup config with DAQ policy
ap = ArgumentParser(description="DAQ Example")
# Configure in your config file or programmatically

with ap.run() as x:
    x.connect()

    # Define what to measure
    daq_list = DaqList(
        name="my_measurements",
        event_num=0,  # Event channel number
        stim=False,
        enable_timestamps=True,
        entries=[
            DaqListEntry(name="signal1", address=0x1000, size=4),
            DaqListEntry(name="signal2", address=0x1004, size=2),
        ]
    )

    # Start DAQ
    x.setupDaq([daq_list])
    x.startStopSynch(0x01)  # Start measurement

    # Read data (method depends on policy)
    # For queue-based policy:
    while True:
        data = x.daqQueue.get(timeout=1.0)
        print(f"Received: {data}")

    # Stop
    x.startStopSynch(0x00)  # Stop measurement
    x.disconnect()
```

**See also:**
- `pyxcp/examples/` folder for complete working examples
- `docs/tutorial.rst` for detailed DAQ setup

**Related issues:** #156, #142, #164, #210

---

### Q: My ECU doesn't support GET_DAQ_PROCESSOR_INFO and throws ERR_CMD_UNKNOWN. What should I do?

**A:** As of version 0.26.3, pyxcp automatically handles ECUs that don't support GET_DAQ_PROCESSOR_INFO (which is optional per XCP spec).

When this command fails, pyxcp uses conservative fallback defaults:
- Dynamic DAQ configuration (requires ALLOC_DAQ)
- No timestamp support
- No prescaler support
- Standard identification field (IDF_ABS_ODT_NUMBER)

**To use DAQ with such ECUs:**

```python
# This will now work even if GET_DAQ_PROCESSOR_INFO is not supported
daq_info = master.getDaqInfo(include_event_lists=False)

# You'll need to manually configure DAQ lists using dynamic allocation
master.freeDaq()  # Clear any existing configuration
master.allocDaq(1)  # Allocate 1 DAQ list
master.allocOdt(0, 1)  # Allocate 1 ODT for DAQ list 0
master.allocOdtEntry(0, 0, 2)  # Allocate 2 entries in ODT 0

# Then configure and start as usual
master.setDaqPtr(0, 0, 0)
master.writeDaq(0, 4, 0, address1)  # Add measurements
master.writeDaq(0, 4, 0, address2)
master.setDaqListMode(0x10, 0, event_channel, 1, 0)
master.startStopDaqList(1, 0)
master.startStopSynch(1)
```

**Note:** You'll see a warning in the logs when fallback mode is used:
```
WARNING: GET_DAQ_PROCESSOR_INFO not supported by ECU (error: ERR_CMD_UNKNOWN). Using fallback defaults. DAQ functionality may be limited.
```

**Related Issues:** #230, #184

---

### Q: I get "NotImplementedError: Pre-action REINIT_DAQ" when using multiple DAQ lists. How do I fix this?

**A:** Fixed in version 0.26.3! This error occurred when the XCP slave required a FREE_DAQ command before re-allocating DAQ lists.

The error handler now automatically calls `freeDaq()` as a pre-action when the slave indicates REINIT_DAQ is needed.

**Before 0.26.3 (workaround):**
```python
# Had to manually free and re-setup
master.freeDaq()
daq_parser.setup()  # Setup all DAQ lists again
```

**After 0.26.3:**
```python
# Just configure multiple DAQ lists - automatic handling
daq_lists = [
    DaqList(name="List1", measurements=[...]),
    DaqList(name="List2", measurements=[...]),
]
daq_parser = Daq(master, daq_lists)
daq_parser.setup()  # Works automatically!
```

**Related Issues:** #208

---

### Q: `WRITE_DAQ` fails with `ERR_OUT_OF_RANGE (0x22)`

**A:** The address you're trying to write is out of range for the DAQ list. Check:

1. **Verify address is correct** - Use `shortUpload` to test:
   ```python
   data = x.shortUpload(0x1000, 4)  # Should succeed
   ```

2. **Check ODT limits** - DAQ entry might exceed ODT size
3. **Ensure address is aligned** - Some ECUs require 2/4-byte alignment
4. **Check A2L file** - Verify address matches measurement definition

**Related issues:** #253

---

### Q: DAQ has ~60ms delay every few readings

**A:** This is caused by buffering. You can:

1. **Reduce buffer size** in transport layer config:
   ```python
   c.Transport.buffer_size = 1  # Minimize buffering
   ```

2. **Use hardware timestamps** if available (Ethernet/UDP with IEEE 1588)

3. **Increase DAQ event rate** - Check ECU configuration

**Related issues:** #218

---

### Q: Memory grows continuously when using DAQ

**A:** Known issue with event queue not being cleared. Workarounds:

1. **Use HDF5 policy** (streaming to disk):
   ```python
   from pyxcp.transport.hdf5_policy import Hdf5Policy
   # Configure policy in your config
   ```

2. **Manually clear queue** periodically:
   ```python
   while not x.daqQueue.empty():
       x.daqQueue.get_nowait()
   ```

3. **Use fixed-size queue** with maxsize parameter

**This will be fixed in an upcoming release.**

**Related issues:** #171, #110

---

## CAN Transport

### Q: CAN DAQ gets interrupted after connection / unexpected messages

**A:** **FIXED in v0.26.3+**. The CAN filter timing has been improved to prevent Basic Traffic from entering the buffer between bus start and filter activation.

Additionally, DAQ ID filters can now be updated dynamically after connection:

```python
# Filters are set at connect() time
x.connect()

# If DAQ IDs become known later, update filters:
if hasattr(x.transport, 'can_interface'):
    x.transport.can_interface.update_daq_filters(daq_ids)
```

**Tip:** If you still encounter unexpected CAN messages, enable debug logging to see which IDs are being received:
```python
import logging
logging.basicConfig(level=logging.DEBUG)
```

**Related issues:** #231, #136

---

### Q: Vector CANape / XCPsim connection timeout with "XCPsim" app_name

**A:** Configure the Vector app_name in your config:

```python
from pyxcp.config import PyXCP

app = PyXCP()
app.transport.can.interface = "vector"
app.transport.can.channel = "0"
app.transport.can.vector.app_name = "XCPsim"  # Set Vector application name

# Use config with Master
from pyxcp import Master
with Master("can", config=app) as xm:
    xm.connect()
```

**Note:** `app_name` parameter support depends on your python-can version:
- python-can < 4.0: May need to manually modify VectorBus source
- python-can >= 4.0: Should work via configuration

**Verify parameter is passed:**
```python
# Check log output when connecting:
# "XCPonCAN - Interface-Type: 'vector' Parameters: [('app_name', 'XCPsim'), ...]"
```

**Alternative:** Use Vector's CANcase to configure the application name in Vector Hardware Config, then use serial number instead:
```python
app.transport.can.vector.serial = 12345  # Your CANcase serial
```

**Related issues:** #224

---

### Q: How do I use multiple CAN channels simultaneously?

**A:** Currently, one Master instance = one CAN channel. To use multiple channels:

```python
# Create separate Master instances
from pyxcp import Master
from pyxcp.transport import Can

# Channel 1
master1 = Master(Can(interface='vector', channel=0))
master1.connect()

# Channel 2  
master2 = Master(Can(interface='vector', channel=1))
master2.connect()

# Use both masters independently
master1.shortUpload(...)
master2.shortUpload(...)
```

**Multi-channel wrapper coming in future release.**

**Related issues:** #227

---

### Q: How to use custom CAN driver?

**A:** The API changed in v0.22+. Migration guide:

**Old way (v0.21.x):**
```python
from pyxcp.transport.can import CanInterfaceBase

class MyDriver(CanInterfaceBase):
    pass
```

**New way (v0.22+):**
```python
import can

# Register your driver with python-can
from can.interfaces import VALID_INTERFACES
VALID_INTERFACES['mydriver'] = 'mymodule.MyDriver'

# Then use it normally
c.Transport.Can.interface = 'mydriver'
```

**See:** python-can documentation for custom driver implementation

**Related issues:** #223, #228

---

### Q: Latest pyxcp doesn't work with Vector CANape / XCPsim

**A:** Known compatibility issue. Workarounds:

1. **Use pyxcp v0.23.9** (last known working version)
2. **Check your Vector device serial** - May need explicit config:
   ```python
   c.Transport.Can.interface = 'vector'
   c.Transport.Can.serial = 12345  # Your device serial
   ```

**Fix in progress.**

**Related issues:** #224, #204

---

## Configuration

### Q: `AttributeError: 'dict' object has no attribute 'general'`

**A:** You're using old TOML config format with new pyxcp. Options:

1. **Migrate to Traitlets config** (recommended):
   ```python
   from pyxcp.config import get_config

   c = get_config()
   c.Transport.layer = 'CAN'
   c.Transport.Can.interface = 'vector'
   # etc.
   ```

2. **Use ArgumentParser** (simplest):
   ```python
   from pyxcp.cmdline import ArgumentParser

   ap = ArgumentParser(description="My Tool")
   with ap.run() as x:
       x.connect()
       # ...
   ```

3. **Keep TOML** (legacy, will show deprecation warning):
   Use pyxcp v0.23.9 or earlier

**Related issues:** #200, #201

---

### Q: `DaqToCsv` fails with `FileNotFoundError` in Robot Framework

**A:** Config discovery looks in wrong working directory. Fix:

```python
# Option 1: Use absolute paths
c.Recorder.output_file = '/absolute/path/to/output.csv'

# Option 2: Set working directory explicitly
import os
os.chdir('/path/to/your/config')

# Option 3: Specify config file explicitly
from pyxcp import ArgumentParser
ap = ArgumentParser(config='/absolute/path/to/config.py')
```

**Related issues:** #260

---

### Q: Dependency constraints are too strict

**A:** You can relax them by installing from source:

```bash
git clone https://github.com/christoph2/pyxcp.git
cd pyxcp
# Edit pyproject.toml to loosen constraints
pip install -e .
```

Or create a local fork with adjusted dependencies.

**A fix to loosen constraints is planned.**

**Related issues:** #211

---

## Error Handling & Timeouts

### Q: Error handler repeats errors forever / infinite retry

**A:** By default, pyxcp follows XCP standard (infinite retry). Configure timeouts:

```python
c.Master.timeout = 2.0  # Global timeout in seconds
c.Master.max_retries = 3  # Max retry attempts (default: infinite)
```

**Better retry configuration coming in future release.**

**Related issues:** #216, #107

---

### Q: `XcpTimeoutError: Response timed out [block_receive]`

**A:** Increase timeout or check connection:

```python
# Increase timeout
c.Transport.timeout = 5.0  # seconds

# For CAN:
c.Transport.Can.timeout = 2.0

# Debug with verbose logging
x = ap.run(loglevel='DEBUG')
```

Check:
- ECU is powered and responding
- CAN termination is correct
- Network cable connected (Ethernet)
- Correct CAN ID configuration

**Related issues:** #155

---

### Q: `Master.close()` takes too long

**A:** Configure disconnect timeout:

```python
c.Master.disconnect_timeout = 0.5  # seconds, default is 2.0
```

Or use context manager (automatically closes):
```python
with ap.run() as x:
    x.connect()
    # ... work ...
# Auto-disconnects here
```

**Related issues:** #209

---

## General Usage

### Q: How do I use this library? / Where do I start?

**A:** Quickstart guide:

**1. Install:**
```bash
pip install pyxcp
```

**2. Minimal example:**
```python
from pyxcp.cmdline import ArgumentParser

ap = ArgumentParser(description="My XCP Tool")

# Create/edit config file that ap generates, or configure programmatically
with ap.run() as x:
    x.connect()

    # Read slave info
    print(f"ID: {x.identifier(0x01)}")
    print(f"Properties: {x.slaveProperties}")

    # Read memory
    data = x.shortUpload(address=0x1000, length=4)
    print(f"Data: {data.hex()}")

    # Write memory
    x.shortDownload(address=0x1000, data=b'\x01\x02\x03\x04')

    x.disconnect()
```

**3. See examples:**
```bash
# List available examples
xcp-examples --list

# Run an example
xcp-examples run daq_simple
```

**4. Read the tutorial:**
- See `docs/tutorial.rst`
- Check `pyxcp/examples/` folder

**Related issues:** #129, #143, #184

---

### Q: How do I use pyxcp with an A2L file?

**A:** pyxcp works with the `pya2ldb` library:

```python
from pya2ldb import DB

# Load A2L
db = DB()
db.open("your_file.a2l")

# Get measurement info
measurement = db.query(db.Measurement).filter_by(name="MySignal").first()
address = measurement.address

# Use with pyxcp
with ap.run() as x:
    x.connect()
    data = x.shortUpload(address, measurement.size)
    x.disconnect()
```

**See:** [pya2ldb documentation](https://github.com/christoph2/pya2l)

**Related issues:** #179, #184

---

### Q: What XCP slave devices / ECUs work with pyxcp?

**A:** pyxcp implements XCP 1.0/1.1 standard and works with:

- **Commercial tools:** Vector CANape, ETAS INCA (as slave simulators)
- **Open source:** XCPlite (included in examples)
- **Real ECUs:** Most automotive ECUs with XCP support
- **DIY projects:** Arduino, Raspberry Pi with XCP slave implementation

**Note:** Some vendor-specific extensions may not be supported.

**Related issues:** #114

---

### Q: Can I use pyxcp for ECU flashing?

**A:** Yes! pyxcp supports the PROGRAM segment of XCP:

```python
with ap.run() as x:
    x.connect()

    # Enter programming mode
    x.programStart()

    # Clear memory
    x.programClear(mode=0, size=flash_size)

    # Program data
    for chunk in data_chunks:
        x.program(chunk)

    # Verify
    x.programVerify(...)

    # Reset
    x.programReset()

    x.disconnect()
```

**See:** `pyxcp/examples/flashing.py` for complete example

**Related issues:** #221

---

## Troubleshooting

### Q: My issue is not listed here

**A:** Check these resources:

1. **Documentation:** `docs/troubleshooting.rst` and `docs/troubleshooting_matrix.rst`
2. **Examples:** `pyxcp/examples/` folder
3. **GitHub Issues:** Search [existing issues](https://github.com/christoph2/pyxcp/issues)
4. **GitHub Discussions:** Ask in [Discussions](https://github.com/christoph2/pyxcp/discussions)

When reporting an issue, please include:
- pyxcp version: `python -c "import pyxcp; print(pyxcp.__version__)"`
- Python version: `python --version`
- Operating system
- Transport layer (CAN/ETH/USB/Serial)
- Minimal code to reproduce

---

### Q: How do I enable debug logging?

**A:** Use the `-l` flag or configure logging:

```python
# Command line
python your_script.py -l DEBUG

# Programmatically
import logging
logging.basicConfig(level=logging.DEBUG)

# Or with ArgumentParser
ap = ArgumentParser(loglevel='DEBUG')
```

**Related issues:** #176

---

### Q: Logging configuration interferes with my application

**A:** pyxcp now uses NullHandler by default. Configure manually:

```python
import logging

# Configure pyxcp logging
pyxcp_logger = logging.getLogger('pyxcp')
pyxcp_logger.setLevel(logging.INFO)
handler = logging.StreamHandler()
handler.setFormatter(logging.Formatter('%(levelname)s:%(name)s:%(message)s'))
pyxcp_logger.addHandler(handler)

# Your application logging is separate
app_logger = logging.getLogger('myapp')
# ... configure as needed
```

**Related issues:** #176

---

## Contributing

### Q: Can I contribute to pyxcp?

**A:** Yes! Contributions are welcome:

1. **Report bugs:** Use [issue templates](https://github.com/christoph2/pyxcp/issues/new/choose)
2. **Submit PRs:**
   - Fork the repo
   - Create feature branch
   - Run `pre-commit install`
   - Make changes
   - Run tests: `pytest`
   - Submit PR

3. **Improve docs:** Documentation PRs are especially welcome!

See `CODE_OF_CONDUCT.md` for community guidelines.

---

**Last updated:** 2026-02-14
**pyxcp version:** 0.26.2+

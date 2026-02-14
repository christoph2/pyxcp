# pyXCP Quickstart Guide

**Get started with pyXCP in 15 minutes** ⚡

This guide will take you from installation to your first XCP connection, parameter read/write, and basic DAQ recording.

---

## 📋 Prerequisites

- **Python 3.8+** (64-bit recommended)
- **XCP Slave Device:** ECU, simulator, or test tool (e.g., Vector CANape, XCPlite)
- **Transport Interface:** CAN adapter, Ethernet connection, USB device, or serial port
- **Optional:** A2L file for symbolic access (ASAM MCD-2 MC)

> **Safety Note:** XCP is for development and testing. Never use on safety-critical systems without proper safety analysis.

---

## 🚀 Installation

### Basic Installation

```bash
pip install pyxcp
```

Verify installation:

```bash
python -c "import pyxcp; print(pyxcp.__version__)"
# Should print: 0.26.5 (or higher)
```

### With Optional Dependencies

```bash
# For A2L file support
pip install pyxcp pya2ldb

# For specific CAN drivers
pip install pyxcp python-can[pcan]     # PEAK CAN
pip install pyxcp python-can[vector]   # Vector
pip install pyxcp python-can[ixxat]    # IXXAT
```

---

## 🎯 Your First XCP Connection

### 1. Minimal CAN Example

The simplest possible XCP connection via CAN:

```python
from pyxcp import Master

# Connect to ECU via CAN
with Master("can") as xcp:
    xcp.connect()

    # Read ECU identification
    ecu_id = xcp.getId(0x01)
    print(f"Connected to ECU: {ecu_id}")

    xcp.disconnect()
```

**Run with command-line config:**

```bash
python your_script.py --transport CAN --device socketcan --channel can0 --bitrate 500000
```

### 2. Ethernet Example (TCP)

For Ethernet-based XCP slaves:

```python
from pyxcp import Master

# Connect via Ethernet
with Master("eth") as xcp:
    xcp.connect()

    # Read slave properties
    props = xcp.slaveProperties
    print(f"Protocol Layer: {props.protocolLayerVersion}")
    print(f"Max CTO: {props.maxCto} bytes")
    print(f"Max DTO: {props.maxDto} bytes")

    xcp.disconnect()
```

**Run with:**

```bash
python your_script.py --transport ETH --host 192.168.1.100 --port 5555 --protocol TCP
```

### 3. No Config File Required (v0.26.5+)

Use programmatic configuration:

```python
from pyxcp import Master
from pyxcp.config import create_application_from_config, set_application

# Define configuration
config = {
    "Transport": {
        "CAN": {
            "device": "socketcan",
            "channel": "can0",
            "bitrate": 500000,
            "max_dlc": 8
        }
    }
}

# Create application
app = create_application_from_config(config)
set_application(app)

# Now use Master as usual
with Master("can") as xcp:
    xcp.connect()
    print(f"ECU ID: {xcp.getId(0x01)}")
    xcp.disconnect()
```

---

## 📖 Reading and Writing Parameters

### Upload (Read from ECU)

```python
from pyxcp import Master

with Master("can") as xcp:
    xcp.connect()

    # Read 4 bytes from address 0x1A2000
    data = xcp.upload(address=0x1A2000, length=4)
    print(f"Raw data: {data.hex()}")

    # Convert to integer (little-endian)
    import struct
    value = struct.unpack("<I", data)[0]
    print(f"Value: {value}")

    xcp.disconnect()
```

### Download (Write to ECU)

```python
from pyxcp import Master
import struct

with Master("can") as xcp:
    xcp.connect()

    # Unlock calibration (if protected)
    if not xcp.getCurrentProtectionStatus()["cal_pag"]:
        seed = xcp.getSeed(0x01)  # Get seed
        key = b"MySecretKey123"    # Your key
        xcp.unlock(key)

    # Write integer value to address
    new_value = 42
    data = struct.pack("<I", new_value)
    xcp.download(address=0x1A2000, data=data)

    # Verify write
    readback = xcp.upload(address=0x1A2000, length=4)
    print(f"Written: {new_value}, Read back: {struct.unpack('<I', readback)[0]}")

    xcp.disconnect()
```

---

## 📊 Basic DAQ Recording

### Simple DAQ Example

Record measurements from ECU to CSV:

```python
from pyxcp import Master
from pyxcp.daq_stim import DaqList, DaqToCsv
import time

with Master("can") as xcp:
    xcp.connect()

    # Configure DAQ list
    daq_list = DaqList(
        name="Engine",
        event=0,  # Event channel (from getDaqEventInfo)
        measurements=[
            {"address": 0x1A2000, "ext": 0, "size": 4},  # Engine speed
            {"address": 0x1A2004, "ext": 0, "size": 4},  # Engine temp
            {"address": 0x1A2008, "ext": 0, "size": 2},  # Throttle pos
        ]
    )

    # Create recording policy (saves to CSV)
    policy = DaqToCsv([daq_list])

    # Setup and start DAQ
    xcp.setupDaq([daq_list], policy)
    xcp.startDaq()

    # Record for 10 seconds
    print("Recording for 10 seconds...")
    time.sleep(10)

    # Stop DAQ
    xcp.stopDaq()
    xcp.disconnect()

print("Recording complete! Check output CSV file.")
```

**Output:** Creates timestamped CSV file with your measurements.

### DAQ with Data Conversion

Convert raw bytes to engineering values:

```python
from pyxcp.daq_stim import DaqList, DaqToCsv
import struct

def convert_engine_speed(raw_bytes):
    """Convert 4 bytes to RPM."""
    raw = struct.unpack("<I", raw_bytes)[0]
    return raw * 0.25  # Scaling factor

def convert_temperature(raw_bytes):
    """Convert 4 bytes to Celsius."""
    raw = struct.unpack("<I", raw_bytes)[0]
    return (raw * 0.1) - 40.0  # Offset and scaling

# Add conversion functions to measurements
measurements = [
    {
        "address": 0x1A2000,
        "ext": 0,
        "size": 4,
        "name": "EngineSpeed_RPM",
        "conversion": convert_engine_speed
    },
    {
        "address": 0x1A2004,
        "ext": 0,
        "size": 4,
        "name": "EngineTemp_C",
        "conversion": convert_temperature
    }
]

# Use in DaqList as before...
```

---

## 🔧 Configuration Options

### Method 1: Command-Line Arguments (Recommended)

Use `ArgumentParser` for flexible CLI configuration:

```python
from pyxcp.cmdline import ArgumentParser

ap = ArgumentParser(description="My XCP Tool")

with ap.run() as xcp:
    xcp.connect()
    # ... your code
    xcp.disconnect()
```

Run with:

```bash
# CAN
python tool.py --transport CAN --device socketcan --channel can0 --bitrate 500000

# Ethernet
python tool.py --transport ETH --host 192.168.1.100 --port 5555 --protocol TCP

# USB
python tool.py --transport USB --vendor-id 0x1234 --product-id 0x5678
```

### Method 2: Config File

Create `pyxcp_conf.py` in your script directory:

```python
c = get_config()

# Transport configuration
c.Transport.CAN.device = "socketcan"
c.Transport.CAN.channel = "can0"
c.Transport.CAN.bitrate = 500000
c.Transport.CAN.max_dlc = 8

# Ethernet alternative
# c.Transport.Eth.host = "192.168.1.100"
# c.Transport.Eth.port = 5555
# c.Transport.Eth.protocol = "TCP"

# General settings
c.General.loglevel = "INFO"
```

Config file search order:
1. `PYXCP_CONFIG` environment variable
2. Current working directory
3. Script directory
4. User home `~/.pyxcp/pyxcp_conf.py`

### Method 3: Programmatic (Library Usage)

Best for embedding pyXCP in your application:

```python
from pyxcp.config import create_application_from_config, set_application

config = {
    "Transport": {
        "CAN": {
            "device": "socketcan",
            "channel": "can0",
            "bitrate": 500000
        }
    }
}

app = create_application_from_config(config)
set_application(app)
```

---

## 🎓 Next Steps

### Learn More

- **[Full Tutorial](tutorial.rst)** - Comprehensive guide with advanced topics
- **[FAQ](FAQ.md)** - Common questions and solutions
- **[Examples](../pyxcp/examples/)** - Complete working examples
- **[API Reference](pyxcp.rst)** - Detailed API documentation

### Explore Examples

```bash
cd pyxcp/examples/

# Basic connection and info
python xcphello.py --transport CAN --device socketcan --channel can0

# DAQ recording
python run_daq.py --transport CAN --device socketcan --channel can0

# Multi-channel CAN
python multi_channel_can.py
```

### Common Patterns

**Read calibration parameter by name (with A2L):**

```python
from pya2ldb import DB

db = DB()
db.import_a2l("my_ecu.a2l")

# Find parameter by name
param = db.query("EngineSpeedLimit")
address = param.address
size = param.size

# Read from ECU
data = xcp.upload(address=address, length=size)
```

**Error handling:**

```python
from pyxcp.master import Master
from pyxcp.types import XcpTimeoutError, XcpResponseError

with Master("can") as xcp:
    try:
        xcp.connect()
        xcp.upload(address=0x1A2000, length=4)
    except XcpTimeoutError:
        print("Timeout - ECU not responding")
    except XcpResponseError as e:
        print(f"XCP Error: {e.error_code} - {e.error_text}")
    finally:
        xcp.disconnect()
```

---

## 🐛 Troubleshooting

### CAN Connection Issues

**"Device not found"**
```bash
# Linux: Check interface exists
ip link show can0

# Create virtual CAN for testing
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0
```

**"Permission denied"**
```bash
# Add user to dialout group (Linux)
sudo usermod -a -G dialout $USER
# Log out and back in
```

### Ethernet Connection Issues

**"Connection refused"**
- Verify ECU IP: `ping 192.168.1.100`
- Check XCP port (usually 5555)
- Verify firewall rules

**"Timeout"**
- Increase timeout: `xcp.config.timeout = 5.0  # seconds`
- Check ECU is powered and XCP enabled

### Common XCP Errors

| Error Code | Meaning | Solution |
|------------|---------|----------|
| `0x10` | CMD_UNKNOWN | ECU doesn't support this command |
| `0x20` | CMD_BUSY | Wait and retry |
| `0x22` | OUT_OF_RANGE | Invalid address or length |
| `0x25` | ACCESS_LOCKED | Unlock calibration first |
| `0x30` | PGM_ACTIVE | Stop programming session |

See [FAQ](FAQ.md#troubleshooting) for more solutions.

---

## 💡 Quick Reference

### Essential Commands

```python
# Connection
xcp.connect()
xcp.disconnect()

# Info
xcp.getId(0x01)              # ECU identification
xcp.slaveProperties          # Protocol info
xcp.getDaqInfo()            # DAQ capabilities

# Memory Access
xcp.upload(addr, length)     # Read
xcp.download(addr, data)     # Write

# Calibration Protection
xcp.getSeed(mode)           # Get seed
xcp.unlock(key)             # Unlock with key
xcp.getCurrentProtectionStatus()  # Check status

# DAQ
xcp.setupDaq(lists, policy) # Configure
xcp.startDaq()              # Start
xcp.stopDaq()               # Stop
```

### Transport Parameters

**CAN:**
- `--device`: socketcan, vector, pcan, ixxat
- `--channel`: Interface name (e.g., can0, vcan0)
- `--bitrate`: 125000, 250000, 500000, 1000000

**Ethernet:**
- `--host`: IP address (e.g., 192.168.1.100)
- `--port`: TCP/UDP port (default: 5555)
- `--protocol`: TCP or UDP

**USB:**
- `--vendor-id`: USB vendor ID (hex)
- `--product-id`: USB product ID (hex)

---

## 🎉 You're Ready!

You now know how to:
- ✅ Install and verify pyXCP
- ✅ Connect to an XCP slave via CAN or Ethernet
- ✅ Read and write ECU parameters
- ✅ Record DAQ measurements to CSV
- ✅ Configure pyXCP for your needs

**Next:** Check out [complete examples](../pyxcp/examples/) or dive into the [full tutorial](tutorial.rst).

**Questions?** See [FAQ](FAQ.md) or [open an issue](https://github.com/christoph2/pyxcp/issues).

---

**Happy Calibrating!** 🚗💨

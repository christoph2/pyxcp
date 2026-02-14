# Command-Line Tools Reference

pyXCP provides seven command-line tools for XCP device interaction, configuration management, and data conversion. All tools support the new Python-based configuration system introduced in v0.26.4+.

## Quick Reference

| Tool | Purpose | Common Use Case |
|------|---------|----------------|
| `xcp-info` | Inspect ECU capabilities | "What does this ECU support?" |
| `xcp-id-scanner` | Scan CAN bus for ECUs | "What's the XCP ID?" |
| `xcp-fetch-a2l` | Download A2L from ECU | "I need the A2L file" |
| `xcp-profile` | Manage configuration files | "Create/convert configs" |
| `xcp-examples` | Copy example scripts | "Show me code examples" |
| `xmraw-converter` | Convert measurement data | "Export DAQ data to CSV" |
| `pyxcp-probe-can-drivers` | List CAN drivers | "What CAN drivers are available?" |

**Note:** There's also `xcp-daq-recorder` (not in pyproject.toml scripts) for automated DAQ recording from JSON config.

---

## Configuration Methods

All XCP tools (except `xcp-examples` and `pyxcp-probe-can-drivers`) support three configuration methods:

### Method 1: Python Config File (Recommended)
```bash
xcp-info -t eth --config my_config.py
```

**Create a config file:**
```bash
xcp-profile create -o my_config.py
```

**Config file structure** (example for Ethernet):
```python
# my_config.py
def create_transport(parent):
    from pyxcp.transport.eth import Eth
    return Eth(parent, host="192.168.1.100", port=5555, protocol="TCP")
```

### Method 2: Command-Line Arguments
```bash
xcp-info -t eth --host 192.168.1.100 --port 5555
xcp-info -t can --can-interface socketcan --can-channel can0
```

### Method 3: Legacy TOML (Deprecated, still supported)
```bash
xcp-info -t eth --config legacy_config.toml
```

**Convert legacy to Python:**
```bash
xcp-profile convert -o new_config.py old_config.toml
```

---

## Tool Details

### 1. xcp-info
**Inspect XCP slave capabilities and configuration**

#### Usage
```bash
xcp-info [OPTIONS]
```

#### Purpose
Queries an XCP slave for its supported features: DAQ configuration, paging (calibration), programming capabilities, and implemented IDs. This is your "first contact" tool when working with a new ECU.

#### Options
- `--no-daq` - Skip DAQ information (faster, useful if DAQ queries hang)
- `--no-pag` - Skip paging/calibration information
- `--no-pgm` - Skip programming/flashing information
- `--no-ids` - Skip ID scanning (FILE_NAME, FILE_TO_UPLOAD, etc.)

#### Examples

**Full inspection (Ethernet):**
```bash
xcp-info -t eth --host 192.168.1.100 --port 5555
```

**Quick check (skip DAQ and PAG):**
```bash
xcp-info -t can --config can_config.py --no-daq --no-pag
```

**With config file:**
```bash
xcp-info -t eth --config my_ecu.py
```

#### Output Sections
1. **Slave Properties** - Protocol version, byte order, max packet sizes
2. **Implemented IDs** - Available ID types (A2L filename, file upload, etc.)
3. **Protection Status** - Which resources are protected (CAL/DAQ/STIM/PGM)
4. **DAQ Info** - Number of DAQ lists, ODTs, event channels, predefined lists
5. **PAG Info** - Calibration segments, pages per segment
6. **PGM Info** - Programming properties, sector info

#### Troubleshooting
**Symptom:** Tool hangs during DAQ query  
**Solution:** Use `--no-daq` flag. Some ECUs respond slowly to `GET_DAQ_PROCESSOR_INFO`.

**Symptom:** "Protection status error"  
**Solution:** Use seed/key file (see FAQ.md). Add to config file or use `--seed-key-dll`.

**Symptom:** "Connection timeout"  
**Solution:**
- Ethernet: Check firewall, verify ECU IP with `ping`
- CAN: Verify bus speed, check termination, run `pyxcp-probe-can-drivers`

---

### 2. xcp-id-scanner
**Scan CAN bus to find XCP slaves**

#### Usage
```bash
xcp-id-scanner [OPTIONS]
```

#### Purpose
Broadcasts XCP CONNECT commands on a CAN bus to discover active XCP slaves. Returns the XCP ID (CAN identifier) for each responding slave. Essential for finding unknown ECUs on a CAN network.

#### How It Works
1. Iterates through common XCP CAN IDs (typically 0x700-0x7FF range)
2. Sends CONNECT command to each ID
3. Waits for response (RES/ERR packet)
4. Reports responding IDs with slave properties

#### Examples

**Scan with config file:**
```bash
xcp-id-scanner -t can --config can_config.py
```

**Scan with command-line config:**
```bash
xcp-id-scanner -t can --can-interface socketcan --can-channel can0 --can-bitrate 500000
```

**Typical output:**
```
Scanning for XCP slaves...
Found slave at ID 0x700:
  Protocol Version: 1.0
  Max DTO: 8
  Max CTO: 8
  Resource: CAL/DAQ supported
```

#### Tips
- **Scanning takes time** - Expect 10-30 seconds for full scan
- **Bus load** - Generates broadcast traffic; don't run on production CAN bus
- **Limited to CAN** - Only works with CAN transport (not Ethernet/USB)
- **Use result in config** - Found ID goes into your config file's `can_id_master` parameter

---

### 3. xcp-fetch-a2l
**Download A2L file from XCP slave**

#### Usage
```bash
xcp-fetch-a2l [OPTIONS]
```

#### Purpose
Fetches the A2L (ASAP2) file directly from an XCP slave if it supports the `UPLOAD` command and `FILE_TO_UPLOAD` identifier. This is the modern way to get A2L files without manual OEM distribution.

#### Requirements
- Slave must implement `XcpGetIdType.FILE_TO_UPLOAD` (ID type 1)
- Slave must support `UPLOAD` command
- Check availability with: `xcp-info --no-daq --no-pag --no-pgm`

#### Examples

**Fetch from Ethernet ECU:**
```bash
xcp-fetch-a2l -t eth --host 192.168.1.100 --port 5555
```

**Fetch with config file:**
```bash
xcp-fetch-a2l -t can --config my_ecu.py
```

**Specify output filename:**
```bash
xcp-fetch-a2l -t eth --config ecu.py
# Tool uses filename from slave, or prompts if exists
```

#### Output
- Saves to filename reported by slave (from `XcpGetIdType.FILENAME`)
- If no filename available, defaults to `output.a2l`
- Prompts before overwriting existing files

#### Troubleshooting
**Symptom:** "Empty response from ID 'FILE_TO_UPLOAD'"  
**Solution:** ECU doesn't support A2L upload. Request A2L from OEM or development team.

**Symptom:** "Protection status error"  
**Solution:** A2L upload may be protected. Unlock with seed/key (configure in config file).

**Symptom:** Downloaded A2L is corrupted/incomplete  
**Solution:**
- Check `MAX_BS` (block size) in ECU configuration - may be too small
- Try with different transport (Ethernet often more reliable than CAN)
- Verify ECU firmware - some versions have broken UPLOAD implementation

---

### 4. xcp-profile
**Create and convert configuration files**

#### Usage
```bash
xcp-profile <create|convert> [OPTIONS]
```

#### Purpose
Manages pyXCP configuration files. Use `create` to generate a template with all available options, or `convert` to migrate legacy JSON/TOML configs to the new Python format.

#### Subcommands

##### create
Generate a new Python configuration file with all options documented.

```bash
# Save to file
xcp-profile create -o my_config.py

# Preview in terminal
xcp-profile create

# Pipe to less for browsing
xcp-profile create | less
```

**Generated config includes:**
- All transport options (CAN, Ethernet, USB, Serial)
- DAQ configuration
- Timing parameters
- Commented examples for each transport type

##### convert
Convert legacy JSON/TOML configuration to Python format.

```bash
# Convert single file
xcp-profile convert -o new_config.py old_config.toml

# Convert with custom transport
xcp-profile convert -t eth -o eth_config.py legacy.json
```

#### Examples

**Workflow for new project:**
```bash
# 1. Create template
xcp-profile create -o base_config.py

# 2. Edit base_config.py (uncomment your transport, set parameters)
nano base_config.py

# 3. Test configuration
xcp-info -t eth --config base_config.py
```

**Migrate from legacy:**
```bash
# Old way (TOML, pre-v0.26.4)
xcp-info -t eth --config config.toml

# Convert to Python
xcp-profile convert -o config.py config.toml

# New way (Python, v0.26.4+)
xcp-info -t eth --config config.py
```

#### Configuration Discovery Order
pyXCP searches for config files in this order:
1. `PYXCP_CONFIG` environment variable
2. `--config` command-line argument
3. `pyxcp_conf.py` in current working directory
4. `pyxcp_conf.py` in script directory
5. `~/.pyxcp/pyxcp_conf.py`

#### Tips
- **Use Python configs** - More flexible, better IDE support, easier debugging
- **Version control** - Python configs work better with git (no TOML formatting issues)
- **Multiple profiles** - Create separate configs for each ECU: `ecu1.py`, `ecu2.py`
- **Environment variable** - Set `PYXCP_CONFIG=/path/to/config.py` for project-wide default

---

### 5. xcp-examples
**Copy example scripts to your project**

#### Usage
```bash
xcp-examples OUTPUT_DIRECTORY [-f]
```

#### Purpose
Copies all pyXCP example scripts from the package installation to a local directory. These examples demonstrate common XCP workflows and serve as templates for your own scripts.

#### Options
- `OUTPUT_DIRECTORY` - Where to copy examples (required)
- `-f, --force` - Overwrite existing files without prompting

#### Examples

**Copy to current directory:**
```bash
xcp-examples .
```

**Copy to examples folder:**
```bash
mkdir my_xcp_examples
xcp-examples my_xcp_examples
```

**Force overwrite:**
```bash
xcp-examples ./examples -f
```

#### Available Examples (v0.26.5+)
After running `xcp-examples`, you'll have:

- `basic_can_connection.py` - Hello world: connect, read info, disconnect
- `calibration_workflow.py` - Complete calibration with seed/key unlock
- `daq_recording.py` - Set up DAQ lists and record to CSV
- `ethernet_connection.py` - TCP/UDP examples with error recovery
- `a2l_integration.py` - Symbolic access with pya2ldb
- `multi_ecu_setup.py` - Parallel DAQ from multiple ECUs

Each example is self-contained with:
- Configuration section at top
- Full error handling
- Detailed comments explaining each step
- Production-ready patterns

#### Tips
- **Start with basic_can_connection.py** - Simplest example, good for testing setup
- **Check config sections** - Edit constants at top of each file before running
- **Run from copied location** - Examples need write access for CSV/log output
- **Combine patterns** - Copy-paste snippets from multiple examples into your script

---

### 6. xmraw-converter
**Convert XMRAW measurement files to other formats**

#### Usage
```bash
xmraw-converter INPUT_FILE -o FORMAT [OPTIONS]
```

#### Purpose
Converts pyXCP's native XMRAW measurement format (created by `DaqRecorder`) to CSV or other formats for analysis in Excel, MATLAB, Python pandas, etc.

#### Arguments
- `INPUT_FILE` - Path to `.xmraw` file (required)
- `-o, --output FORMAT` - Output format: `csv` or `mat` (required)

#### Examples

**Convert to CSV:**
```bash
xmraw-converter measurement_20240214_153000.xmraw -o csv
```

**Output:** Creates `measurement_20240214_153000.csv` in same directory

**Convert multiple files:**
```bash
for file in *.xmraw; do
    xmraw-converter "$file" -o csv
done
```

#### XMRAW Format
XMRAW is pyXCP's binary recording format with:
- **Compression** - LZ4 compression for efficient storage
- **Timestamps** - High-precision timestamps per sample
- **Metadata** - DAQ list configuration embedded in file
- **Performance** - Fast writing during real-time DAQ (simdjson parsing)

**Create XMRAW files:**
```python
from pyxcp.daq_stim import DaqRecorder

recorder = DaqRecorder(daq_lists, "my_recording", 8)
recorder.start(master)
# ... DAQ runs ...
recorder.stop()
# Creates my_recording.xmraw
```

#### CSV Output Format
CSV output includes:
- **First row:** Column headers (variable names)
- **Subsequent rows:** Timestamp + values
- **Separator:** Comma (`,`)
- **Encoding:** UTF-8

**Example CSV:**
```csv
timestamp,engine_speed,throttle_position,coolant_temp
0.000123,850.5,12.3,85.2
0.010145,851.2,12.5,85.3
...
```

#### Tips
- **Large files** - XMRAW converter handles multi-GB files efficiently
- **Pandas integration** - Load CSV with: `df = pd.read_csv("measurement.csv")`
- **MATLAB** - MAT format support for direct MATLAB import (if available)
- **Keep XMRAW files** - Archive original XMRAW; it's more compact than CSV

---

### 7. pyxcp-probe-can-drivers
**List available CAN drivers on your system**

#### Usage
```bash
pyxcp-probe-can-drivers
```

#### Purpose
Scans your system for available python-can backend drivers and reports which are usable. Essential for troubleshooting "No backend available" errors.

#### No Arguments
This tool takes no arguments - just run it.

#### Example Output
```
Available CAN drivers:
======================

✓ socketcan (Linux)
  Status: Available
  Channels: can0, can1

✓ vector (Vector CANcaseXL)
  Status: Available  
  DLL found: C:\Program Files\Vector\...

✗ pcan (PEAK-System PCAN)
  Status: NOT AVAILABLE
  Reason: PCAN driver not installed

✓ virtual (Virtual CAN)
  Status: Available
  Note: For testing without hardware
```

#### Supported Drivers
python-can supports many backends. Common ones:

**Linux:**
- `socketcan` - Native Linux CAN support (recommended)
- `virtual` - Virtual CAN for testing

**Windows:**
- `vector` - Vector CANcaseXL, CANcardXL, etc.
- `pcan` - PEAK-System PCAN USB, PCI
- `ixxat` - HMS/Ixxat CAN interfaces
- `kvaser` - Kvaser CAN interfaces
- `virtual` - Virtual CAN for testing

**Cross-platform:**
- `usb2can` - Geschwister Schneider USB-to-CAN

#### Troubleshooting

**No drivers available:**
1. **Install driver software** from hardware vendor
2. **Install python-can extras:** `pip install python-can[vector,pcan,kvaser]`
3. **Check DLL paths** - Windows drivers need DLLs in PATH or system32

**Driver listed but connection fails:**
- **Linux socketcan:** Run `ip link set can0 up type can bitrate 500000`
- **Vector:** Start CANoe/CANalyzer once to register driver
- **PCAN:** Run PCAN-View to verify hardware detection

**Virtual driver for testing:**
```python
# Use virtual CAN if no hardware available
# Config file:
def create_transport(parent):
    from pyxcp.transport.can import Can
    return Can(parent, can_interface="virtual", can_channel="test_channel")
```

---

## 8. xcp-daq-recorder (Bonus Tool)
**Automated DAQ recording from JSON configuration**

**Note:** This tool exists in `pyxcp/scripts/xcp_daq_recorder.py` but is not listed in `[tool.poetry.scripts]` of pyproject.toml, so it's not installed as a command-line entry point by default.

#### Usage (if manually added to PATH)
```bash
xcp-daq-recorder DAQ_CONFIG.json [XCP_OPTIONS]
```

#### Purpose
Automates DAQ list recording based on a JSON configuration file. Useful for automated testing, CI/CD, or repeated measurements with the same DAQ setup.

#### JSON Configuration Format
```json
{
  "runtime_seconds": 60,
  "output_file": "my_recording",
  "output_type": "xmraw",
  "daq_lists": [
    {
      "name": "Powertrain",
      "event": 0,
      "mode": "DAQ",
      "elements": [
        {"address": 0x400000, "ext": 0, "size": 4},
        {"address": 0x400010, "ext": 0, "size": 2}
      ]
    }
  ]
}
```

#### Parameters
- `runtime_seconds` - How long to record (default: 60)
- `output_file` - Base filename (no extension)
- `output_type` - `"xmraw"` or `"csv"`
- `daq_lists` - Array of DAQ list configurations

---

## Common Workflows

### Workflow 1: First Contact with Unknown ECU
```bash
# 1. Check if ECU is reachable
ping 192.168.1.100

# 2. Probe system for CAN drivers (if using CAN)
pyxcp-probe-can-drivers

# 3. Create config file
xcp-profile create -o my_ecu.py
# Edit my_ecu.py: set transport, host/port or CAN interface

# 4. Test connection and get capabilities
xcp-info -t eth --config my_ecu.py

# 5. Try to download A2L
xcp-fetch-a2l -t eth --config my_ecu.py

# 6. If A2L fetch fails, check which IDs are available
xcp-info -t eth --config my_ecu.py --no-daq --no-pag
```

### Workflow 2: Setup DAQ Recording
```bash
# 1. Copy examples for reference
xcp-examples ./my_project

# 2. Customize daq_recording.py with your variables
nano my_project/daq_recording.py

# 3. Run recording (creates .xmraw file)
python my_project/daq_recording.py

# 4. Convert to CSV for analysis
xmraw-converter run_daq_*.xmraw -o csv

# 5. Analyze in pandas/Excel
python -c "import pandas as pd; df = pd.read_csv('run_daq_*.csv'); print(df.describe())"
```

### Workflow 3: Multi-ECU Setup
```bash
# 1. Scan CAN bus for all ECUs
xcp-id-scanner -t can --config can_bus.py

# 2. Create config for each ECU
xcp-profile create -o ecu1.py
xcp-profile create -o ecu2.py
# Edit each: set unique can_id_master

# 3. Test each ECU individually
xcp-info -t can --config ecu1.py --no-daq --no-pag
xcp-info -t can --config ecu2.py --no-daq --no-pag

# 4. Use multi_ecu_setup.py example for parallel DAQ
xcp-examples .
python multi_ecu_setup.py
```

---

## Transport-Specific Tips

### Ethernet (TCP/UDP)
**Recommended for:** High-bandwidth DAQ, XCP-on-Ethernet ECUs  
**Typical config:**
```python
def create_transport(parent):
    from pyxcp.transport.eth import Eth
    return Eth(parent, host="192.168.1.100", port=5555, protocol="TCP")
```

**Tips:**
- **TCP vs UDP:** TCP = reliable, ordered; UDP = lower latency, no retries
- **Test connectivity first:** `ping <host>` before running XCP tools
- **Firewall:** Add exception for XCP port (common: 5555, 5556)
- **IPv6 support:** Use `host="fe80::1"` for link-local addresses

### CAN
**Recommended for:** Automotive ECUs, in-vehicle networks  
**Typical config:**
```python
def create_transport(parent):
    from pyxcp.transport.can import Can
    return Can(parent, can_interface="socketcan", can_channel="can0",
               can_id_master=0x700, can_id_slave=0x701)
```

**Tips:**
- **Run probe first:** `pyxcp-probe-can-drivers` to check available drivers
- **Bus setup (Linux):** `sudo ip link set can0 up type can bitrate 500000`
- **CAN-FD:** Set `can_fd=True` and `can_data_bitrate` in config
- **Unknown ID:** Use `xcp-id-scanner` to find correct `can_id_master`

### USB
**Recommended for:** Development boards with USB-XCP  
**Typical config:**
```python
def create_transport(parent):
    from pyxcp.transport.usb_transport import Usb
    return Usb(parent, vendor_id=0x1234, product_id=0x5678)
```

**Tips:**
- **Find IDs:** `lsusb` on Linux, Device Manager on Windows
- **Permissions (Linux):** Add udev rule for non-root access
- **Driver:** Install libusb: `pip install pyusb`, plus system libusb driver

### Serial (SxI)
**Recommended for:** Bootloaders, minimal XCP implementations  
**Typical config:**
```python
def create_transport(parent):
    from pyxcp.transport.sxi import SxI
    return SxI(parent, port="COM3", baudrate=115200)
```

**Tips:**
- **Port names:** `/dev/ttyUSB0` on Linux, `COM3` on Windows
- **Baudrate:** Match ECU setting (common: 115200, 230400)
- **Flow control:** Usually off for XCP, but check ECU requirements

---

## Troubleshooting Guide

### Error: "No backend available"
**Tools:** xcp-id-scanner, xcp-info (CAN transport)

**Cause:** python-can driver not installed or configured

**Solution:**
1. Run `pyxcp-probe-can-drivers` to see available drivers
2. Install missing driver extras: `pip install python-can[vector,pcan]`
3. Verify driver DLL/library installation
4. Check system CAN interface: `ip link show` (Linux)

---

### Error: "Connection timeout"
**Tools:** All XCP tools except xcp-examples

**Cause:** Cannot reach ECU

**Solution:**
- **Ethernet:** `ping <ecu_ip>` to verify network connectivity
- **CAN:** Check bus termination (120Ω), verify bitrate matches ECU
- **USB:** Verify cable connection, check device enumeration
- **All:** Verify ECU is powered and running XCP stack

---

### Error: "Protection status error"
**Tools:** xcp-info, xcp-fetch-a2l

**Cause:** Resource (CAL/DAQ/STIM/PGM) is protected by seed/key

**Solution:**
1. Check protection status: `xcp-info --no-daq --no-pag`
2. Add seed/key DLL to config:
   ```python
   def create_transport(parent):
       # ... transport config ...

   SEED_KEY_DLL = "path/to/SeedNKeyXcp.dll"
   ```
3. See FAQ.md section "Seed/Key Protection" for detailed setup

---

### Error: Tool hangs during execution
**Tools:** xcp-info (with --no-daq/--no-pag flags)

**Cause:** ECU doesn't respond to certain optional commands

**Solution:**
- Use `xcp-info --no-daq --no-pag --no-pgm` to skip problematic queries
- Some ECUs have slow/broken GET_DAQ_PROCESSOR_INFO - this is normal
- Add timeout increase to config: `transport.timeout = 5.0`

---

### CSV/XMRAW files are huge
**Tools:** xmraw-converter

**Cause:** High sample rate or many variables

**Solution:**
- **XMRAW:** Already compressed (LZ4) - this is expected size
- **CSV:** Use `xmraw-converter` only for analysis subsets
- **Reduce data:** Lower DAQ event rate, record fewer variables
- **Post-process:** Use pandas to downsample: `df = df[::10]` (every 10th sample)

---

## Environment Variables

Tools respect these environment variables:

- `PYXCP_CONFIG` - Default config file path (overrides CWD search)
- `PYXCP_LOGLEVEL` - Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`
- `PYXCP_SEED_KEY_DLL` - Default seed/key DLL path (if not in config)

**Example usage:**
```bash
export PYXCP_CONFIG=/opt/xcp_configs/production.py
export PYXCP_LOGLEVEL=DEBUG
xcp-info -t eth  # Uses production.py config, debug logging
```

---

## Additional Resources

- **Quickstart Guide:** `docs/quickstart.md` - Zero to DAQ in 15 minutes
- **Example Scripts:** Run `xcp-examples .` for code templates
- **FAQ:** `docs/FAQ.md` - Common questions and solutions
- **GitHub Issues:** https://github.com/christoph2/pyxcp/issues - Report bugs

---

## Summary

The pyXCP command-line tools provide a complete workflow from ECU discovery to measurement data export:

1. **Discovery:** `pyxcp-probe-can-drivers` → `xcp-id-scanner` → `xcp-info`
2. **Configuration:** `xcp-profile create` → edit config → test with `xcp-info`
3. **Development:** `xcp-examples` → customize → run scripts
4. **Data acquisition:** Python scripts with `DaqRecorder` → `xmraw-converter`

**Next steps:**
- Read `docs/quickstart.md` for hands-on tutorial
- Run `xcp-examples ./my_project` to get started with code
- Check `docs/FAQ.md` if you encounter issues

Happy XCP hacking! 🚀

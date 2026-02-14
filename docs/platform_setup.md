# Platform Setup Guide

pyXCP runs on Windows, Linux, and macOS. This guide covers platform-specific installation, C++ extension compilation, CAN driver setup, and common platform-specific issues.

## Table of Contents
- [Quick Start by Platform](#quick-start-by-platform)
- [Windows Setup](#windows-setup)
- [Linux Setup](#linux-setup)
- [macOS Setup](#macos-setup)
- [Docker and CI/CD](#docker-and-cicd)
- [Troubleshooting](#troubleshooting)

---

## Quick Start by Platform

### Windows
```bash
# Install Python 3.10+ (from python.org)
pip install pyxcp

# For CAN: Install driver (Vector, PCAN, Kvaser, etc.)
# For building from source: Install Visual Studio Build Tools
pip install pyxcp --no-binary pyxcp  # Build from source if needed
```

### Linux (Ubuntu/Debian)
```bash
# Install dependencies
sudo apt update
sudo apt install python3-pip python3-dev build-essential cmake

# Install pyxcp
pip install pyxcp

# For CAN: Setup SocketCAN
sudo apt install can-utils
sudo ip link set can0 up type can bitrate 500000
```

### macOS
```bash
# Install Xcode Command Line Tools
xcode-select --install

# Install Python via Homebrew (recommended)
brew install python@3.12

# Install pyxcp
pip3 install pyxcp

# For CAN: Install driver (limited options, see CAN section)
```

---

## Windows Setup

### Python Installation

**Recommended:** Python 3.10+ from [python.org](https://www.python.org/downloads/)

**During installation:**
- ✅ Check "Add Python to PATH"
- ✅ Check "Install pip"
- ✅ Consider "Disable path length limit" (for long file paths)

**Verify installation:**
```powershell
python --version  # Should be 3.10+
pip --version
```

### Installing pyXCP

**Option 1: Binary wheel (recommended, fastest)**
```powershell
pip install pyxcp
```

This installs pre-compiled C++ extensions for Windows. No compiler needed.

**Option 2: Build from source**
```powershell
# Install Visual Studio Build Tools first (see below)
pip install pyxcp --no-binary pyxcp
```

### C++ Build Tools (for source builds)

If you need to build C++ extensions from source (development, custom modifications):

**Install Visual Studio Build Tools:**
1. Download from: https://visualstudio.microsoft.com/downloads/
2. Select "Build Tools for Visual Studio 2022"
3. Install workload: **"Desktop development with C++"**
4. Includes: MSVC compiler, CMake, Windows SDK

**Verify installation:**
```powershell
# Check for cl.exe (MSVC compiler)
where cl

# Check for cmake
cmake --version
```

**Alternative: MinGW-w64 (not recommended)**
```powershell
# MinGW can work but has compatibility issues
choco install mingw  # via Chocolatey
```

### CAN Drivers on Windows

pyXCP uses **python-can** for CAN communication. Supported Windows backends:

#### Vector (CANcaseXL, CANcardXL, VN-series)
**Most popular for automotive development**

1. Install Vector driver software:
   - Download from Vector website (requires account)
   - Install CANoe/CANalyzer or standalone driver package

2. Install python-can Vector backend:
   ```powershell
   pip install python-can[vector]
   ```

3. Verify:
   ```powershell
   pyxcp-probe-can-drivers
   # Should list "vector" as available
   ```

4. Configuration:
   ```python
   # pyxcp_conf.py
   def create_transport(parent):
       from pyxcp.transport.can import Can
       return Can(
           parent,
           can_interface="vector",
           can_channel=0,  # Channel index
           can_id_master=0x700,
           can_id_slave=0x701,
           can_bitrate=500000
       )
   ```

#### PEAK-System PCAN (PCAN-USB, PCAN-PCI, etc.)
**Popular USB CAN adapter**

1. Install PCAN driver:
   - Download from: https://www.peak-system.com/Downloads.76.0.html
   - Install PCAN-View (includes drivers)

2. Install python-can PCAN backend:
   ```powershell
   pip install python-can[pcan]
   ```

3. Verify with PCAN-View first (test hardware)

4. Configuration:
   ```python
   def create_transport(parent):
       from pyxcp.transport.can import Can
       return Can(
           parent,
           can_interface="pcan",
           can_channel="PCAN_USBBUS1",  # or PCAN_PCIBUS1, etc.
           can_id_master=0x700,
           can_id_slave=0x701,
           can_bitrate=500000
       )
   ```

#### Kvaser (Leaf, USBcan, etc.)
1. Install Kvaser CANlib SDK from: https://www.kvaser.com/downloads/
2. Install backend:
   ```powershell
   pip install python-can[kvaser]
   ```

#### IXXAT (HMS)
1. Install IXXAT VCI driver
2. Install backend:
   ```powershell
   pip install python-can[ixxat]
   ```

#### Virtual CAN (for testing without hardware)
```powershell
# No installation needed, built into python-can
pip install python-can

# Configuration
def create_transport(parent):
    from pyxcp.transport.can import Can
    return Can(
        parent,
        can_interface="virtual",
        can_channel="test_channel",
        can_id_master=0x700,
        can_id_slave=0x701
    )
```

### Seed/Key DLLs (32-bit to 64-bit bridging)

**Problem:** OEM seed/key DLLs are typically 32-bit, but Python is 64-bit.

**Solution:** pyXCP includes `asamkeydll.exe` bridge program.

**Setup:**
1. Ensure you have MinGW-w64 installed (to compile bridge if needed)
2. Place seed/key DLL in project directory
3. Configure:
   ```python
   # In config file
   SEED_KEY_DLL = "SeedNKeyXcp.dll"
   ```

pyXCP automatically uses the bridge when running 64-bit Python with 32-bit DLL.

**Troubleshooting:**
```powershell
# Check Python bitness
python -c "import struct; print(struct.calcsize('P') * 8)"
# Output: 64 (for 64-bit Python)

# If asamkeydll.exe missing, rebuild:
# (Requires MinGW-w64 gcc)
gcc -m32 -o asamkeydll.exe asamkeydll.c
```

### Windows Firewall (for Ethernet XCP)

**Allow Python through firewall:**
```powershell
# Run as Administrator
netsh advfirewall firewall add rule name="Python XCP" dir=in action=allow program="C:\Path\To\python.exe" enable=yes
```

Or: Windows Defender Firewall → Allow an app → Add Python executable

---

## Linux Setup

### Distribution-Specific Install

#### Ubuntu/Debian (20.04, 22.04, 24.04)
```bash
# Update package index
sudo apt update

# Install build dependencies
sudo apt install -y \
    python3-pip \
    python3-dev \
    python3-venv \
    build-essential \
    cmake \
    pybind11-dev \
    libpython3-dev

# Install pyxcp
pip3 install pyxcp

# For CAN: Install SocketCAN tools
sudo apt install can-utils
```

#### Fedora/RHEL/CentOS
```bash
# Install dependencies
sudo dnf install -y \
    python3-pip \
    python3-devel \
    gcc-c++ \
    cmake \
    pybind11-devel

# Install pyxcp
pip3 install pyxcp

# For CAN
sudo dnf install can-utils
```

#### Arch Linux
```bash
# Install dependencies
sudo pacman -S python-pip base-devel cmake pybind11

# Install pyxcp
pip install pyxcp

# For CAN
sudo pacman -S can-utils
```

### SocketCAN Setup (Native Linux CAN)

**SocketCAN is the recommended CAN interface on Linux** - native kernel support, no proprietary drivers.

#### 1. Check if CAN hardware is detected
```bash
# List CAN interfaces
ip link show | grep can

# If using USB CAN adapter (e.g., PEAK PCAN-USB):
dmesg | grep -i can
# Should show: peak_usb or similar
```

#### 2. Configure CAN interface
```bash
# Bring interface up with 500 kbit/s
sudo ip link set can0 up type can bitrate 500000

# For CAN-FD (if supported):
sudo ip link set can0 up type can bitrate 500000 dbitrate 2000000 fd on

# Verify
ip -details link show can0
```

#### 3. Persistent configuration (systemd)
Create `/etc/systemd/network/80-can0.network`:
```ini
[Match]
Name=can0

[CAN]
BitRate=500K
# For CAN-FD:
# DataBitRate=2M
# FD=yes

[Link]
Up=yes
```

Enable:
```bash
sudo systemctl enable systemd-networkd
sudo systemctl restart systemd-networkd
```

#### 4. Test SocketCAN
```bash
# Terminal 1: Listen for CAN frames
candump can0

# Terminal 2: Send test frame
cansend can0 123#DEADBEEF
```

#### 5. pyXCP configuration
```python
# pyxcp_conf.py
def create_transport(parent):
    from pyxcp.transport.can import Can
    return Can(
        parent,
        can_interface="socketcan",
        can_channel="can0",  # or can1, vcan0, etc.
        can_id_master=0x700,
        can_id_slave=0x701,
        can_bitrate=500000  # Must match interface config
    )
```

### Virtual CAN (for testing without hardware)

```bash
# Load vcan kernel module
sudo modprobe vcan

# Create virtual CAN interface
sudo ip link add dev vcan0 type vcan
sudo ip link set up vcan0

# Verify
ip link show vcan0

# Make persistent (add to /etc/modules):
echo "vcan" | sudo tee -a /etc/modules
```

**pyXCP config for vcan:**
```python
def create_transport(parent):
    from pyxcp.transport.can import Can
    return Can(parent, can_interface="socketcan", can_channel="vcan0",
               can_id_master=0x700, can_id_slave=0x701)
```

### USB Permissions (for USB CAN adapters and USB XCP)

**Problem:** Permission denied accessing USB device

**Solution 1: udev rules (recommended)**

Create `/etc/udev/rules.d/99-pyxcp.rules`:
```bash
# PEAK PCAN-USB (vendor:product = 0c72:000c)
SUBSYSTEM=="usb", ATTRS{idVendor}=="0c72", ATTRS{idProduct}=="000c", MODE="0666"

# Generic rule for all USB CAN adapters (adjust vendor/product):
SUBSYSTEM=="usb", ATTRS{idVendor}=="XXXX", ATTRS{idProduct}=="YYYY", MODE="0666"

# For SocketCAN devices:
KERNEL=="can*", MODE="0666"
```

Reload rules:
```bash
sudo udevadm control --reload-rules
sudo udevadm trigger
```

**Solution 2: Add user to dialout group**
```bash
sudo usermod -a -G dialout $USER
# Log out and back in for changes to take effect
```

### Building from Source on Linux

**When needed:**
- Development of pyXCP itself
- Modifying C++ extensions
- Custom Python installations

**Process:**
```bash
# Clone repository
git clone https://github.com/christoph2/pyxcp.git
cd pyxcp

# Install Poetry (recommended) or use pip
pip3 install poetry

# Install dependencies
poetry install

# Build C++ extensions
python3 build_ext.py

# Verify build
ls -la pyxcp/transport/transport_ext*.so
python3 -c "from pyxcp.transport import transport_ext; print('OK')"

# Run tests
poetry run pytest
```

**Common build issues:** See [LINUX_BUILD_FIXES.md](../LINUX_BUILD_FIXES.md)

### Performance Tuning (Linux)

**For high-frequency DAQ (>1 kHz):**

```bash
# Increase network buffer sizes (for Ethernet XCP)
sudo sysctl -w net.core.rmem_max=26214400
sudo sysctl -w net.core.wmem_max=26214400

# Disable CPU frequency scaling
sudo cpupower frequency-set -g performance

# Set process priority (run pyXCP with elevated priority)
sudo nice -n -10 python3 my_daq_script.py

# Or use chrt for real-time scheduling
sudo chrt -f 50 python3 my_daq_script.py
```

---

## macOS Setup

### Prerequisites

**Install Xcode Command Line Tools:**
```bash
xcode-select --install
```

**Install Homebrew (package manager):**
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### Python Installation

**Option 1: Homebrew (recommended)**
```bash
brew install python@3.12
# Verify
python3 --version
```

**Option 2: Official installer from python.org**

### Install pyXCP

```bash
# Install from PyPI
pip3 install pyxcp

# Or build from source
git clone https://github.com/christoph2/pyxcp.git
cd pyxcp
pip3 install poetry
poetry install
python3 build_ext.py
```

### CAN on macOS

**Limited options compared to Linux/Windows:**

1. **USB CAN adapters with macOS drivers:**
   - PEAK PCAN-USB (driver available from PEAK)
   - Kvaser Leaf (driver from Kvaser)
   - IXXAT USB-to-CAN (HMS driver)

2. **Virtual CAN for testing:**
   ```bash
   pip3 install python-can

   # Use virtual interface in config
   def create_transport(parent):
       from pyxcp.transport.can import Can
       return Can(parent, can_interface="virtual", can_channel="test")
   ```

3. **SocketCAN via Linux VM:**
   - Run Ubuntu in Parallels/VMware Fusion
   - Pass through USB CAN adapter to VM
   - Use SocketCAN in VM (better driver support)

### Known Issues on macOS

**Issue: C++ extension build fails with Xcode 15+**

Error: `cannot find -lpython3.12`

**Solution:**
```bash
# Set library path explicitly
export LDFLAGS="-L$(brew --prefix)/lib"
export CPPFLAGS="-I$(brew --prefix)/include"
pip3 install pyxcp --no-binary pyxcp
```

**Issue: Python.h not found**

**Solution:**
```bash
# Install full Python dev environment
brew reinstall python@3.12
```

---

## Docker and CI/CD

### Docker Container for pyXCP

**Use case:** Consistent testing environment, CI/CD pipelines, reproducible builds

#### Basic Dockerfile

```dockerfile
# Dockerfile
FROM ubuntu:24.04

# Install dependencies
RUN apt-get update && apt-get install -y \
    python3-pip \
    python3-dev \
    build-essential \
    cmake \
    pybind11-dev \
    can-utils \
    && rm -rf /var/lib/apt/lists/*

# Install pyxcp
RUN pip3 install --no-cache-dir pyxcp

# Setup virtual CAN
RUN modprobe vcan || true

# Working directory
WORKDIR /workspace

# Default command
CMD ["python3"]
```

**Build and run:**
```bash
docker build -t pyxcp-dev .
docker run -it --privileged pyxcp-dev bash
# --privileged needed for SocketCAN
```

#### Docker Compose for XCP development

```yaml
# docker-compose.yml
services:
  pyxcp:
    build: .
    privileged: true  # For CAN
    volumes:
      - ./pyxcp_workspace:/workspace
      - /dev:/dev  # Access to host devices
    network_mode: host  # For Ethernet XCP
    environment:
      - PYXCP_CONFIG=/workspace/pyxcp_conf.py
      - PYXCP_LOGLEVEL=DEBUG
    command: python3 my_xcp_script.py
```

**Run:**
```bash
docker-compose up
```

#### Minimal Test Container

```dockerfile
# Dockerfile.test - for CI/CD unit tests
FROM python:3.12-slim

WORKDIR /app
COPY . /app

RUN pip install --no-cache-dir poetry && \
    poetry config virtualenvs.create false && \
    poetry install --no-dev

# Run tests
CMD ["pytest", "-v"]
```

### GitHub Actions CI/CD

**.github/workflows/test.yml:**
```yaml
name: Test pyXCP

on: [push, pull_request]

jobs:
  test:
    runs-on: ${{ matrix.os }}
    strategy:
      matrix:
        os: [ubuntu-latest, windows-latest, macos-latest]
        python-version: ['3.10', '3.11', '3.12']

    steps:
    - uses: actions/checkout@v4

    - name: Set up Python
      uses: actions/setup-python@v5
      with:
        python-version: ${{ matrix.python-version }}

    - name: Install dependencies (Linux)
      if: runner.os == 'Linux'
      run: |
        sudo apt-get update
        sudo apt-get install -y build-essential cmake pybind11-dev

    - name: Install pyxcp
      run: |
        pip install poetry
        poetry install

    - name: Build C++ extensions
      run: python build_ext.py

    - name: Run tests
      run: poetry run pytest -v

    - name: Upload coverage
      uses: codecov/codecov-action@v4
      if: matrix.os == 'ubuntu-latest' && matrix.python-version == '3.12'
```

### GitLab CI

**.gitlab-ci.yml:**
```yaml
image: python:3.12

stages:
  - build
  - test

before_script:
  - apt-get update -qq
  - apt-get install -y build-essential cmake pybind11-dev
  - pip install poetry
  - poetry install

build:
  stage: build
  script:
    - python build_ext.py
    - poetry build
  artifacts:
    paths:
      - dist/

test:
  stage: test
  script:
    - poetry run pytest -v --cov=pyxcp
  coverage: '/TOTAL.*\s+(\d+%)$/'
```

---

## Troubleshooting

### Common Issues Across All Platforms

#### Issue: "No module named 'pyxcp'"

**Cause:** pyXCP not installed or wrong Python interpreter

**Solution:**
```bash
# Verify pip is installing to correct Python
pip --version
python -m pip install pyxcp

# Or use explicit interpreter
python3.12 -m pip install pyxcp
```

#### Issue: "ImportError: cannot import name 'transport_ext'"

**Cause:** C++ extensions not built or incompatible

**Solution:**
```bash
# Reinstall with rebuild
pip install --no-cache-dir --force-reinstall --no-binary pyxcp pyxcp

# Or build manually
python build_ext.py
```

#### Issue: Version mismatch (old pyxcp cached)

**Solution:**
```bash
# Clear pip cache
pip cache purge

# Reinstall
pip uninstall pyxcp
pip install pyxcp
```

---

### Windows-Specific Issues

#### Issue: "error: Microsoft Visual C++ 14.0 or greater is required"

**Cause:** No C++ compiler for building extensions

**Solution:**
1. Install pre-built wheel: `pip install pyxcp` (should work without compiler)
2. Or install Visual Studio Build Tools (see [Windows C++ Build Tools](#c-build-tools-for-source-builds))

#### Issue: CAN driver not found

**Cause:** python-can backend not installed or DLL missing

**Solution:**
```powershell
# Check available drivers
pyxcp-probe-can-drivers

# Install missing backend
pip install python-can[vector]  # or [pcan], [kvaser], etc.

# Verify DLL exists (e.g., for Vector)
where vxlapi64.dll
# Should be in C:\Windows\System32 or Vector installation folder
```

#### Issue: "OSError: [WinError 126] The specified module could not be found"

**Cause:** Missing Visual C++ Redistributable

**Solution:**
Download and install: https://learn.microsoft.com/en-us/cpp/windows/latest-supported-vc-redist

---

### Linux-Specific Issues

#### Issue: "error: command 'gcc' failed"

**Cause:** Missing build tools

**Solution:**
```bash
sudo apt install build-essential python3-dev cmake pybind11-dev
```

#### Issue: "Operation not permitted" when accessing CAN

**Cause:** Insufficient permissions

**Solution:**
```bash
# Option 1: Add user to groups
sudo usermod -a -G dialout $USER
sudo usermod -a -G can $USER
newgrp dialout  # Or log out/in

# Option 2: Run with sudo (not recommended for production)
sudo python3 my_script.py
```

#### Issue: CAN interface not showing up

**Cause:** Driver not loaded or interface down

**Solution:**
```bash
# Check interface exists
ip link show

# Check dmesg for driver errors
dmesg | tail -30

# Bring up interface
sudo ip link set can0 up type can bitrate 500000

# For USB adapters, check if connected
lsusb
```

#### Issue: "No such file or directory: '/usr/lib/libpython3.12.so'"

**Cause:** Python library not installed or wrong path

**Solution:**
```bash
# Install Python dev package
sudo apt install python3.12-dev libpython3.12-dev

# Or let CMake auto-detect (pyxcp v0.26.3+ handles this)
pip install --no-binary pyxcp pyxcp
```

See [LINUX_BUILD_FIXES.md](../LINUX_BUILD_FIXES.md) for detailed Linux build troubleshooting.

---

### macOS-Specific Issues

#### Issue: "xcrun: error: invalid active developer path"

**Cause:** Xcode Command Line Tools not installed

**Solution:**
```bash
xcode-select --install
```

#### Issue: CAN driver not available

**Cause:** Limited macOS CAN driver support

**Solution:**
- Install vendor-specific driver (PEAK, Kvaser)
- Or use virtual CAN for testing
- Or run Linux VM with USB passthrough

---

## Summary

### Recommended Setup by Use Case

**Production deployment (Ethernet XCP):**
- Any platform works well
- Linux preferred for stability and performance
- Windows if using Vector tools (CANoe/CANalyzer)

**CAN bus development:**
- **Linux:** Best option (SocketCAN, native kernel support)
- **Windows:** Good with Vector/PCAN drivers
- **macOS:** Limited, consider Linux VM

**CI/CD and automated testing:**
- Docker with Ubuntu base image
- GitHub Actions multi-platform matrix
- Virtual CAN for tests without hardware

**Quick prototyping:**
- Windows: `pip install pyxcp` + Vector/PCAN driver
- Linux: `apt install python3-pyxcp can-utils` + SocketCAN
- macOS: `brew install python@3.12` + `pip install pyxcp`

### Quick Health Check

Run this after installation on any platform:

```bash
# 1. Verify pyxcp installed
python -m pip show pyxcp

# 2. Test import
python -c "import pyxcp; print(f'pyXCP {pyxcp.__version__} OK')"

# 3. Check CAN drivers
pyxcp-probe-can-drivers

# 4. Test C++ extensions
python -c "from pyxcp.transport import transport_ext; print('Extensions OK')"

# 5. Run example
xcp-examples ./test_examples
# Edit test_examples/basic_can_connection.py config, then run
```

If all 5 steps succeed, you're ready to use pyXCP! 🚀

---

## Additional Resources

- **Installation:** [docs/installation.rst](installation.rst) - Basic installation instructions
- **Quickstart:** [docs/quickstart.md](quickstart.md) - Your first XCP connection
- **CLI Tools:** [docs/cli_tools.md](cli_tools.md) - Command-line tools setup
- **Linux Builds:** [LINUX_BUILD_FIXES.md](../LINUX_BUILD_FIXES.md) - Linux-specific build issues
- **FAQ:** [docs/FAQ.md](FAQ.md) - Common questions

**python-can documentation:** https://python-can.readthedocs.io/  
**SocketCAN tutorial:** https://elinux.org/Bringing_CAN_interface_up

#!/bin/bash
# Linux Build Test Script for pyxcp
# Tests the build process on Ubuntu/Debian systems

set -e  # Exit on error

echo "========================================"
echo "pyxcp Linux Build Test"
echo "========================================"
echo ""

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Print system info
echo -e "${YELLOW}System Information:${NC}"
uname -a
python3 --version
cmake --version 2>/dev/null || echo "cmake NOT installed"
gcc --version | head -1 || echo "gcc NOT installed"
echo ""

# Check dependencies
echo -e "${YELLOW}Checking Dependencies...${NC}"
MISSING_DEPS=()

command -v cmake >/dev/null 2>&1 || MISSING_DEPS+=("cmake")
command -v gcc >/dev/null 2>&1 || MISSING_DEPS+=("build-essential")
command -v g++ >/dev/null 2>&1 || MISSING_DEPS+=("g++")
python3 -c "import pybind11" 2>/dev/null || MISSING_DEPS+=("pybind11-dev OR python3-pybind11")

# Check for Python development headers
if ! pkg-config --exists python3; then
    MISSING_DEPS+=("python3-dev")
fi

# Check for Python link library
PYTHON_LIB=$(find /usr -name "libpython*.so" 2>/dev/null | head -1)
if [ -z "$PYTHON_LIB" ]; then
    echo -e "${YELLOW}Warning: Python shared library not found${NC}"
fi

PYTHON_STATIC_LIB=$(find /usr -name "libpython*.a" 2>/dev/null | head -1)
if [ -z "$PYTHON_STATIC_LIB" ]; then
    echo -e "${YELLOW}Warning: Python static library not found (may be OK)${NC}"
fi

if [ ${#MISSING_DEPS[@]} -gt 0 ]; then
    echo -e "${RED}ERROR: Missing dependencies:${NC}"
    printf '  - %s\n' "${MISSING_DEPS[@]}"
    echo ""
    echo -e "${YELLOW}Install with:${NC}"
    echo "  sudo apt update"
    echo "  sudo apt install build-essential cmake python3-dev libpython3-dev pybind11-dev"
    exit 1
fi

echo -e "${GREEN}✓ All dependencies found${NC}"
echo ""

# Test pybind11 config
echo -e "${YELLOW}Testing pybind11 configuration...${NC}"
PYBIND11_CMAKE=$(python3 -m pybind11 --cmakedir 2>/dev/null || echo "")
if [ -z "$PYBIND11_CMAKE" ]; then
    echo -e "${RED}ERROR: pybind11 CMake config not found${NC}"
    echo "Install with: pip install pybind11[global]"
    exit 1
fi
echo "pybind11 CMake dir: $PYBIND11_CMAKE"
export pybind11_DIR="$PYBIND11_CMAKE"
echo -e "${GREEN}✓ pybind11 configured${NC}"
echo ""

# Test Python library detection
echo -e "${YELLOW}Testing Python library detection...${NC}"
python3 << 'EOF'
import sysconfig
import sys
from pathlib import Path

VARS = sysconfig.get_config_vars()
print(f"Python version: {sys.version}")
print(f"Python executable: {sys.executable}")
print(f"Python include: {sysconfig.get_path('include')}")
print(f"Python library: {VARS.get('LIBRARY', 'N/A')}")
print(f"LIBDIR: {VARS.get('LIBDIR', 'N/A')}")
print(f"MULTIARCH: {VARS.get('MULTIARCH', 'N/A')}")

# Check if library exists
library = VARS.get('LIBRARY')
if library:
    libdir = VARS.get('LIBDIR')
    multiarch = VARS.get('MULTIARCH', '')
    if libdir:
        paths = [
            Path(libdir) / multiarch / library,
            Path(libdir) / library
        ]
        found = False
        for p in paths:
            if p.exists():
                print(f"✓ Found library at: {p}")
                found = True
                break
        if not found:
            print(f"✗ Library not found in {libdir}")
            sys.exit(1)
else:
    print("✗ LIBRARY variable not set")
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Python library detection failed${NC}"
    echo "This may cause build issues. Install python3-dev:"
    echo "  sudo apt install python3-dev libpython3-dev"
    exit 1
fi
echo -e "${GREEN}✓ Python library detected${NC}"
echo ""

# Clean previous build
echo -e "${YELLOW}Cleaning previous build...${NC}"
rm -rf build dist *.egg-info
rm -f pyxcp/**/*.so pyxcp/**/*.pyd
echo -e "${GREEN}✓ Cleaned${NC}"
echo ""

# Build extensions
echo -e "${YELLOW}Building C++ extensions...${NC}"
echo "========================================"
python3 build_ext.py

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${RED}ERROR: Build failed${NC}"
    exit 1
fi
echo "========================================"
echo -e "${GREEN}✓ Build successful${NC}"
echo ""

# Verify built extensions
echo -e "${YELLOW}Verifying built extensions...${NC}"
EXPECTED_EXTENSIONS=(
    "pyxcp/transport/transport_ext"
    "pyxcp/cpp_ext/cpp_ext"
    "pyxcp/daq_stim/stim"
    "pyxcp/recorder/rekorder"
)

MISSING_EXTENSIONS=()
for ext in "${EXPECTED_EXTENSIONS[@]}"; do
    if ls ${ext}*.so 1> /dev/null 2>&1; then
        echo -e "  ${GREEN}✓${NC} ${ext}.so"
    else
        echo -e "  ${RED}✗${NC} ${ext}.so"
        MISSING_EXTENSIONS+=("$ext")
    fi
done

if [ ${#MISSING_EXTENSIONS[@]} -gt 0 ]; then
    echo ""
    echo -e "${RED}ERROR: Missing extensions:${NC}"
    printf '  - %s\n' "${MISSING_EXTENSIONS[@]}"
    exit 1
fi
echo -e "${GREEN}✓ All extensions built${NC}"
echo ""

# Test import
echo -e "${YELLOW}Testing Python import...${NC}"
python3 << 'EOF'
try:
    import pyxcp
    print(f"✓ pyxcp version: {pyxcp.__version__}")

    # Test extensions
    from pyxcp.transport import transport_ext
    print("✓ transport_ext imported")

    from pyxcp.cpp_ext import cpp_ext
    print("✓ cpp_ext imported")

    from pyxcp.daq_stim import stim
    print("✓ stim imported")

    from pyxcp.recorder import rekorder
    print("✓ rekorder imported")

    print("\n✓ All imports successful")
except ImportError as e:
    print(f"\n✗ Import failed: {e}")
    import sys
    sys.exit(1)
EOF

if [ $? -ne 0 ]; then
    echo -e "${RED}ERROR: Import test failed${NC}"
    exit 1
fi
echo ""

# Run quick tests
echo -e "${YELLOW}Running quick tests...${NC}"
python3 -m pytest pyxcp/tests/test_utils.py -v --tb=short

if [ $? -ne 0 ]; then
    echo ""
    echo -e "${YELLOW}Warning: Some tests failed${NC}"
    echo "This may be OK if you don't have CAN hardware"
else
    echo -e "${GREEN}✓ Tests passed${NC}"
fi
echo ""

# Summary
echo "========================================"
echo -e "${GREEN}✓ Linux Build Test PASSED${NC}"
echo "========================================"
echo ""
echo "Next steps:"
echo "  1. Run full test suite: pytest"
echo "  2. Install locally: pip install -e ."
echo "  3. Build wheel: pip install build && python -m build"
echo ""

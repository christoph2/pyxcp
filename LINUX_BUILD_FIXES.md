# Linux Build Issues - Fixes and Workarounds

## Issues Fixed

### 1. C++23 → C++20 Downgrade
**Problem:** C++23 requires very new compilers (GCC 11+) not available on Ubuntu 20.04/22.04  
**Fix:** Changed `CMAKE_CXX_STANDARD` from 23 to 20 in CMakeLists.txt  
**Impact:** Better compatibility, still modern C++

### 2. Python Library Detection
**Problem:** `build_ext.py` crashes with `UnboundLocalError: libdir` when Python library not found  
**Fix:** Added fallback to proceed without explicit library path (let CMake auto-detect)  
**Files Changed:** `build_ext.py` lines 84-87, 120-123

### 3. pybind11 Not REQUIRED
**Problem:** `find_package(pybind11 CONFIG)` fails silently if not found  
**Fix:** Added `REQUIRED` keyword: `find_package(pybind11 CONFIG REQUIRED)`  
**Files Changed:** `CMakeLists.txt` line 12

### 4. mtune=native Removed
**Problem:** `-mtune=native` creates non-portable binaries (optimized for build machine CPU)  
**Fix:** Removed flag for better wheel distribution  
**Files Changed:** `CMakeLists.txt` line 22

### 5. Added CMAKE_CXX_STANDARD_REQUIRED
**Problem:** CMake might fall back to older C++ standard silently  
**Fix:** Added `CMAKE_CXX_STANDARD_REQUIRED ON` to enforce C++20  
**Files Changed:** `CMakeLists.txt` line 17

## Testing

### Test on Ubuntu 24.04:
```bash
chmod +x test_linux_build.sh
./test_linux_build.sh
```

The script will:
1. Check all dependencies
2. Verify Python library detection
3. Build extensions
4. Test imports
5. Run quick tests

### Manual Test:
```bash
# Install dependencies
sudo apt update
sudo apt install build-essential cmake python3-dev libpython3-dev pybind11-dev

# Build
python3 build_ext.py

# Verify
ls -la pyxcp/transport/transport_ext*.so
python3 -c "from pyxcp.transport import transport_ext; print('OK')"
```

## Common Issues & Solutions

### Issue: `cmake: command not found`
```bash
sudo apt install cmake
```

### Issue: `pybind11 not found`
```bash
# Option 1: System package
sudo apt install pybind11-dev

# Option 2: Python package
pip install pybind11[global]
export pybind11_DIR=$(python3 -m pybind11 --cmakedir)
```

### Issue: `Python.h: No such file or directory`
```bash
sudo apt install python3-dev libpython3-dev
```

### Issue: `cannot find -lpython3.12` (link error)
```bash
# Verify library exists
find /usr -name "libpython*.so"
find /usr -name "libpython*.a"

# If missing, install dev package
sudo apt install python3.12-dev  # or your Python version
```

### Issue: GCC too old for C++20
```bash
# Check GCC version
gcc --version

# GCC 8+ required for C++20
# On Ubuntu 18.04, upgrade:
sudo add-apt-repository ppa:ubuntu-toolchain-r/test
sudo apt update
sudo apt install gcc-10 g++-10
export CC=gcc-10
export CXX=g++-10
```

## GitHub Actions / CI

### Update cibuildwheel config:

In `.github/workflows/build.yml`:
```yaml
- name: Install dependencies (Linux)
  if: runner.os == 'Linux'
  run: |
    sudo apt-get update
    sudo apt-get install -y build-essential cmake pybind11-dev

- name: Build wheels
  uses: pypa/cibuildwheel@v2.16.5
  env:
    CIBW_BEFORE_BUILD_LINUX: |
      yum install -y cmake3 pybind11-devel || \
      apt-get update && apt-get install -y cmake pybind11-dev
```

## Distribution Checklist

Before releasing wheels:
- [ ] Test on Ubuntu 20.04, 22.04, 24.04
- [ ] Test on Debian 11, 12
- [ ] Test with Python 3.10, 3.11, 3.12, 3.13, 3.14
- [ ] Verify wheel contains all .so files
- [ ] Test import in fresh virtualenv
- [ ] Check wheel size (<5 MB per platform ideally)

## Related Issues
- #169: Cannot build on Ubuntu 24.04
- #240: transport_ext not found
- #188: DLL load failed
- #186: Linux wheels missing from PyPI

## Next Steps
1. ✅ Test this locally on Windows (limited)
2. ⏳ Test on Ubuntu 24.04 VM
3. ⏳ Update CI/CD pipeline
4. ⏳ Release 0.26.3 with fixes
5. ⏳ Backport to older versions if needed

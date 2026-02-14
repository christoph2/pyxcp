# Changelog

All notable changes to pyxcp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **Docs**: Quickstart Guide - "From Zero to DAQ in 15 Minutes" (#184, #129, #143)
- **Docs**: CLI Tools Reference - Comprehensive command-line tools guide (23 KB)
- **Docs**: 6 production-ready example scripts (basic connection, calibration, DAQ, Ethernet, A2L, multi-ECU)

### Documented
- **Quickstart**: Installation and verification
- **Quickstart**: First CAN and Ethernet connections
- **Quickstart**: Reading/writing parameters with examples
- **Quickstart**: Basic DAQ recording to CSV
- **Quickstart**: Three configuration methods (CLI, file, programmatic)
- **Quickstart**: Common troubleshooting scenarios
- **Quickstart**: Quick reference table for essential commands
- **Examples**: `basic_can_connection.py` - Hello world XCP workflow
- **Examples**: `calibration_workflow.py` - Complete calibration with seed/key unlock (#184)
- **Examples**: `daq_recording.py` - Full DAQ to CSV with conversions
- **Examples**: `ethernet_connection.py` - TCP/UDP examples with error recovery
- **Examples**: `a2l_integration.py` - Symbolic access with pya2ldb (#179)
- **Examples**: `multi_ecu_setup.py` - Parallel and synchronized multi-ECU patterns (#227)
- **CLI Tools**: All 7 CLI tools documented with usage, examples, troubleshooting
- **CLI Tools**: Transport-specific configuration tips
- **CLI Tools**: Common workflows (first contact, DAQ setup, multi-ECU)
- **CLI Tools**: Environment variables (PYXCP_CONFIG, PYXCP_LOGLEVEL)
- **CLI Tools**: Troubleshooting matrix for common errors

## [0.26.5] - 2026-02-14

### Added
- **DAQ**: Optional logger parameter for DaqProcessor, DaqRecorder, DaqOnlinePolicy, DaqToCsv (#260)
- **DAQ**: Automatic fallback logger when configuration file not available
- **Config**: PYXCP_CONFIG environment variable for config file location
- **Config**: Multi-path config discovery (CWD, script dir, ~/.pyxcp/, env var)
- **Config**: Programmatic config creation via `create_application_from_config()` (#211)
- **Config**: `set_application()` to set global application instance
- **Tests**: 8 new config discovery tests in `test_config_discovery.py`

### Changed
- **DAQ**: DaqProcessor now works without pyxcp_conf.py configuration file (#260)
- **Config**: Enhanced config file search with multiple fallback locations
- **Config**: Better error messages when config file not found

### Fixed
- **DAQ**: FileNotFoundError when using DaqToCsv in Robot Framework or pytest (#260)
- **Config**: Config discovery now supports test frameworks and CI/CD environments (#211)

### Documented
- **Config**: Robot Framework usage pattern with explicit logger
- **Config**: DaqToCsv configuration options in FAQ
- **Config**: Programmatic configuration examples for library usage
- **Config**: Config file search order and environment variable usage

## [0.26.4] - 2026-02-14

### Added
- **CAN**: Dynamic DAQ filter update method `update_daq_filters()` (#136)
- **CAN**: Multi-channel example `examples/multi_channel_can.py` (#227)

### Changed
- **CAN**: Improved filter timing - filters configured before bus activation (#231)
- **CAN**: Filter logging moved after bus initialization for better diagnostics

### Fixed
- **CAN**: Filter timing race condition causing DAQ interruption (#231)
- **CAN**: DAQ identifiers not included in initial filter (#136)

### Documented
- **CAN**: Vector CANape / XCPsim setup with app_name configuration (#224)
- **CAN**: Multi-channel usage patterns and examples (#227)
- **CAN**: Filter timing and DAQ ID filtering behavior

## [0.26.3] - 2026-02-14

### Added
- GitHub issue templates (bug report, feature request, documentation)
- Comprehensive FAQ documentation (30+ common questions)
- PyInstaller hook file for easier bundling
- Logging configuration with NullHandler default
- CONTRIBUTING.md with development guidelines
- Linux build test script (	est_linux_build.sh)
- TOML configuration deprecation warnings
- **DAQ**: Automatic fallback when GET_DAQ_PROCESSOR_INFO not supported (#230)
- **DAQ**: Implemented REINIT_DAQ pre-action for multiple DAQ lists (#208)

### Changed
- **BREAKING**: C++ standard downgraded from C++23 to C++20 for broader compatibility
- Relaxed dependency version ranges for better compatibility
- CMakeLists.txt: pybind11 now REQUIRED (fails fast if missing)
- CMakeLists.txt: Removed `-mtune=native` for better wheel portability
- build_ext.py: Added fallback for Python library detection
- CI workflow: Added Linux/macOS system dependencies
- Enhanced `.github/copilot-instructions.md`
- **DAQ**: GET_DAQ_PROCESSOR_INFO is now optional (per XCP spec)

### Fixed
- Linux build failures on Ubuntu 24.04 (#169)
- Python library detection on Ubuntu systems
- Logging interference with user applications (#176)
- PyInstaller bundling issues (#261, #203)
- `UnboundLocalError: libdir` during build
- **DAQ**: ECUs without GET_DAQ_PROCESSOR_INFO support now work (#230, #184)
- **DAQ**: Multiple DAQ lists work without NotImplementedError (#208)

### Documented
- FAQ addresses issues: #240, #188, #199, #169, #208, #253, #156, #142, #227, and more
- LINUX_BUILD_FIXES.md with common build issues and solutions
- Contributing guide with quick start and conventions
- DAQ fallback behavior and ECU compatibility

## [0.26.2] - 2024-XX-XX

### Previous Release
See git history for changes prior to 0.26.3.

---

## Version Numbering

pyxcp follows [Semantic Versioning](https://semver.org/):
- MAJOR version: Incompatible API changes
- MINOR version: New functionality (backwards compatible)
- PATCH version: Bug fixes (backwards compatible)

## Issue References

This changelog references GitHub issues. View details at:
https://github.com/christoph2/pyxcp/issues/[issue-number]

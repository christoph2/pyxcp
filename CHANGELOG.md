# Changelog

All notable changes to pyxcp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- **WP-7**: Comprehensive A2L Integration Guide (`docs/a2l_integration.rst`, 14 KB)
  * End-to-end tutorial: XCP + A2L workflow with symbolic access
  * Complete code examples: calibration, DAQ setup, unit conversion
  * Tool comparison: pyxcp vs asamint usage scenarios
  * Prominent reference to `asamint` project (production MCS)
  * Data type conversion guide (RAT_FUNC, TAB_VERB)
  * Troubleshooting section for common A2L issues
  * FAQ: When to use pyxcp vs asamint
- **README**: Added "Related Projects" section highlighting asamint
- **README**: Quick reference to A2L Integration Guide

## [0.27.0] - 2026-02-15

### Changed
- **BREAKING**: Default frame acquisition policy changed from `LegacyFrameAcquisitionPolicy` to `NoOpPolicy` (#171)
  * Prevents unbounded memory growth in DAQ mode (~2 GB leak in 24h @ 100 Hz)
  * **Validation results**: NoOpPolicy has 290x less memory growth than Legacy (6.75 MB vs 1,958 MB in 24h)
  * `LegacyFrameAcquisitionPolicy` now emits `DeprecationWarning` when explicitly used
  * **Migration required**: Code accessing `.daqQueue` or `.evQueue` must switch to modern policies
  * See `docs/migration_policies.rst` for complete migration guide

### Added
- **WP-6 Phase 2-4**: Memory leak fix and validation
  * `NoOpPolicy` as new default: O(1) memory (discards frames immediately)
  * `FrameRecorderPolicy`: Streams to disk with 25x less memory growth than Legacy
  * `StdoutPolicy`: Console output with constant memory
  * All policies exported from `pyxcp.transport` for easy access
  * Comprehensive documentation (`docs/migration_policies.rst`, 7.5 KB):
    - Policy comparison with code examples
    - Performance benchmarks from 5-minute validation tests
    - Migration checklist for existing code
    - Backward compatibility guide
  * Validation test scripts (`pyxcp/benchmarks/validation_*.py`)

### Fixed
- **Issue #171**: Memory leak in DAQ mode completely resolved
  * Root cause: `LegacyFrameAcquisitionPolicy` had 8 unbounded C++ TsQueues
  * Event queue grew indefinitely during DAQ operation
  * Solution: Changed default to `NoOpPolicy` with O(1) memory footprint

## [0.26.8] - 2026-02-15

### Added
- **WP-8 Phase 1**: Configurable retry strategy via `c.General.max_retries` (#216, #107, #155)
  * `-1` (default): Infinite retries per XCP standard
  * `0`: No retries, fail immediately
  * `≥1`: Max retry attempts before exception
  * Prevents infinite loops in production while maintaining XCP spec compliance
  * 12 new tests for retry behavior
- **WP-8 Phase 2**: Enhanced timeout diagnostics with frame counters
  * Frame tracking: `frames_sent`, `frames_received`, `last_command_sent`
  * Transport-specific troubleshooting hints (CAN: termination, IDs, bitrate; ETH: network, firewall, IP/port)
  * Suggested timeout increase in error messages
  * Enhanced diagnostics dump with frame statistics
  * 7 new tests for timeout diagnostics
- **FAQ**: Comprehensive retry configuration guide with production vs development recommendations
- **Example**: `robust_error_handling.py` demonstrating retry strategies for different environments

### Changed
- **Error Handler**: Repeater class now respects `max_retries` configuration option
- **Error Handler**: User can override XCP standard infinite retry behavior
- **Transport**: Timeout error messages now include frame counts and specific troubleshooting steps
- **Transport**: Diagnostics dump includes frame counters for better failure analysis

## [0.26.7] - 2026-02-14

### Added
- **CAN-FD Documentation**: Comprehensive guide in FAQ.md covering mixed mode, pure FD mode, platform setup, and troubleshooting (#70)
- **CAN-FD Example**: New `canfd_example.py` (10 KB) demonstrating CAN-FD configuration for both modes

### Fixed
- **Issue #70**: CAN-FD support verified (resolved in v0.16.8) and fully documented with examples
- **Issue #209**: Master.close() delay reduced from ~5s to ~0.6s (10x improvement)
  * CAN transport `recv()` timeout optimized: 2.0s → 0.1s for responsive shutdown
  * Listener thread join timeout reduced: 2.0s → 0.5s
  * All 169 CAN tests passing
- **Issue #217**: SlCan parameter filtering verified (already fixed in v0.26.1, commit d8607dc)

### Changed
- **Performance**: CAN listen thread now exits within ~100ms after close signal (was up to 2 seconds)
- **Performance**: Master.close() comparable to udsoncan speed (~0.6s vs ~5s previously)

### Documented
- **CAN-FD**: Mixed mode (FD on-demand) vs Pure FD mode (AUTOSAR compliant)
- **CAN-FD**: Platform-specific setup for Linux SocketCAN and Windows Vector/PEAK
- **CAN-FD**: Discrete DLCs (0-8, 12, 16, 20, 24, 32, 48, 64) and padding behavior
- **CAN-FD**: ECU capability detection and troubleshooting guide

## [0.26.6] - 2026-02-14

### Added
- **Docs**: Quickstart Guide - "From Zero to DAQ in 15 Minutes" (11.8 KB) (#184, #129, #143)
- **Docs**: CLI Tools Reference - Comprehensive command-line tools guide (23 KB) (#184, #113)
- **Docs**: Platform Setup Guide - OS-specific installation and configuration (22 KB) (#262, #253, #169)
- **Docs**: Troubleshooting Guide - Symptom-based decision trees (24 KB) (20+ issues addressed)
- **Docs**: 6 production-ready example scripts (43 KB total) (#184, #179, #227, #113, #143, #129)
  * `basic_can_connection.py` - Hello world XCP workflow (2.5 KB)
  * `calibration_workflow.py` - Complete calibration with seed/key unlock (5.4 KB)
  * `daq_recording.py` - Full DAQ to CSV with conversions (5.8 KB)
  * `ethernet_connection.py` - TCP/UDP examples with error recovery (8.9 KB)
  * `a2l_integration.py` - Symbolic access with pya2ldb (9.6 KB)
  * `multi_ecu_setup.py` - Parallel and synchronized multi-ECU patterns (11.0 KB)

### Documented
- **Quickstart**: Installation and verification for new users
- **Quickstart**: First CAN and Ethernet connections with examples
- **Quickstart**: Reading/writing parameters with code samples
- **Quickstart**: Basic DAQ recording to CSV workflow
- **Quickstart**: Three configuration methods (CLI, file, programmatic)
- **Quickstart**: Common troubleshooting scenarios with solutions
- **Quickstart**: Quick reference table for essential commands
- **CLI Tools**: All 7 CLI tools with usage, examples, troubleshooting
- **CLI Tools**: Transport-specific configuration tips (CAN, Ethernet, USB, Serial)
- **CLI Tools**: Common workflows (first contact, DAQ setup, multi-ECU)
- **CLI Tools**: Environment variables (PYXCP_CONFIG, PYXCP_LOGLEVEL)
- **CLI Tools**: Troubleshooting matrix for common CLI errors
- **Platform Setup**: Windows installation (Python, MSVC, CAN drivers: Vector/PCAN/Kvaser/IXXAT)
- **Platform Setup**: Linux installation (Ubuntu/Debian/Fedora/Arch + SocketCAN setup)
- **Platform Setup**: macOS installation (Homebrew, Xcode tools, limited CAN options)
- **Platform Setup**: Docker and CI/CD (Dockerfile, docker-compose, GitHub Actions, GitLab CI)
- **Platform Setup**: CAN driver setup for all platforms (SocketCAN, Vector, PCAN, Virtual CAN)
- **Platform Setup**: USB permissions (Linux udev rules for non-root access)
- **Platform Setup**: Build from source instructions (all platforms)
- **Platform Setup**: Seed/key DLL bridging on Windows (32-bit to 64-bit)
- **Platform Setup**: Platform-specific troubleshooting matrix
- **Platform Setup**: Performance tuning tips (Linux real-time scheduling, network buffers)
- **Troubleshooting**: Symptom-based decision trees (connection, import, config, DAQ, CAN, performance)
- **Troubleshooting**: XCP error code reference (0x00-0x43) with solutions
- **Troubleshooting**: Python exception guide (TimeoutError, PermissionError, OSError)
- **Troubleshooting**: Platform-specific issue matrix (Linux/Windows/macOS)
- **Troubleshooting**: USB permissions setup (Linux udev rules)
- **Troubleshooting**: 7-step quick diagnostic checklist
- **FAQ**: Enhanced troubleshooting section with links to decision trees and guides

### Summary
This release adds **123.8 KB** of comprehensive documentation addressing the most common user questions and issues:
- **New users**: Complete 15-minute quickstart guide eliminates initial confusion
- **Developers**: 6 production-ready examples provide copy-paste templates for common tasks
- **Operators**: CLI tools reference covers all command-line utilities
- **Admins**: Platform setup guide with OS-specific installation for Windows/Linux/macOS
- **Support**: Troubleshooting decision trees for quick problem resolution

**Issues Addressed:** #184 (50 comments), #179, #227, #260, #211, #262, #253, #188, #199, #240,
#169, #261, #203, #247, #263, #223, #226, #219, #212, #113, #143, #129 (20+ issues)

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

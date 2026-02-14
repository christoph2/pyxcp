# Changelog

All notable changes to pyxcp will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- GitHub issue templates (bug report, feature request, documentation)
- Comprehensive FAQ documentation (30+ common questions)
- PyInstaller hook file for easier bundling
- Logging configuration with NullHandler default
- CONTRIBUTING.md with development guidelines
- Linux build test script (	est_linux_build.sh)
- TOML configuration deprecation warnings

### Changed
- **BREAKING**: C++ standard downgraded from C++23 to C++20 for broader compatibility
- Relaxed dependency version ranges for better compatibility
- CMakeLists.txt: pybind11 now REQUIRED (fails fast if missing)
- CMakeLists.txt: Removed `-mtune=native` for better wheel portability
- build_ext.py: Added fallback for Python library detection
- CI workflow: Added Linux/macOS system dependencies
- Enhanced `.github/copilot-instructions.md`

### Fixed
- Linux build failures on Ubuntu 24.04 (#169)
- Python library detection on Ubuntu systems
- Logging interference with user applications (#176)
- PyInstaller bundling issues (#261, #203)
- `UnboundLocalError: libdir` during build

### Documented
- FAQ addresses issues: #240, #188, #199, #169, #208, #253, #156, #142, #227, and more
- LINUX_BUILD_FIXES.md with common build issues and solutions
- Contributing guide with quick start and conventions

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

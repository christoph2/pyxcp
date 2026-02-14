# Contributing to pyxcp

Thank you for your interest in contributing to pyxcp! This document provides guidelines and information for contributors.

## Quick Start

1. **Fork the repository** on GitHub
2. **Clone your fork** locally:
   ```bash
   git clone https://github.com/YOUR-USERNAME/pyxcp.git
   cd pyxcp
   ```
3. **Install development dependencies**:
   ```bash
   poetry install --with dev
   pre-commit install
   ```
4. **Create a branch** for your changes:
   ```bash
   git checkout -b feature/your-feature-name
   ```

## Development Workflow

### Building C++ Extensions

pyxcp includes native C++ extensions that need to be compiled:

```bash
# Build extensions
python build_ext.py

# On Linux, ensure dependencies are installed first:
sudo apt install build-essential cmake python3-dev pybind11-dev
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest pyxcp/tests/test_can.py

# Run with coverage
pytest --cov=pyxcp --cov-report=html

# Run single test
pytest pyxcp/tests/test_master.py::TestMaster::testConnect
```

### Code Quality

We use pre-commit hooks to ensure code quality:

```bash
# Run all checks manually
pre-commit run --all-files

# Individual tools:
ruff format .          # Format code
ruff check . --fix     # Lint and auto-fix
bandit -c bandit.yml -r pyxcp/  # Security scan
mypy pyxcp/           # Type checking
```

**Code Style:**
- Line length: 132 characters
- Formatter: ruff (replaces black)
- Follow existing patterns in the codebase

### Making Changes

1. **Keep changes focused**: One feature or bug fix per PR
2. **Write tests**: Add tests for new features or bug fixes
3. **Update documentation**: Update docs if behavior changes
4. **Follow conventions**: See [Key Conventions](#key-conventions) below

### Committing

```bash
# Stage your changes
git add .

# Commit with descriptive message
git commit -m "Add feature: description

- Detail 1
- Detail 2

Fixes: #123"
```

All commits are automatically checked by pre-commit hooks.

## Pull Request Process

1. **Update your branch** with latest main:
   ```bash
   git fetch upstream
   git rebase upstream/master
   ```

2. **Push to your fork**:
   ```bash
   git push origin feature/your-feature-name
   ```

3. **Create Pull Request** on GitHub:
   - Use the PR template
   - Reference related issues
   - Describe what changed and why
   - Add screenshots if relevant

4. **Respond to reviews**:
   - Address feedback promptly
   - Push additional commits to the same branch
   - Mark conversations as resolved when fixed

5. **Merge requirements**:
   - All tests pass
   - Pre-commit hooks pass
   - At least one maintainer approval
   - No merge conflicts

## Key Conventions

### Project-Specific Patterns

1. **Context Manager for XCP connections**:
   ```python
   from pyxcp.cmdline import ArgumentParser

   ap = ArgumentParser(description="My tool")
   with ap.run() as x:
       x.connect()
       # ... operations
       x.disconnect()
   ```

2. **Configuration via Traitlets** (not TOML):
   ```python
   from pyxcp.config import get_config

   c = get_config()
   c.Transport.layer = 'CAN'
   c.Transport.Can.interface = 'vector'
   ```

3. **Transport Layer** - inherit from `base.BaseTransport`:
   ```python
   from pyxcp.transport.base import BaseTransport

   class MyTransport(BaseTransport):
       def connect(self):
           # Implementation
           pass
   ```

4. **C++ Extensions**:
   - Source in `pyxcp/{module}/*.cpp`
   - pybind11 wrapper in `*_wrapper.cpp`
   - Rebuild after changes: `python build_ext.py`

### Testing Patterns

- Use `pyxcp.transport.mock` for tests without hardware
- Tests with hardware should be skippable (check for `PYXCP_TEST_HARDWARE` env var)
- DAQ tests use fixtures sparingly (prefer direct instantiation)

### Documentation

- Docstrings: Google style
- Update `docs/` if adding features
- Add examples to `pyxcp/examples/` for significant features
- Update FAQ for common issues

## Areas to Contribute

Looking for ideas? Check these:

### High Priority (from Roadmap)
- [ ] Implement `REINIT_DAQ` command (issue #208)
- [ ] Fix CAN filter timing (issue #231)
- [ ] Multi-channel CAN support (issue #227)
- [ ] Improve DAQ documentation and examples (issue #156, #142)
- [ ] Memory leak in DAQ mode (issue #171)

### Documentation
- [ ] More tutorial examples
- [ ] Video tutorials
- [ ] Translation (German, Chinese)
- [ ] Troubleshooting guides

### Testing
- [ ] Increase test coverage (currently ~85%)
- [ ] Integration tests with real ECUs
- [ ] Performance benchmarks

### Good First Issues
Look for issues labeled `good-first-issue` on GitHub.

## Reporting Bugs

Use the [Bug Report template](https://github.com/christoph2/pyxcp/issues/new?template=bug_report.yml) and include:

- pyxcp version
- Python version
- Operating system
- Transport layer (CAN/ETH/USB/Serial)
- Minimal code to reproduce
- Expected vs actual behavior

## Feature Requests

Use the [Feature Request template](https://github.com/christoph2/pyxcp/issues/new?template=feature_request.yml) and describe:

- Problem you're trying to solve
- Proposed solution
- Alternative approaches considered
- Impact/use case

## Communication

- **Issues**: Bug reports, feature requests
- **Discussions**: Questions, ideas, general discussion
- **Pull Requests**: Code contributions
- **Email**: christoph2@users.noreply.github.com (for security issues)

## Code of Conduct

Please read and follow our [Code of Conduct](CODE_OF_CONDUCT.md). We are committed to providing a welcoming and inclusive environment.

## License

By contributing, you agree that your contributions will be licensed under the LGPL v3+ license.

## Recognition

Contributors are listed in [CONTRIBUTORS](CONTRIBUTORS) file. Thank you for your contributions!

## Work Packages & Roadmap

Check our [roadmap](https://github.com/christoph2/pyxcp/issues) for planned features and improvements. Major initiatives are organized into Work Packages:

- **WP-1**: Build & Deployment Infrastructure
- **WP-2**: DAQ Implementation
- **WP-3**: CAN Transport Stability
- **WP-4**: Configuration System
- **WP-5**: Error Handling
- **WP-6**: Memory & Performance
- **WP-7**: Documentation
- **WP-8**: Logging
- **WP-9**: Extended Features

See session roadmap documents for details on each work package.

## Getting Help

- **FAQ**: Check [docs/FAQ.md](docs/FAQ.md) first
- **Documentation**: See `docs/` folder
- **Examples**: See `pyxcp/examples/` folder
- **Discussions**: Ask questions in GitHub Discussions
- **Issues**: Search existing issues for similar problems

## Development Environment Tips

### VS Code

Recommended extensions:
- Python
- Pylance
- Ruff
- C/C++ (for native extensions)
- CMake

### PyCharm

- Enable poetry integration
- Configure ruff as external tool
- Set line length to 132

### Linux Development

```bash
# Ubuntu/Debian dependencies
sudo apt install build-essential cmake python3-dev pybind11-dev

# Test build
./test_linux_build.sh
```

### Windows Development

- Install Visual Studio Build Tools
- Select "Desktop development with C++"
- Restart terminal after install

---

**Thank you for contributing to pyxcp!** 🚀

For questions or guidance, open a [Discussion](https://github.com/christoph2/pyxcp/discussions) or reach out to maintainers.

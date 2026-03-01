# Configuration Migration Guide

**Quick Start:** pyXCP v0.26+ uses a new **Python-based** configuration system powered by [Traitlets](https://traitlets.readthedocs.io/). This replaces the old TOML/JSON dictionary-based configs.

## Why Migrate?

The new system provides:
- **Type safety** and validation
- **IDE autocomplete** support
- **Better error messages**
- **Programmatic configuration** (loops, conditionals, functions)

## Quick Migration

### Old Style (TOML) ❌

```toml
[TRANSPORT]
LAYER = "ETH"

[ETH]
HOST = "192.168.1.100"
PORT = 5555
PROTOCOL = "TCP"
```

### New Style (Python) ✅

```python
# my_config.py
c = get_config()  # noqa

c.Transport.layer = "ETH"
c.Transport.Eth.host = "192.168.1.100"
c.Transport.Eth.port = 5555
c.Transport.Eth.protocol = "TCP"
```

## Common Patterns

### 1. Basic CAN Configuration

**Old (dict):**
```python
config = {
    "TRANSPORT": "CAN",
    "CAN_DRIVER": "vector",
    "CAN_CHANNEL": 0,
    "CAN_ID_MASTER": 1,
    "CAN_ID_SLAVE": 2,
}
```

**New (traitlets):**
```python
c = get_config()

c.Transport.layer = "CAN"
c.Transport.Can.interface = "vector"
c.Transport.Can.channel = 0
c.Transport.Can.can_id_master = 1
c.Transport.Can.can_id_slave = 2
c.Transport.Can.bitrate = 1000000
```

### 2. Ethernet with Seed & Key

**Old:**
```python
config = {
    "TRANSPORT": "ETH",
    "HOST": "localhost",
    "PORT": 5555,
    "PROTOCOL": "TCP",
    "SEED_N_KEY_DLL": "SeedNKeyXcp.dll",
}
```

**New:**
```python
c = get_config()

c.Transport.layer = "ETH"
c.Transport.Eth.host = "localhost"
c.Transport.Eth.port = 5555
c.Transport.Eth.protocol = "TCP"

# Option 1: DLL
c.General.seed_n_key_dll = "SeedNKeyXcp.dll"

# Option 2: Python function (preferred!)
def my_seed_key(resource: int, seed: bytes) -> bytes:
    # Your algorithm here
    return key

c.General.seed_n_key_function = my_seed_key
```

### 3. CAN with Vector Serial Port

**New:**
```python
c = get_config()

c.Transport.layer = "CAN"
c.Transport.Can.interface = "vector"
c.Transport.Can.channel = 0  # or "0", "1", etc.
c.Transport.Can.Vector.serial = 12345  # Hardware serial number (optional)
c.Transport.Can.Vector.app_name = "MyApp"  # Application name from Vector Hardware Config
```

### 4. CAN-FD with MAX_DLC_REQUIRED

**New:**
```python
c = get_config()

c.Transport.layer = "CAN"
c.Transport.Can.interface = "vector"
c.Transport.Can.fd = True
c.Transport.Can.bitrate = 500000
c.Transport.Can.data_bitrate = 2000000
c.Transport.Can.max_dlc_required = True
c.Transport.Can.padding_value = 0xCC
```

## Using Your Config File

### CLI Tools

```bash
# Option 1: Specify config file
xcp-info --config-file my_config.py

# Option 2: Default name (pyxcp_conf.py in current directory)
xcp-info
```

### Python API

```python
from pyxcp.cmdline import ArgumentParser

ap = ArgumentParser(description="My XCP tool", config_file="my_config.py")
with ap.run() as x:
    x.connect()
    # ... your XCP commands
    x.disconnect()
```

### Direct Master Usage

```python
from pyxcp import Master
from pyxcp.config import XcpConfig

config = XcpConfig(
    transport="ETH",
    host="192.168.1.100",
    port=5555,
    protocol="TCP",
)

with Master(config=config) as x:
    x.connect()
    # ...
    x.disconnect()
```

## Generating Config Files

Use the `xcp-profile` tool to generate template configs:

```bash
# Generate full template with all options (commented)
xcp-profile generate --transport ETH --output my_config.py

# Convert old TOML to new Python format
xcp-profile convert old_config.toml --output new_config.py
```

## Troubleshooting

### Error: `AttributeError: 'dict' has no attribute 'general'`

**Cause:** You're passing a dictionary instead of a config file.

**Solution:** Create a `.py` config file (see examples above) and pass it via `--config-file` or as `config_file=` parameter.

### Error: `traitlets.TraitError: Invalid value for Transport.layer`

**Cause:** Invalid transport layer name or typo.

**Valid values:** `'CAN'`, `'ETH'`, `'SXI'`, `'USB'` (must be uppercase)

### Config file not found

**Solution:** Use absolute path or place config in current working directory:

```bash
xcp-info --config-file /path/to/my_config.py
# or
cd /path/to/config && xcp-info --config-file my_config.py
```

## Working Examples

See the `pyxcp/examples/` directory for working configuration files:
- **`conf_eth.py`** - Ethernet configuration with dynamic transport layer selection
- **`conf_cv.py`** - CAN configuration for Vector interfaces
- **`xcphello.py`** - Basic usage example with ArgumentParser

## Additional Resources

- [Configuration Documentation](configuration.rst) - Complete reference
- [Quickstart Guide](quickstart.md) - Getting started examples
- [Troubleshooting Matrix](troubleshooting_matrix.rst) - Common errors and solutions

## Legacy Support

**⚠️ DEPRECATED:** Dictionary-based configs are still supported in pyXCP v0.28.x but will be removed in v0.30.0. Please migrate to the new format.

If you must use legacy configs temporarily:

```python
from pyxcp.config.legacy import ConfigLoader

loader = ConfigLoader("old_config.toml")
config = loader.load()
```

---

**Questions?** File an issue on [GitHub](https://github.com/christoph2/pyxcp/issues) with the `documentation` label.

import warnings
from collections import defaultdict

from traitlets.config.loader import Config

# General
"""
    "LOGLEVEL": (str, False, "WARN"),
    "DISABLE_ERROR_HANDLING": (
        bool,
        False,
        False,
    ),  # Bypass error-handling for performance reasons.
    "SEED_N_KEY_DLL": (str, False, ""),
    "SEED_N_KEY_DLL_SAME_BIT_WIDTH": (bool, False, False),
    "DISCONNECT_RESPONSE_OPTIONAL": (bool, False, False),
================
loglevel = Unicode("WARN").tag(config=True)
disable_error_handling = Bool(False).tag(config=True)
seed_n_key_dll = Unicode(allow_none=True, default_value=None).tag(config=True)
seed_n_key_dll_same_bit_width = Bool(False).tag(config=True)
"""
LEGACY_KEYWORDS = {
    # Transport
    "TRANSPORT": "Transport.layer",
    "CREATE_DAQ_TIMESTAMPS": "Transport.create_daq_timestamps",
    "TIMEOUT": "Transport.timeout",
    "ALIGNMENT": "Transport.alignment",
    # Eth
    "HOST": "Eth.host",
    "PORT": "Eth.port",
    "PROTOCOL": "Eth.protocol",
    "IPV6": "Eth.ipv6",
    "TCP_NODELAY": "Eth.tcp_nodelay",
}

"""
{'General': {'seed_n_key_dll': 'vector_xcp.dll'},
 'Transport': {'CAN': {'bitrate': 10000, 'channel': '123'},
               'alignment': 2,
               'layer': 'USB',
               'timeout': 3.5}}
"""


def nested_update(d: dict, key: str, value) -> dict:
    root, *path, key = key.split(".")
    if path:
        print("???")
    d[root][key] = value


def convert_config(legacy_config: dict) -> Config:
    d = defaultdict(dict)
    for key, value in legacy_config.items():
        item = LEGACY_KEYWORDS.get(key)
        print(key, value)
        nested_update(d=d, key=item, value=value)
    return Config(d)

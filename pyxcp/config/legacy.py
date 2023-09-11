import warnings
from collections import defaultdict

from traitlets.config.loader import Config

LEGACY_KEYWORDS = {
    # General
    "LOGLEVEL": "General.loglevel",
    "DISABLE_ERROR_HANDLING": "General.disable_error_handling",
    "SEED_N_KEY_DLL": "General.seed_n_key_dll",
    "SEED_N_KEY_DLL_SAME_BIT_WIDTH": "General.seed_n_key_dll_same_bit_width",
    "DISCONNECT_RESPONSE_OPTIONAL": "General.disconnect_response_optional",
    # Transport
    "TRANSPORT": "Transport.layer",
    "CREATE_DAQ_TIMESTAMPS": "Transport.create_daq_timestamps",
    "TIMEOUT": "Transport.timeout",
    "ALIGNMENT": "Transport.alignment",
    # Eth
    "HOST": "Transport.Eth.host",
    "PORT": "Transport.Eth.port",
    "PROTOCOL": "Transport.Eth.protocol",
    "IPV6": "Transport.Eth.ipv6",
    "TCP_NODELAY": "Transport.Eth.tcp_nodelay",
    # Can
    "CAN_DRIVER": "Transport.Can.driver",
    "CHANNEL": "Transport.Can.channel",
    "MAX_DLC_REQUIRED": "Transport.Can.max_dlc_required",
    "MAX_CAN_FD_DLC": "Transport.Can.max_can_fd_dlc",
    "PADDING_VALUE": "Transport.Can.padding_value",
    "CAN_USE_DEFAULT_LISTENER": "Transport.Can.use_default_listener",
    "CAN_ID_MASTER": "Transport.Can.can_id_master",
    "CAN_ID_SLAVE": "Transport.Can.can_id_slave",
    "CAN_ID_BROADCAST": "Transport.Can.can_id_broadcast",
    "BITRATE": "Transport.Can.bitrate",
    "RECEIVE_OWN_MESSAGES": "Transport.Can.receive_own_messages",
}


def nested_dict_update(d: dict, key: str, value) -> None:
    root, *path, key = key.split(".")
    sub_dict = d[root]
    for part in path:
        if part not in sub_dict:
            sub_dict[part] = defaultdict(dict)
        sub_dict = sub_dict[part]
    sub_dict[key] = value


def convert_config(legacy_config: dict) -> Config:
    d = defaultdict(dict)
    for key, value in legacy_config.items():
        item = LEGACY_KEYWORDS.get(key)
        print(key, value)
        nested_dict_update(d=d, key=item, value=value)
    return Config(d)

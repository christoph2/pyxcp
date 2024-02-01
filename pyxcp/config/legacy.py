from collections import defaultdict

from traitlets.config import LoggingConfigurable
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
    # Usb
    "SERIAL_NUMBER": "Transport.Usb.serial_number",
    "CONFIGURATION_NUMBER": "Transport.Usb.configuration_number",
    "INTERFACE_NUMBER": "Transport.Usb.interface_number",
    "COMMAND_ENDPOINT_NUMBER": "Transport.Usb.out_ep_number",
    "REPLY_ENDPOINT_NUMBER": "Transport.Usb.in_ep_number",
    "VENDOR_ID": "Transport.Usb.vendor_id",
    "PRODUCT_ID": "Transport.Usb.product_id",
    "LIBRARY": "Transport.Usb.library",
    # Can
    "CAN_DRIVER": "Transport.Can.interface",
    "CHANNEL": "Transport.Can.channel",
    "MAX_DLC_REQUIRED": "Transport.Can.max_dlc_required",
    #   "MAX_CAN_FD_DLC": "Transport.Can.max_can_fd_dlc",
    "PADDING_VALUE": "Transport.Can.padding_value",
    "CAN_USE_DEFAULT_LISTENER": "Transport.Can.use_default_listener",
    # Swap master and slave IDs. (s. https://github.com/christoph2/pyxcp/issues/130)
    "CAN_ID_SLAVE": "Transport.Can.can_id_master",
    "CAN_ID_MASTER": "Transport.Can.can_id_slave",
    "CAN_ID_BROADCAST": "Transport.Can.can_id_broadcast",
    "BITRATE": "Transport.Can.bitrate",
    "RECEIVE_OWN_MESSAGES": "Transport.Can.receive_own_messages",
    "POLL_INTERVAL": "Transport.Can.poll_interval",
    "FD": "Transport.Can.fd",
    "DATA_BITRATE": "Transport.Can.data_bitrate",
    "ACCEPT_VIRTUAL": "Transport.Can.Kvaser.accept_virtual",
    "SJW": "Transport.Can.sjw_abr",
    "TSEG1": "Transport.Can.tseg1_abr",
    "TSEG2": "Transport.Can.tseg2_abr",
    "TTY_BAUDRATE": "Transport.Can.SlCan.ttyBaudrate",
    "UNIQUE_HARDWARE_ID": "Transport.Can.Ixxat.unique_hardware_id",
    "RX_FIFO_SIZE": "Transport.Can.Ixxat.rx_fifo_size",
    "TX_FIFO_SIZE": "Transport.Can.Ixxat.tx_fifo_size",
    "DRIVER_MODE": "Transport.Can.Kvaser.driver_mode",
    "NO_SAMP": "Transport.Can.Kvaser.no_samp",
    "SINGLE_HANDLE": "Transport.Can.Kvaser.single_handle",
    "USE_SYSTEM_TIMESTAMP": "Transport.Can.Neovi.use_system_timestamp",
    "OVERRIDE_LIBRARY_NAME": "Transport.Can.Neovi.override_library_name",
    "BAUDRATE": "Transport.Can.Serial.baudrate",
    "SLEEP_AFTER_OPEN": "Transport.Can.SlCan.sleep_after_open",
    "DEVICE_NUMBER": "Transport.Can.Systec.device_number",
    "RX_BUFFER_ENTRIES": "Transport.Can.Systec.rx_buffer_entries",
    "TX_BUFFER_ENTRIES": "Transport.Can.Systec.tx_buffer_entries",
    "FLAGS": "Transport.Can.Usb2Can.flags",
    "APP_NAME": "Transport.Can.Vector.app_name",
    "RX_QUEUE_SIZE": "Transport.Can.Vector.rx_queue_size",
}


def nested_dict_update(d: dict, key: str, value) -> None:
    root, *path, key = key.split(".")
    sub_dict = d[root]
    for part in path:
        if part not in sub_dict:
            sub_dict[part] = defaultdict(dict)
        sub_dict = sub_dict[part]
    sub_dict[key] = value


def convert_config(legacy_config: dict, logger: LoggingConfigurable) -> Config:
    interface_name = None
    resolv = []
    d = defaultdict(dict)
    for key, value in legacy_config.items():
        key = key.upper()
        item = LEGACY_KEYWORDS.get(key)
        if item is None:
            logger.warning(f"Unknown keyword {key!r} in config file")
            continue
        if key == "CAN_DRIVER":
            value = value.lower()
            interface_name = value
        if key in ("SERIAL", "LOG_ERRORS", "STATE", "RTSCTS"):
            resolv.append((key, value))
        else:
            nested_dict_update(d=d, key=item, value=value)
    for key, value in resolv:
        if key == "SERIAL":
            if interface_name == "neovi":
                d["Transport.Can.Neovi.serial"] = value
            elif interface_name == "vector":
                d["Transport.Can.Vector.serial"] = value
        elif key == "LOG_ERRORS":
            if interface_name == "nican":
                d["Transport.Can.NiCan.log_errors"] = value
        elif key == "STATE":
            if interface_name == "pcan":
                d["Transport.Can.PCan.state"] = value
            elif interface_name == "systec":
                d["Transport.Can.Systec.state"] = value
        elif key == "RTSCTS":
            if interface_name == "serial":
                d["Transport.Can.Serial.rtscts"] = value
            elif interface_name == "slcan":
                d["Transport.Can.SlCan.rtscts"] = value
    return Config(d)

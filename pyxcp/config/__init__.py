#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import json
import sys
import warnings
from pathlib import Path
from pprint import pprint

import toml
from traitlets import Bool
from traitlets import Enum
from traitlets import Float
from traitlets import Int
from traitlets import Integer
from traitlets import List
from traitlets import Unicode
from traitlets.config import Application
from traitlets.config import Configurable
from traitlets.config import Instance
from traitlets.config import SingletonConfigurable
from traitlets.config.loader import Config
from traitlets.config.loader import load_pyconfig_files

from pyxcp.config import legacy


class General(SingletonConfigurable):
    """ """

    loglevel = Unicode("WARN").tag(config=True)
    disable_error_handling = Bool(False).tag(config=True)
    disconnect_response_optional = Bool(False).tag(config=True)
    seed_n_key_dll = Unicode(allow_none=True, default_value=None).tag(config=True)
    seed_n_key_dll_same_bit_width = Bool(False).tag(config=True)

    def __str__(self):
        return str(
            f"General(loglevel: '{self.loglevel}', disable_error_handling: {self.disable_error_handling}, seed_n_key_dll: '{self.seed_n_key_dll}', seed_n_key_dll_same_bit_width: {self.seed_n_key_dll_same_bit_width})"
        )  #


class CanAlystii(SingletonConfigurable):
    baud = Integer(allow_none=True).tag(config=True)
    timing0 = Integer(allow_none=True).tag(config=True)
    timing1 = Integer(allow_none=True).tag(config=True)

    PARAMETER_TO_KW_ARG_MAP = {
        "BAUD": "baud",
        "TIMING0": "timing0",
        "TIMING1": "timing1",
    }

    def __str__(self):
        return str(f"CanAlystii(baud={self.baud}, timing0={self.timing0}, timing1={self.timing1})")


class Etas(SingletonConfigurable):
    fd = Bool(False).tag(config=True)
    data_bitrate = Integer(250000).tag(config=True)

    PARAMETER_TO_KW_ARG_MAP = {
        "fd": "fd",
        "data_bitrate": "data_bitrate",
    }

    def __str__(self):
        return str(f"Etas(fd={self.fd}, data_bitrate={self.data_bitrate})")


"""
candriver/iscan (pyXCP.Transport.CAN.iscan)
-------------------------------------------
    PARAMETER_MAP = {
        #                           Type    Req'd   Default
        "POLL_INTERVAL": (float, False, 0.01),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "POLL_INTERVAL": "poll_interval",
    }
"""


class CAN(SingletonConfigurable):
    driver = Unicode("").tag(config=True)
    channel = Unicode("").tag(config=True)
    max_dlc_required = Bool(False).tag(config=True)
    max_can_fd_dlc = Integer(64).tag(config=True)
    padding_value = Integer(0).tag(config=True)
    use_default_listener = Bool(True).tag(config=True)
    can_id_master = Integer().tag(config=True)
    can_id_slave = Integer().tag(config=True)
    can_id_broadcast = Integer().tag(config=True)
    bitrate = Integer(250000).tag(config=True)
    receive_own_messages = Bool(False).tag(config=True)

    classes = List([CanAlystii, Etas])

    etas = Instance(Etas).tag(config=True)
    canalystii = Instance(CanAlystii).tag(config=True)

    def __init__(self, **kws):
        super().__init__(**kws)
        self.etas = Etas.instance(config=self.config, parent=self)
        self.canalystii = CanAlystii.instance(config=self.config, parent=self)

    def __str__(self):
        # return f"Can(can_driver='{self.can_driver}', channel='{self.channel}', max_dlc_required={self.max_dlc_required}, max_can_fd_dlc={self.max_can_fd_dlc}, padding_value={self.padding_value}), CanAlystii={self.CanAlystii}, Etas={self.Etas}"
        return f"Can(can_driver='{self.can_driver}', channel='{self.channel}', bitrate={self.bitrate}, max_dlc_required={self.max_dlc_required}, max_can_fd_dlc={self.max_can_fd_dlc}, padding_value={self.padding_value})"


class Eth(SingletonConfigurable):
    """
    transport/eth (pyXCP.Transport.Eth)
    -----------------------------------
        "HOST": (str, False, "localhost"),
        "PORT": (int, False, 5555),
        "PROTOCOL": (str, False, "TCP"),
        "IPV6": (bool, False, False),
        "TCP_NODELAY": (bool, False, False),
    """

    host = Unicode("localhost").tag(config=True)
    port = Integer(5555).tag(config=True)
    protocol = Unicode("TCP").tag(config=True)
    ipv6 = Bool(False).tag(config=True)
    tcp_nodelay = Bool(False).tag(config=True)

    def __str__(self):
        return f"Eth(host='{self.host}', port={self.port}, protocol='{self.protocol}', ipv6={self.ipv6}, tcp_nodelay={self.tcp_nodelay})"


class SxI(SingletonConfigurable):
    """
    transport/sxi (pyXCP.Transport.SxI)
    -----------------------------------
        "PORT": (str, False, "COM1"),
        "BITRATE": (int, False, 38400),
        "BYTESIZE": (int, False, 8),
        "PARITY": (str, False, "N"),
        "STOPBITS": (int, False, 1),

    """

    port = Unicode("COM1").tag(config=True)
    bitrate = Integer(38400).tag(config=True)
    bytesize = Integer(8).tag(config=True)
    parity = Unicode("N").tag(config=True)
    stopbits = Integer(1).tag(config=True)

    def __str__(self):
        return f"SxI(port='{self.port}', bitrate={self.bitrate}, bytesize={self.bytesize}, parity='{self.parity}', stopbits={self.stopbits})"


class USB(SingletonConfigurable):
    """
    transport/usb_transport (pyXCP.Transport.USB)
    ---------------------------------------------
        "serial_number": (str, True, ""),
        "configuration_number": (int, True, 1),
        "interface_number": (int, True, 2),
        "command_endpoint_number": (int, True, 0),
        "reply_endpoint_number": (int, True, 1),
    """

    serial_number = Unicode("").tag(config=True)
    configuration_number = Integer(1).tag(config=True)
    interface_number = Integer(2).tag(config=True)
    command_endpoint_number = Integer(0).tag(config=True)
    reply_endpoint_number = Integer(1).tag(config=True)

    def __str__(self):
        return f"USB(serial_number='{self.serial_number}', configuration_number={self.configuration_number}, interface_number={self.interface_number}, command_endpoint_number={self.command_endpoint_number}, reply_endpoint_number={self.reply_endpoint_number})"


class Transport(SingletonConfigurable):
    """ """

    classes = List([CAN, Eth, SxI, USB])

    layer = Enum(["CAN", "ETH", "SXI", "USB"], default_value=None, allow_none=False).tag(config=True)  # Enum
    create_daq_timestamps = Bool(False).tag(config=True)
    timeout = Float(2.0).tag(config=True)
    alignment = Enum([1, 2, 4, 8], default_value=1).tag(config=True)

    can = Instance(CAN).tag(config=True)
    eth = Instance(Eth).tag(config=True)
    sxi = Instance(SxI).tag(config=True)
    usb = Instance(USB).tag(config=True)

    def __init__(self, **kws):
        super().__init__(**kws)
        self.can = CAN.instance(config=self.config, parent=self)
        self.eth = Eth.instance(config=self.config, parent=self)
        self.sxi = SxI.instance(config=self.config, parent=self)
        self.usb = USB.instance(config=self.config, parent=self)

    def __str__(self):
        return str(
            f"Transport(layer='{self.layer}', create_daq_timestamps={self.create_daq_timestamps}, timeout={self.timeout}, alignment={self.alignment}), Can={self.can}, Eth={self.eth}, SxI={self.sxi}, USB={self.usb}"
        )


class PyXCP(Application):
    config_file = Unicode(default_value="pyxcp_conf.py", help="base name of config file").tag(config=True)

    classes = List([General, Transport])

    def initialize(self, argv=None):
        self.parse_command_line(argv)
        if self.config_file:
            self.load_config_file(self.config_file)
            # res = load_pyconfig_files([self.config_file], "c:\csprojects")
            # print("Loaded CFG-File: ", self.config_file, res, self.config)
        print("SC", self.config)
        self.general = General.instance(config=self.config, parent=self)
        self.transport = Transport.instance(parent=self)  # Transport(config=self.config, parent=self)

    def confy(self):
        for klass in app._classes_with_config_traits():
            # pprint(klass.class_config_section())
            if hasattr(klass, "classes"):
                print("KLASEES", klass.classes)
            for name, tr_type in klass._traits.items():
                if isinstance(tr_type, Instance):
                    print(name, tr_type)
            # ctr = klass.class_traits(config=True)

    def __str__(self):
        return f"PyXCP: {self.config.general}"


class Configuration:
    pass


# PyXCP.launch_instance()  # "conf_test.py"
# app = PyXCP.instance()
app = PyXCP()

app.initialize(sys.argv)
app.start()

print(app.config)
print(app.general.loglevel)
# print("TR:", app.config.transport.alignment)
print("TR:", app.transport)
print("CN:", app.transport.can)
print("ET:", app.transport.eth)
print("GN:", app.general)

ci = CAN.instance()

# print("SX:", app.transport.sxi)
# print("US:", app.transport.usb)

# print("etas", app.transport.can.etas)
# print(app.confy())
# print(app.generate_config_file())


def readConfiguration(phile: io.TextIOWrapper):
    pth = Path(phile.name)
    suffix = pth.suffix.lower()
    if suffix == ".py":
        pass
    else:
        if suffix == ".json":
            reader = json
        elif suffix == ".toml":
            reader = toml
        else:
            raise ValueError(f"Unknown file type for config: {suffix}")
        with pth.open("r") as f:
            cfg = reader.loads(f.read())
            if cfg:
                cfg = legacy.convert_config(cfg)
        return cfg

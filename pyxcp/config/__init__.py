#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import json
import sys
import warnings
from pathlib import Path
from pprint import pprint

import can
import toml
from traitlets import Any
from traitlets import Bool
from traitlets import Enum
from traitlets import Float
from traitlets import Int
from traitlets import Integer
from traitlets import List
from traitlets import Unicode
from traitlets import Union
from traitlets.config import Application
from traitlets.config import Configurable
from traitlets.config import Instance
from traitlets.config import SingletonConfigurable
from traitlets.config.loader import Config
from traitlets.config.loader import load_pyconfig_files

from pyxcp.config import legacy


class CanBase:
    has_fd = False
    has_bitrate = True
    has_data_bitrate = False
    has_poll_interval = False
    has_receive_own_messages = False
    has_timing = False

    can_param_map = {
        "sjw_abr": None,
        "tseg1_abr": None,
        "tseg2_abr": None,
        "sjw_dbr": None,
        "tseg1_dbr": None,
        "tseg2_dbr": None,
    }


class CanAlystii(SingletonConfigurable, CanBase):
    """CANalyst-II is a USB to CAN Analyzer device produced by Chuangxin Technology."""

    interface_name = "canalystii"

    has_timing = True

    device = Integer(default_value=None, allow_none=True, help="""Optional USB device number.""").tag(config=True)
    rx_queue_size = Integer(
        default_value=None,
        allow_none=True,
        help="""If set, software received message queue can only grow to this many
messages (for all channels) before older messages are dropped """,
    ).tag(config=True)


class CanTact(SingletonConfigurable, CanBase):
    """Interface for CANtact devices from Linklayer Labs"""

    interface_name = "cantact"

    has_poll_interval = True
    has_timing = True

    monitor = Bool(default_value=False, allow_none=True, help="""If true, operate in listen-only monitoring mode""").tag(
        config=True
    )


class Etas(SingletonConfigurable, CanBase):
    """ETAS"""

    interface_name = "etas"

    has_fd = True
    has_data_bitrate = True
    has_receive_own_messages = True


class Gs_Usb(SingletonConfigurable, CanBase):
    """Geschwister Schneider USB/CAN devices and candleLight USB CAN interfaces."""

    interface_name = "gs_usb"

    index = Integer(
        default_value=None,
        allow_none=True,
        help="""device number if using automatic scan, starting from 0.
If specified, bus/address shall not be provided.""",
    ).tag(config=True)
    bus = Integer(default_value=None, allow_none=True, help="""number of the bus that the device is connected to""").tag(
        config=True
    )
    address = Integer(default_value=None, allow_none=True, help="""address of the device on the bus it is connected to""").tag(
        config=True
    )


class Ics_Neovi(SingletonConfigurable, CanBase):
    """Intrepid Control Systems (ICS) neoVI interfaces."""

    interface_name = "ics_neovi"

    has_fd = True
    has_data_bitrate = True
    has_receive_own_messages = True

    use_system_timestamp = Bool(
        default_value=None, allow_none=True, help="Use system timestamp for can messages instead of the hardware timestamp"
    ).tag(config=True)
    serial = Unicode(
        default_value=None, allow_none=True, help="Serial to connect (optional, will use the first found if not supplied)"
    ).tag(config=True)
    override_library_name = Unicode(
        default_value=None, allow_none=True, help="Absolute path or relative path to the library including filename."
    ).tag(config=True)


class IsCan(SingletonConfigurable, CanBase):
    """Interface for isCAN from Thorsis Technologies GmbH, former ifak system GmbH."""

    interface_name = "iscan"

    has_poll_interval = True


class Ixxat(SingletonConfigurable, CanBase):
    """IXXAT Virtual Communication Interface"""

    interface_name = "ixxat"

    has_fd = True
    has_data_bitrate = True
    has_receive_own_messages = True

    unique_hardware_id = Integer(
        default_value=None,
        allow_none=True,
        help="""UniqueHardwareId to connect (optional, will use the first found if not supplied)""",
    ).tag(config=True)
    extended = Bool(default_value=None, allow_none=True, help="""Enables the capability to use extended IDs.""").tag(config=True)
    rx_fifo_size = Integer(default_value=None, allow_none=True, help="""Receive fifo size""").tag(config=True)
    tx_fifo_size = Integer(default_value=None, allow_none=True, help="""Transmit fifo size""").tag(config=True)
    ssp_dbr = Integer(
        default_value=None,
        allow_none=True,
        help="Secondary sample point (data). Only takes effect with fd and bitrate switch enabled.",
    ).tag(config=True)
    can_param_map = {
        "sjw_abr": "sjw_abr",
        "tseg1_abr": "tseg1_abr",
        "tseg2_abr": "tseg2_abr",
        "sjw_dbr": "sjw_dbr",
        "tseg1_dbr": "tseg1_dbr",
        "tseg2_dbr": "tseg2_dbr",
    }


class Kvaser(SingletonConfigurable, CanBase):
    """Kvaser's CANLib"""

    interface_name = "kvaser"

    has_fd = True
    has_data_bitrate = True
    has_receive_own_messages = True

    can_param_map = {
        "sjw_abr": "sjw",
        "tseg1_abr": "tseg1",
        "tseg2_abr": "tseg2",
    }

    accept_virtual = Bool(default_value=None, allow_none=True, help="If virtual channels should be accepted.").tag(config=True)
    no_samp = Enum(
        [1, 3],
        default_value=None,
        allow_none=True,
        help="""Either 1 or 3. Some CAN controllers can also sample each bit three times.
In this case, the bit will be sampled three quanta in a row,
with the last sample being taken in the edge between TSEG1 and TSEG2.
Three samples should only be used for relatively slow baudrates""",
    ).tag(config=True)
    driver_mode = Bool(default_value=None, allow_none=True, help="Silent or normal.").tag(config=True)
    single_handle = Bool(
        default_value=None,
        allow_none=True,
        help="""Use one Kvaser CANLIB bus handle for both reading and writing.
This can be set if reading and/or writing is done from one thread. """,
    ).tag(config=True)


class NeouSys(SingletonConfigurable, CanBase):
    """Neousys CAN Interface"""

    interface_name = "neousys"

    device = Integer(default_value=None, allow_none=True, help="Device number").tag(config=True)


class NiCan(SingletonConfigurable, CanBase):
    """National Instruments NI-CAN"""

    interface_name = "nican"

    log_errors = Bool(
        default_value=None,
        allow_none=True,
        help="""If True, communication errors will appear as CAN messages with
``is_error_frame`` set to True and ``arbitration_id`` will identify
the error. """,
    ).tag(config=True)


class NixNet(SingletonConfigurable, CanBase):
    """National Instruments NI-XNET"""

    interface_name = "nixnet"

    has_poll_interval = True
    has_receive_own_messages = True
    has_timing = True


class PCan(SingletonConfigurable, CanBase):
    """PCAN Basic API"""

    interface_name = "pcan"

    has_fd = True
    has_timing = True

    can_param_map = {
        "sjw_abr": "nom_sjw",
        "tseg1_abr": "nom_tseg1",
        "tseg2_abr": "nom_tseg2",
        "sjw_dbr": "data_sjw",
        "tseg1_dbr": "data_tseg1",
        "tseg2_dbr": "data_tseg2",
    }

    device_id = Integer(
        default_value=None,
        allow_none=True,
        help="""Select the PCAN interface based on its ID. The device ID is a 8/32bit
value that can be configured for each PCAN device. If you set the
device_id parameter, it takes precedence over the channel parameter.
The constructor searches all connected interfaces and initializes the
first one that matches the parameter value. If no device is found,
an exception is raised.""",
    ).tag(config=True)
    state = Instance(can.bus.BusState, default_value=None, allow_none=True, help="BusState of the channel.").tag(config=True)


#     f_clock = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     f_clock_mhz = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)

#     nom_brp = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     data_brp = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)

#     auto_reset = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class Robotell(SingletonConfigurable, CanBase):
    """ """

    interface_name = "robotell"


#     ttyBaudrate = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     rtscts = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class SeeedStudio(SingletonConfigurable, CanBase):
    """ """

    interface_name = "seeedstudio"


#     timeout = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     baudrate = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     frame_type = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     operation_mode = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class Serial(SingletonConfigurable, CanBase):
    """ """

    interface_name = "serial"

    has_bitrate = False


#     rtscts = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     timeout = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     baudrate = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class SlCan(SingletonConfigurable, CanBase):
    """ """

    interface_name = "slcan"

    has_poll_interval = True


#     ttyBaudrate = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     rtscts = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     timeout = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     btr = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     sleep_after_open = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class SocketCan(SingletonConfigurable, CanBase):
    """ """

    interface_name = "socketcan"

    has_fd = True
    has_bitrate = False
    has_receive_own_messages = True


class SocketCanD(SingletonConfigurable, CanBase):
    """ """

    interface_name = "socketcand"

    has_bitrate = False


#     host = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     port = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class Systec(SingletonConfigurable, CanBase):
    """ """

    interface_name = "systec"

    has_receive_own_messages = True


#     state = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     device_number = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     rx_buffer_entries = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     tx_buffer_entries = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class Udp_Multicast(SingletonConfigurable, CanBase):
    """ """

    interface_name = "udp_multicast"

    has_fd = True
    has_bitrate = False
    has_receive_own_messages = True


#     port = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     hop_limit = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class Usb2Can(SingletonConfigurable, CanBase):
    """ """

    interface_name = "usb2can"


#     flags = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     dll = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     serial.1 = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class Vector(SingletonConfigurable, CanBase):
    """ """

    interface_name = "vector"

    has_fd = True
    has_data_bitrate = True
    has_poll_interval = True
    has_receive_own_messages = True
    has_timing = True


#     sjw_abr = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     tseg1_abr = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     tseg2_abr = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     sjw_dbr = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     tseg1_dbr = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     tseg2_dbr = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     serial.1 = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     rx_queue_size.1 = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     app_name = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class Virtual(SingletonConfigurable, CanBase):
    """ """

    interface_name = "virtual"

    has_bitrate = False
    has_receive_own_messages = True


#     rx_queue_size.1 = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     preserve_timestamps = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)
#     protocol = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


class CAN(SingletonConfigurable):
    interface = Unicode("", help="").tag(config=True)
    channel = Any(help="").tag(config=True)
    max_dlc_required = Bool(False, help="Master to slave frames always to have DLC = MAX_DLC = 8").tag(config=True)
    max_can_fd_dlc = Integer(64, help="").tag(config=True)
    padding_value = Integer(0, help="Fill value, if max_dlc_required == True and DLC < MAX_DLC").tag(config=True)
    use_default_listener = Bool(True, help="").tag(config=True)
    can_id_master = Integer(default_value=None, allow_none=True, help="CAN-ID master -> slave (Bit31= 1: extended identifier)").tag(
        config=True
    )
    can_id_slave = Integer(default_value=None, allow_none=True, help="CAN-ID slave -> master (Bit31= 1: extended identifier)").tag(
        config=True
    )
    can_id_broadcast = Integer(
        default_value=None, allow_none=True, help="Auto detection CAN-ID (Bit31= 1: extended identifier)"
    ).tag(config=True)
    bitrate = Integer(250000, help="CAN bitrate in bits/s (arbitration phase, if CAN FD).").tag(config=True)
    receive_own_messages = Bool(False, help="Enable self-reception of sent messages.").tag(config=True)
    poll_interval = Float(default_value=None, allow_none=True, help="Poll interval in seconds when reading messages.").tag(
        config=True
    )
    fd = Bool(False, help="If CAN-FD frames should be supported.").tag(config=True)
    data_bitrate = Integer(default_value=None, allow_none=True, help="Which bitrate to use for data phase in CAN FD.").tag(
        config=True
    )
    sjw_abr = Integer(
        default_value=None, allow_none=True, help="Bus timing value sample jump width (arbitration, SJW if CAN classic)."
    ).tag(config=True)
    tseg1_abr = Integer(
        default_value=None, allow_none=True, help="Bus timing value tseg1 (arbitration, TSEG1 if CAN classic)."
    ).tag(config=True)
    tseg2_abr = Integer(
        default_value=None, allow_none=True, help="Bus timing value tseg2 (arbitration, TSEG2, if CAN classic)"
    ).tag(config=True)
    sjw_dbr = Integer(default_value=None, allow_none=True, help="Bus timing value sample jump width (data).").tag(config=True)
    tseg1_dbr = Integer(default_value=None, allow_none=True, help="Bus timing value tseg1 (data).").tag(config=True)
    tseg2_dbr = Integer(default_value=None, allow_none=True, help="Bus timing value tseg2 (data).").tag(config=True)
    timing = Union(
        [Instance(can.BitTiming), Instance(can.BitTimingFd)],
        default_value=None,
        allow_none=True,
        help="""Custom bit timing settings.
    (.s https://github.com/hardbyte/python-can/blob/develop/can/bit_timing.py)
    If this parameter is provided, it takes precedence over all other
    timing-related parameters.
    """,
    ).tag(config=True)

    EXCLUDE_FROM_DRIVERS = ()

    classes = List(
        [
            CanAlystii,
            CanTact,
            Etas,
            Gs_Usb,
            Ics_Neovi,
            IsCan,
            Ixxat,
            Kvaser,
            NeouSys,
            NiCan,
            NixNet,
            PCan,
            Robotell,
            SeeedStudio,
            Serial,
            SlCan,
            SocketCan,
            SocketCanD,
            Systec,
            Udp_Multicast,
            Usb2Can,
            Vector,
            Virtual,
        ]
    )

    def __init__(self, **kws):
        super().__init__(**kws)

        self.canalystii = CanAlystii.instance(config=self.config, parent=self)
        self.cantact = CanTact.instance(config=self.config, parent=self)
        self.etas = Etas.instance(config=self.config, parent=self)
        self.gs_usb = Gs_Usb.instance(config=self.config, parent=self)
        self.ics_neovi = Ics_Neovi.instance(config=self.config, parent=self)
        self.iscan = IsCan.instance(config=self.config, parent=self)
        self.ixxat = Ixxat.instance(config=self.config, parent=self)
        self.kvaser = Kvaser.instance(config=self.config, parent=self)
        self.neousys = NeouSys.instance(config=self.config, parent=self)
        self.nican = NiCan.instance(config=self.config, parent=self)
        self.nixnet = NixNet.instance(config=self.config, parent=self)
        self.pcan = PCan.instance(config=self.config, parent=self)
        self.robotell = Robotell.instance(config=self.config, parent=self)
        self.seeedstudio = SeeedStudio.instance(config=self.config, parent=self)
        self.serial = Serial.instance(config=self.config, parent=self)
        self.slcan = SlCan.instance(config=self.config, parent=self)
        self.socketcan = SocketCan.instance(config=self.config, parent=self)
        self.socketcand = SocketCanD.instance(config=self.config, parent=self)
        self.systec = Systec.instance(config=self.config, parent=self)
        self.udp_multicast = Udp_Multicast.instance(config=self.config, parent=self)
        self.usb2can = Usb2Can.instance(config=self.config, parent=self)
        self.vector = Vector.instance(config=self.config, parent=self)
        self.virtual = Virtual.instance(config=self.config, parent=self)

    def __str__(self):
        # return f"Can(can_driver='{self.can_driver}', channel='{self.channel}', max_dlc_required={self.max_dlc_required}, max_can_fd_dlc={self.max_can_fd_dlc}, padding_value={self.padding_value}), CanAlystii={self.CanAlystii}, Etas={self.Etas}"
        return f"Can(can_driver='{self.interface}', channel='{self.channel}', bitrate={self.bitrate}, max_dlc_required={self.max_dlc_required}, max_can_fd_dlc={self.max_can_fd_dlc}, padding_value={self.padding_value})"


class Eth(SingletonConfigurable):
    """ """

    host = Unicode("localhost").tag(config=True)
    port = Integer(5555).tag(config=True)
    protocol = Enum(["TCP", "UDP"], default_value="UDP").tag(config=True)
    ipv6 = Bool(False).tag(config=True)
    tcp_nodelay = Bool(False).tag(config=True)
    bind_to_address = Unicode(default_value=None, allow_none=True, help="Specific local address.").tag(config=True)
    bind_to_port = Integer(default_value=None, allow_none=True, help="Specific local port.").tag(config=True)

    def __str__(self):
        return f"Eth(host='{self.host}', port={self.port}, protocol='{self.protocol}', ipv6={self.ipv6}, tcp_nodelay={self.tcp_nodelay})"


class SxI(SingletonConfigurable):
    """SPI and SCI connections."""

    port = Unicode("COM1", help="").tag(config=True)
    bitrate = Integer(38400, help="").tag(config=True)
    bytesize = Enum([5, 6, 7, 8], default_value=8, help="").tag(config=True)
    parity = Enum(["N", "E", "O", "M", "S"], default_value="N", help="").tag(config=True)
    stopbits = Enum([1, 1.5, 2], default_value=1, help="").tag(config=True)

    """
    -prot<x>     Set the SxI protocol type SYNC = 1,CTR = 2,SYNC+CTR = 3 (Default 0)
    -cs<x>       Set the SxI checksum type LEN+CTR+PACKETS = 1, ONLY PACKETS = 2 (Default 0 no checksum)
    """

    def __str__(self):
        return f"SxI(port='{self.port}', bitrate={self.bitrate}, bytesize={self.bytesize}, parity='{self.parity}', stopbits={self.stopbits})"


class USB(SingletonConfigurable):
    """ """

    serial_number = Unicode("").tag(config=True)
    configuration_number = Integer(1).tag(config=True)
    interface_number = Integer(2).tag(config=True)
    command_endpoint_number = Integer(0).tag(config=True)
    reply_endpoint_number = Integer(1).tag(config=True)
    vendor_id = Integer(0).tag(config=True)
    product_id = Integer(0).tag(config=True)

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


class General(SingletonConfigurable):
    """ """

    loglevel = Unicode("WARN").tag(config=True)
    disable_error_handling = Bool(False).tag(config=True)
    disconnect_response_optional = Bool(False).tag(config=True)
    seed_n_key_dll = Unicode("", allow_none=False).tag(config=True)
    seed_n_key_dll_same_bit_width = Bool(False).tag(config=True)

    def __str__(self):
        return str(
            f"General(loglevel: '{self.loglevel}', disable_error_handling: {self.disable_error_handling}, seed_n_key_dll: '{self.seed_n_key_dll}', seed_n_key_dll_same_bit_width: {self.seed_n_key_dll_same_bit_width})"
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
        for klass in application._classes_with_config_traits():
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


application = PyXCP()

application.initialize(sys.argv)
application.start()


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

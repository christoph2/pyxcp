#!/usr/bin/env python
# -*- coding: utf-8 -*-
import io
import json
import sys
import typing
import warnings
from pathlib import Path

import can
import toml
from traitlets import Any
from traitlets import Bool
from traitlets import Callable
from traitlets import Dict
from traitlets import Enum
from traitlets import Float
from traitlets import Int
from traitlets import Integer
from traitlets import List
from traitlets import TraitError
from traitlets import Unicode
from traitlets import Union
from traitlets.config import Application
from traitlets.config import Configurable
from traitlets.config import Instance
from traitlets.config import SingletonConfigurable
from traitlets.config.loader import Config
from traitlets.config.loader import load_pyconfig_files

from pyxcp.config import legacy

warnings.simplefilter("always")


class CanBase:
    has_fd = False
    has_bitrate = True
    has_data_bitrate = False
    has_poll_interval = False
    has_receive_own_messages = False
    has_timing = False

    OPTIONAL_BASE_PARAMS = (
        "has_fd",
        "has_bitrate",
        "has_data_bitrate",
        "has_poll_interval",
        "has_receive_own_messages",
        "has_timing",
    )

    CAN_PARAM_MAP = {
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


class Neovi(SingletonConfigurable, CanBase):
    """Intrepid Control Systems (ICS) neoVI interfaces."""

    interface_name = "neovi"

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

    CAN_PARAM_MAP = {
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

    CAN_PARAM_MAP = {
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
    has_fd = True

    CAN_PARAM_MAP = {
        "data_bitrate": "fd_bitrate",
    }

    can_termination = Bool(default_value=None, allow_none=True, help="Enable bus termination.")


class PCan(SingletonConfigurable, CanBase):
    """PCAN Basic API"""

    interface_name = "pcan"

    has_fd = True
    has_timing = True

    CAN_PARAM_MAP = {
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
    state = Instance(can.BusState, default_value=None, allow_none=True, help="BusState of the channel.").tag(config=True)

    f_clock = Enum(
        [20000000, 24000000, 30000000, 40000000, 60000000, 80000000],
        default_value=None,
        allow_none=True,
        help="""Ignored if not using CAN-FD.
Pass either f_clock or f_clock_mhz.""",
    ).tag(config=True)
    f_clock_mhz = Enum(
        [20, 24, 30, 40, 60, 80],
        default_value=None,
        allow_none=True,
        help="""Ignored if not using CAN-FD.
Pass either f_clock or f_clock_mhz. """,
    ).tag(config=True)

    nom_brp = Integer(
        min=1,
        max=1024,
        default_value=None,
        allow_none=True,
        help="""Clock prescaler for nominal time quantum.
Ignored if not using CAN-FD.""",
    ).tag(config=True)
    data_brp = Integer(
        min=1,
        max=1024,
        default_value=None,
        allow_none=True,
        help="""Clock prescaler for fast data time quantum.
Ignored if not using CAN-FD.""",
    ).tag(config=True)

    auto_reset = Bool(
        default_value=None,
        allow_none=True,
        help="""Enable automatic recovery in bus off scenario.
Resetting the driver takes ~500ms during which
it will not be responsive.""",
    ).tag(config=True)


class Robotell(SingletonConfigurable, CanBase):
    """Interface for Chinese Robotell compatible interfaces"""

    interface_name = "robotell"

    ttyBaudrate = Integer(
        default_value=None,
        allow_none=True,
        help="""baudrate of underlying serial or usb device
(Ignored if set via the `channel` parameter, e.g. COM7@11500).""",
    ).tag(config=True)
    rtscts = Bool(default_value=None, allow_none=True, help="turn hardware handshake (RTS/CTS) on and off.").tag(config=True)


class SeeedStudio(SingletonConfigurable, CanBase):
    """Seeed USB-Can analyzer interface."""

    interface_name = "seeedstudio"

    timeout = Float(default_value=None, allow_none=True, help="Timeout for the serial device in seconds.").tag(config=True)
    baudrate = Integer(default_value=None, allow_none=True, help="Baud rate of the serial device in bit/s.").tag(config=True)
    frame_type = Enum(["STD", "EXT"], default_value=None, allow_none=True, help="To select standard or extended messages.").tag(
        config=True
    )
    operation_mode = Enum(
        ["normal", "loopback", "silent", "loopback_and_silent"], default_value=None, allow_none=True, help=""" """
    ).tag(config=True)


class Serial(SingletonConfigurable, CanBase):
    """A text based interface."""

    interface_name = "serial"

    has_bitrate = False

    rtscts = Bool(default_value=None, allow_none=True, help="turn hardware handshake (RTS/CTS) on and off.").tag(config=True)
    timeout = Float(default_value=None, allow_none=True, help="Timeout for the serial device in seconds.").tag(config=True)
    baudrate = Integer(default_value=None, allow_none=True, help="Baud rate of the serial device in bit/s.").tag(config=True)


class SlCan(SingletonConfigurable, CanBase):
    """CAN over Serial / SLCAN."""

    interface_name = "slcan"

    has_poll_interval = True

    ttyBaudrate = Integer(default_value=None, allow_none=True, help="Baud rate of the serial device in bit/s.").tag(config=True)
    rtscts = Bool(default_value=None, allow_none=True, help="turn hardware handshake (RTS/CTS) on and off.").tag(config=True)
    timeout = Float(default_value=None, allow_none=True, help="Timeout for the serial device in seconds.").tag(config=True)
    btr = Integer(default_value=None, allow_none=True, help="BTR register value to set custom can speed.").tag(config=True)
    sleep_after_open = Float(
        default_value=None, allow_none=True, help="Time to wait in seconds after opening serial connection."
    ).tag(config=True)


class SocketCan(SingletonConfigurable, CanBase):
    """Linux SocketCAN."""

    interface_name = "socketcan"

    has_fd = True
    has_bitrate = False
    has_receive_own_messages = True

    local_loopback = Bool(
        default_value=None,
        allow_none=True,
        help="""If local loopback should be enabled on this bus.
Please note that local loopback does not mean that messages sent
on a socket will be readable on the same socket, they will only
be readable on other open sockets on the same machine. More info
can be read on the socketcan documentation:
See https://www.kernel.org/doc/html/latest/networking/can.html#socketcan-local-loopback1""",
    ).tag(config=True)


class SocketCanD(SingletonConfigurable, CanBase):
    """Network-to-CAN bridge as a Linux damon."""

    interface_name = "socketcand"

    has_bitrate = False

    host = Unicode(default_value=None, allow_none=True, help=""" """).tag(config=True)
    port = Integer(default_value=None, allow_none=True, help=""" """).tag(config=True)


class Systec(SingletonConfigurable, CanBase):
    """SYSTEC interface"""

    interface_name = "systec"

    has_receive_own_messages = True

    state = Instance(can.BusState, default_value=None, allow_none=True, help="BusState of the channel.").tag(config=True)
    device_number = Integer(min=0, max=254, default_value=None, allow_none=True, help="The device number of the USB-CAN.").tag(
        config=True
    )
    rx_buffer_entries = Integer(
        default_value=None, allow_none=True, help="The maximum number of entries in the receive buffer."
    ).tag(config=True)
    tx_buffer_entries = Integer(
        default_value=None, allow_none=True, help="The maximum number of entries in the transmit buffer."
    ).tag(config=True)


class Udp_Multicast(SingletonConfigurable, CanBase):
    """A virtual interface for CAN communications between multiple processes using UDP over Multicast IP."""

    interface_name = "udp_multicast"

    has_fd = True
    has_bitrate = False
    has_receive_own_messages = True

    port = Integer(default_value=None, allow_none=True, help="The IP port to read from and write to.").tag(config=True)
    hop_limit = Integer(default_value=None, allow_none=True, help="The hop limit in IPv6 or in IPv4 the time to live (TTL).").tag(
        config=True
    )


class Usb2Can(SingletonConfigurable, CanBase):
    """Interface to a USB2CAN Bus."""

    interface_name = "usb2can"

    flags = Integer(
        default_value=None, allow_none=True, help="Flags to directly pass to open function of the usb2can abstraction layer."
    ).tag(config=True)
    dll = Unicode(default_value=None, allow_none=True, help="Path to the DLL with the CANAL API to load.").tag(config=True)
    serial = Unicode(default_value=None, allow_none=True, help="Alias for `channel` that is provided for legacy reasons.").tag(
        config=True
    )


class Vector(SingletonConfigurable, CanBase):
    """Vector Informatik CAN interfaces."""

    interface_name = "vector"

    has_fd = True
    has_data_bitrate = True
    has_poll_interval = True
    has_receive_own_messages = True
    has_timing = True

    CAN_PARAM_MAP = {
        "sjw_abr": "sjw_abr",
        "tseg1_abr": "tseg1_abr",
        "tseg2_abr": "tseg2_abr",
        "sjw_dbr": "sjw_dbr",
        "tseg1_dbr": "tseg1_dbr",
        "tseg2_dbr": "tseg2_dbr",
    }

    serial = Integer(
        default_value=None,
        allow_none=True,
        help="""Serial number of the hardware to be used.
If set, the channel parameter refers to the channels ONLY on the specified hardware.
If set, the `app_name` does not have to be previously defined in
*Vector Hardware Config*.""",
    ).tag(config=True)
    rx_queue_size = Integer(
        min=16, max=32768, default_value=None, allow_none=True, help="Number of messages in receive queue (power of 2)."
    ).tag(config=True)
    app_name = Unicode(default_value=None, allow_none=True, help="Name of application in *Vector Hardware Config*.").tag(
        config=True
    )


class Virtual(SingletonConfigurable, CanBase):
    """ """

    interface_name = "virtual"

    has_bitrate = False
    has_receive_own_messages = True

    rx_queue_size = Integer(
        default_value=None,
        allow_none=True,
        help="""The size of the reception queue. The reception
queue stores messages until they are read. If the queue reaches
its capacity, it will start dropping the oldest messages to make
room for new ones. If set to 0, the queue has an infinite capacity.
Be aware that this can cause memory leaks if messages are read
with a lower frequency than they arrive on the bus. """,
    ).tag(config=True)
    preserve_timestamps = Bool(
        default_value=None,
        allow_none=True,
        help="""If set to True, messages transmitted via
will keep the timestamp set in the
:class:`~can.Message` instance. Otherwise, the timestamp value
will be replaced with the current system time.""",
    ).tag(
        config=True
    )  #     protocol = Type(default_value=None, allow_none=True, help = """ """).tag(config=True)


CAN_INTERFACE_MAP = {
    "canalystii": CanAlystii,
    "cantact": CanTact,
    "etas": Etas,
    "gs_usb": Gs_Usb,
    "iscan": IsCan,
    "ixxat": Ixxat,
    "kvaser": Kvaser,
    "neousys": NeouSys,
    "neovi": Neovi,
    "nican": NiCan,
    "nixnet": NixNet,
    "pcan": PCan,
    "robotell": Robotell,
    "seeedstudio": SeeedStudio,
    "serial": Serial,
    "slcan": SlCan,
    "socketcan": SocketCan,
    "socketcand": SocketCanD,
    "systec": Systec,
    "udp_multicast": Udp_Multicast,
    "usb2can": Usb2Can,
    "vector": Vector,
    "virtual": Virtual,
}


class Can(SingletonConfigurable):
    VALID_INTERFACES = can.interfaces.VALID_INTERFACES

    interface = Enum(VALID_INTERFACES, default_value=None, allow_none=True, help="CAN interface supported by python-can").tag(
        config=True
    )
    channel = Any(
        default_value=None, allow_none=True, help="Channel identification. Expected type and value is backend dependent."
    ).tag(config=True)
    max_dlc_required = Bool(False, help="Master to slave frames always to have DLC = MAX_DLC = 8").tag(config=True)
    max_can_fd_dlc = Integer(64, help="").tag(config=True)
    padding_value = Integer(0, help="Fill value, if max_dlc_required == True and DLC < MAX_DLC").tag(config=True)
    use_default_listener = Bool(True, help="").tag(config=True)
    can_id_master = Integer(allow_none=False, help="CAN-ID master -> slave (Bit31= 1: extended identifier)").tag(config=True)
    can_id_slave = Integer(allow_none=True, help="CAN-ID slave -> master (Bit31= 1: extended identifier)").tag(config=True)
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

    classes = List(
        [
            CanAlystii,
            CanTact,
            Etas,
            Gs_Usb,
            Neovi,
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

        tos = self.class_own_traits()

        if self.parent.layer == "CAN":
            if self.interface is None or self.interface not in self.VALID_INTERFACES:
                raise TraitError(
                    f"CAN interface must be one of {sorted(list(self.VALID_INTERFACES))} not the {type(self.interface).__name__} {self.interface}."
                )
        self.canalystii = CanAlystii.instance(config=self.config, parent=self)
        self.cantact = CanTact.instance(config=self.config, parent=self)
        self.etas = Etas.instance(config=self.config, parent=self)
        self.gs_usb = Gs_Usb.instance(config=self.config, parent=self)
        self.neovi = Neovi.instance(config=self.config, parent=self)
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

    classes = List([Can, Eth, SxI, USB])

    layer = Enum(
        ["CAN", "ETH", "SXI", "USB"], default_value=None, allow_none=False, help="Choose one of the supported XCP transport layers."
    ).tag(
        config=True
    )  # Enum
    create_daq_timestamps = Bool(False, help="Record time of frame reception or set timestamp to 0.").tag(config=True)
    timeout = Float(
        2.0,
        help="""raise `XcpTimeoutError` after `timeout` seconds
if there is no response to a command.""",
    ).tag(config=True)
    alignment = Enum([1, 2, 4, 8], default_value=1).tag(config=True)

    can = Instance(Can).tag(config=True)
    eth = Instance(Eth).tag(config=True)
    sxi = Instance(SxI).tag(config=True)
    usb = Instance(USB).tag(config=True)

    def __init__(self, **kws):
        super().__init__(**kws)
        self.can = Can.instance(config=self.config, parent=self)
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
    seed_n_key_function = Callable(default_value=None, allow_none=True).tag(config=True)

    def __str__(self):
        return str(
            f"General(loglevel: '{self.loglevel}', disable_error_handling: {self.disable_error_handling}, seed_n_key_dll: '{self.seed_n_key_dll}', seed_n_key_dll_same_bit_width: {self.seed_n_key_dll_same_bit_width})"
        )


class PyXCP(Application):
    config_file = Unicode(default_value="pyxcp_conf.py", help="base name of config file").tag(config=True)

    classes = List([General, Transport])

    def initialize(self, argv=None):
        self.parse_command_line(argv)
        self.read_configuration_file()
        self.general = General.instance(config=self.config, parent=self)
        self.transport = Transport.instance(parent=self)

    def read_configuration_file(self):
        pth = Path(self.config_file)
        suffix = pth.suffix.lower()
        if suffix == ".py":
            self.load_config_file(self.config_file)
        else:
            if suffix == ".json":
                reader = json
            elif suffix == ".toml":
                reader = toml
            else:
                raise ValueError(f"Unknown file type for config: {suffix}")
            with pth.open("r") as f:
                warnings.warn("Old-style configuration file. Please user python based configuration.", DeprecationWarning)
                cfg = reader.loads(f.read())
                if cfg:
                    cfg = legacy.convert_config(cfg)
                    self.config = cfg
            return cfg

    flags = Dict(  # type:ignore[assignment]
        dict(
            debug=({"PyXCP": {"log_level": 10}}, "Set loglevel to DEBUG"),
        )
    )

    aliases = Dict(  # type:ignore[assignment]
        dict(
            c="PyXCP.config_file",
            log_level="PyXCP.log_level",
            l="PyXCP.log_level",
        )
    )

    def _iterate_config_class(self, klass, class_names: typing.List[str]) -> None:
        sub_classes = []
        class_path = ".".join(class_names)
        print(
            f"""\n# ------------------------------------------------------------------------------
# {class_path} configuration
# ------------------------------------------------------------------------------""",
            end="\n\n",
        )
        if hasattr(klass, "classes"):
            kkk = klass.classes
            if hasattr(kkk, "default"):
                if class_names[-1] not in ("PyXCP"):
                    sub_classes.extend(kkk.default())
        for name, tr in klass.class_own_traits().items():
            md = tr.metadata
            if md.get("config"):
                help = md.get("help", "").lstrip()
                commented_lines = "\n".join([f"# {line}" for line in help.split("\n")])
                print(f"#{commented_lines}")
                value = tr.default()
                if isinstance(tr, Instance) and tr.__class__.__name__ not in ("Dict",):
                    continue
                if isinstance(tr, Unicode) and value is not None:
                    value = f"'{value}'"
                if isinstance(tr, Enum):
                    print(f"#  Choices: {tr.info()}")
                else:
                    print(f"#  Type: {tr.info()}")
                print(f"#  Default: {value}")

                print(f"#  c.{class_path}.{name} = {value}", end="\n\n")
        if class_names is None:
            class_names = []
        for sub_klass in sub_classes:
            self._iterate_config_class(sub_klass, class_names + [sub_klass.__name__])

    def generate_config_file(self, file_like: io.IOBase, config=None) -> None:
        print("#")
        print("# Configuration file for pyXCP.")
        print("#")
        print("c = get_config()  # noqa", end="\n\n")

        for klass in self._classes_with_config_traits():
            self._iterate_config_class(klass, [klass.__name__])

    def __str__(self):
        return f"PyXCP: {self.config.general}"


class Configuration:
    pass


application = PyXCP()

application.initialize(sys.argv)
application.start()

# print(application.generate_config_file())
# print("*" * 80)

import sys

application.generate_config_file(sys.stdout)

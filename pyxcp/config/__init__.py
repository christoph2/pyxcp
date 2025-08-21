#!/usr/bin/env python
import io
import json
import logging
import sys
import typing
from pathlib import Path

import can
import toml
from rich.logging import RichHandler
from rich.prompt import Confirm
from traitlets import (
    Any,
    Bool,
    Callable,
    Dict,
    Enum,
    Float,
    HasTraits,
    Integer,
    List,
    TraitError,
    Unicode,
    Union,
)
from traitlets.config import Application, Configurable, Instance, default
from traitlets.config.loader import Config

from pyxcp.config import legacy


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


class CanAlystii(Configurable, CanBase):
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


class CanTact(Configurable, CanBase):
    """Interface for CANtact devices from Linklayer Labs"""

    interface_name = "cantact"

    has_poll_interval = True
    has_timing = True

    monitor = Bool(default_value=False, allow_none=True, help="""If true, operate in listen-only monitoring mode""").tag(
        config=True
    )


class Etas(Configurable, CanBase):
    """ETAS"""

    interface_name = "etas"

    has_fd = True
    has_data_bitrate = True
    has_receive_own_messages = True


class Gs_Usb(Configurable, CanBase):
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


class Neovi(Configurable, CanBase):
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


class IsCan(Configurable, CanBase):
    """Interface for isCAN from Thorsis Technologies GmbH, former ifak system GmbH."""

    interface_name = "iscan"

    has_poll_interval = True


class Ixxat(Configurable, CanBase):
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


class Kvaser(Configurable, CanBase):
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
        values=[1, 3],
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


class NeouSys(Configurable, CanBase):
    """Neousys CAN Interface"""

    interface_name = "neousys"

    device = Integer(default_value=None, allow_none=True, help="Device number").tag(config=True)


class NiCan(Configurable, CanBase):
    """National Instruments NI-CAN"""

    interface_name = "nican"

    log_errors = Bool(
        default_value=None,
        allow_none=True,
        help="""If True, communication errors will appear as CAN messages with
``is_error_frame`` set to True and ``arbitration_id`` will identify
the error. """,
    ).tag(config=True)


class NixNet(Configurable, CanBase):
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


class PCan(Configurable, CanBase):
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
    state = Instance(klass=can.BusState, default_value=None, allow_none=True, help="BusState of the channel.").tag(config=True)

    f_clock = Enum(
        values=[20000000, 24000000, 30000000, 40000000, 60000000, 80000000],
        default_value=None,
        allow_none=True,
        help="""Ignored if not using CAN-FD.
Pass either f_clock or f_clock_mhz.""",
    ).tag(config=True)
    f_clock_mhz = Enum(
        values=[20, 24, 30, 40, 60, 80],
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


class Robotell(Configurable, CanBase):
    """Interface for Chinese Robotell compatible interfaces"""

    interface_name = "robotell"

    ttyBaudrate = Integer(
        default_value=None,
        allow_none=True,
        help="""baudrate of underlying serial or usb device
(Ignored if set via the `channel` parameter, e.g. COM7@11500).""",
    ).tag(config=True)
    rtscts = Bool(default_value=None, allow_none=True, help="turn hardware handshake (RTS/CTS) on and off.").tag(config=True)


class SeeedStudio(Configurable, CanBase):
    """Seeed USB-Can analyzer interface."""

    interface_name = "seeedstudio"

    timeout = Float(default_value=None, allow_none=True, help="Timeout for the serial device in seconds.").tag(config=True)
    baudrate = Integer(default_value=None, allow_none=True, help="Baud rate of the serial device in bit/s.").tag(config=True)
    frame_type = Enum(
        values=["STD", "EXT"], default_value=None, allow_none=True, help="To select standard or extended messages."
    ).tag(config=True)
    operation_mode = Enum(
        values=["normal", "loopback", "silent", "loopback_and_silent"], default_value=None, allow_none=True, help=""" """
    ).tag(config=True)


class Serial(Configurable, CanBase):
    """A text based interface."""

    interface_name = "serial"

    has_bitrate = False

    rtscts = Bool(default_value=None, allow_none=True, help="turn hardware handshake (RTS/CTS) on and off.").tag(config=True)
    timeout = Float(default_value=None, allow_none=True, help="Timeout for the serial device in seconds.").tag(config=True)
    baudrate = Integer(default_value=None, allow_none=True, help="Baud rate of the serial device in bit/s.").tag(config=True)


class SlCan(Configurable, CanBase):
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


class SocketCan(Configurable, CanBase):
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


class SocketCanD(Configurable, CanBase):
    """Network-to-CAN bridge as a Linux damon."""

    interface_name = "socketcand"

    has_bitrate = False

    host = Unicode(default_value=None, allow_none=True, help=""" """).tag(config=True)
    port = Integer(default_value=None, allow_none=True, help=""" """).tag(config=True)


class Systec(Configurable, CanBase):
    """SYSTEC interface"""

    interface_name = "systec"

    has_receive_own_messages = True

    state = Instance(klass=can.BusState, default_value=None, allow_none=True, help="BusState of the channel.").tag(config=True)
    device_number = Integer(min=0, max=254, default_value=None, allow_none=True, help="The device number of the USB-CAN.").tag(
        config=True
    )
    rx_buffer_entries = Integer(
        default_value=None, allow_none=True, help="The maximum number of entries in the receive buffer."
    ).tag(config=True)
    tx_buffer_entries = Integer(
        default_value=None, allow_none=True, help="The maximum number of entries in the transmit buffer."
    ).tag(config=True)


class Udp_Multicast(Configurable, CanBase):
    """A virtual interface for CAN communications between multiple processes using UDP over Multicast IP."""

    interface_name = "udp_multicast"

    has_fd = True
    has_bitrate = False
    has_receive_own_messages = True

    port = Integer(default_value=None, allow_none=True, help="The IP port to read from and write to.").tag(config=True)
    hop_limit = Integer(default_value=None, allow_none=True, help="The hop limit in IPv6 or in IPv4 the time to live (TTL).").tag(
        config=True
    )


class Usb2Can(Configurable, CanBase):
    """Interface to a USB2CAN Bus."""

    interface_name = "usb2can"

    flags = Integer(
        default_value=None, allow_none=True, help="Flags to directly pass to open function of the usb2can abstraction layer."
    ).tag(config=True)
    dll = Unicode(default_value=None, allow_none=True, help="Path to the DLL with the CANAL API to load.").tag(config=True)
    serial = Unicode(default_value=None, allow_none=True, help="Alias for `channel` that is provided for legacy reasons.").tag(
        config=True
    )


class Vector(Configurable, CanBase):
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


class CanCustom(Configurable, CanBase):
    """Generic custom CAN interface.

    Enable basic CanBase options so user-provided python-can backends can
    consume common parameters like bitrate, fd, data_bitrate, poll_interval,
    receive_own_messages, and optional timing.
    """

    interface_name = "custom"

    # Allow usage of the basic options from CanBase for custom backends
    has_fd = True
    has_data_bitrate = True
    has_poll_interval = True
    has_receive_own_messages = True
    has_timing = True


class Virtual(Configurable, CanBase):
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
    ).tag(config=True)


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
    "custom": CanCustom,
}


class Can(Configurable):
    VALID_INTERFACES = set(can.interfaces.VALID_INTERFACES)
    VALID_INTERFACES.add("custom")

    interface = Enum(
        values=VALID_INTERFACES, default_value=None, allow_none=True, help="CAN interface supported by python-can"
    ).tag(config=True)
    channel = Any(
        default_value=None, allow_none=True, help="Channel identification. Expected type and value is backend dependent."
    ).tag(config=True)
    max_dlc_required = Bool(False, help="Master to slave frames always to have DLC = MAX_DLC = 8").tag(config=True)
    # max_can_fd_dlc = Integer(64, help="").tag(config=True)
    padding_value = Integer(0, help="Fill value, if max_dlc_required == True and DLC < MAX_DLC").tag(config=True)
    use_default_listener = Bool(True, help="").tag(config=True)
    can_id_master = Integer(allow_none=False, help="CAN-ID master -> slave (Bit31= 1: extended identifier)").tag(
        config=True
    )  # CMD and STIM packets
    can_id_slave = Integer(allow_none=True, help="CAN-ID slave -> master (Bit31= 1: extended identifier)").tag(
        config=True
    )  # RES, ERR, EV, SERV and DAQ packets.
    can_id_broadcast = Integer(
        default_value=None, allow_none=True, help="Auto detection CAN-ID (Bit31= 1: extended identifier)"
    ).tag(config=True)
    daq_identifier = List(trait=Integer(), default_value=[], allow_none=True, help="One CAN identifier per DAQ-list.").tag(
        config=True
    )
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
        trait_types=[Instance(klass=can.BitTiming), Instance(klass=can.BitTimingFd)],
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
            CanCustom,
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

        if self.parent.layer == "CAN":
            if self.interface is None or self.interface not in self.VALID_INTERFACES:
                raise TraitError(
                    f"CAN interface must be one of {sorted(list(self.VALID_INTERFACES))} not the"
                    " {type(self.interface).__name__} {self.interface}."
                )
        self.canalystii = CanAlystii(config=self.config, parent=self)
        self.cancustom = CanCustom(config=self.config, parent=self)
        self.cantact = CanTact(config=self.config, parent=self)
        self.etas = Etas(config=self.config, parent=self)
        self.gs_usb = Gs_Usb(config=self.config, parent=self)
        self.neovi = Neovi(config=self.config, parent=self)
        self.iscan = IsCan(config=self.config, parent=self)
        self.ixxat = Ixxat(config=self.config, parent=self)
        self.kvaser = Kvaser(config=self.config, parent=self)
        self.neousys = NeouSys(config=self.config, parent=self)
        self.nican = NiCan(config=self.config, parent=self)
        self.nixnet = NixNet(config=self.config, parent=self)
        self.pcan = PCan(config=self.config, parent=self)
        self.robotell = Robotell(config=self.config, parent=self)
        self.seeedstudio = SeeedStudio(config=self.config, parent=self)
        self.serial = Serial(config=self.config, parent=self)
        self.slcan = SlCan(config=self.config, parent=self)
        self.socketcan = SocketCan(config=self.config, parent=self)
        self.socketcand = SocketCanD(config=self.config, parent=self)
        self.systec = Systec(config=self.config, parent=self)
        self.udp_multicast = Udp_Multicast(config=self.config, parent=self)
        self.usb2can = Usb2Can(config=self.config, parent=self)
        self.vector = Vector(config=self.config, parent=self)
        self.virtual = Virtual(config=self.config, parent=self)


class Eth(Configurable):
    """Ethernet."""

    host = Unicode("localhost", help="Hostname or IP address of XCP slave.").tag(config=True)
    port = Integer(5555, help="TCP/UDP port to connect.").tag(config=True)
    protocol = Enum(values=["TCP", "UDP"], default_value="UDP", help="").tag(config=True)
    ipv6 = Bool(False, help="Use IPv6 if `True` else IPv4.").tag(config=True)
    tcp_nodelay = Bool(False, help="*** Expert option *** -- Disable Nagle's algorithm if `True`.").tag(config=True)
    bind_to_address = Unicode(default_value=None, allow_none=True, help="Bind to specific local address.").tag(config=True)
    bind_to_port = Integer(default_value=None, allow_none=True, help="Bind to specific local port.").tag(config=True)


class SxI(Configurable):
    """SCI and SPI connections."""

    port = Unicode("COM1", help="Name of communication interface.").tag(config=True)
    bitrate = Integer(38400, help="Connection bitrate").tag(config=True)
    bytesize = Enum(values=[5, 6, 7, 8], default_value=8, help="Size of byte.").tag(config=True)
    parity = Enum(values=["N", "E", "O", "M", "S"], default_value="N", help="Paritybit calculation.").tag(config=True)
    stopbits = Enum(values=[1, 1.5, 2], default_value=1, help="Number of stopbits.").tag(config=True)
    mode = Enum(
        values=[
            "ASYNCH_FULL_DUPLEX_MODE",
            "SYNCH_FULL_DUPLEX_MODE_BYTE",
            "SYNCH_FULL_DUPLEX_MODE_WORD",
            "SYNCH_FULL_DUPLEX_MODE_DWORD",
            "SYNCH_MASTER_SLAVE_MODE_BYTE",
            "SYNCH_MASTER_SLAVE_MODE_WORD",
            "SYNCH_MASTER_SLAVE_MODE_DWORD",
        ],
        default_value="ASYNCH_FULL_DUPLEX_MODE",
        help="Asynchronous (SCI) or synchronous (SPI) communication mode.",
    ).tag(config=True)
    header_format = Enum(
        values=[
            "HEADER_LEN_BYTE",
            "HEADER_LEN_CTR_BYTE",
            "HEADER_LEN_FILL_BYTE",
            "HEADER_LEN_WORD",
            "HEADER_LEN_CTR_WORD",
            "HEADER_LEN_FILL_WORD",
        ],
        default_value="HEADER_LEN_CTR_WORD",
        help="""XCPonSxI header format.
Number of bytes:

                            LEN CTR FILL
______________________________________________________________
HEADER_LEN_BYTE         |   1   X   X
HEADER_LEN_CTR_BYTE     |   1   1   X
HEADER_LEN_FILL_BYTE    |   1   X   1
HEADER_LEN_WORD         |   2   X   X
HEADER_LEN_CTR_WORD     |   2   2   X
HEADER_LEN_FILL_WORD    |   2   X   2
""",
    ).tag(config=True)
    tail_format = Enum(
        values=["NO_CHECKSUM", "CHECKSUM_BYTE", "CHECKSUM_WORD"], default_value="NO_CHECKSUM", help="XCPonSxI tail format."
    ).tag(config=True)
    framing = Bool(False, help="Enable SCI framing mechanism (ESC chars).").tag(config=True)
    esc_sync = Integer(0x01, min=0, max=255, help="SCI framing protocol character SYNC.").tag(config=True)
    esc_esc = Integer(0x00, min=0, max=255, help="SCI framing protocol character ESC.").tag(config=True)


class Usb(Configurable):
    """Universal Serial Bus connections."""

    serial_number = Unicode("", help="Device serial number.").tag(config=True)
    configuration_number = Integer(1, help="USB configuration number.").tag(config=True)
    interface_number = Integer(2, help="USB interface number.").tag(config=True)
    vendor_id = Integer(0, help="USB vendor ID.").tag(config=True)
    product_id = Integer(0, help="USB product ID.").tag(config=True)
    library = Unicode("", help="Absolute path to USB shared library.").tag(config=True)
    header_format = Enum(
        values=[
            "HEADER_LEN_BYTE",
            "HEADER_LEN_CTR_BYTE",
            "HEADER_LEN_FILL_BYTE",
            "HEADER_LEN_WORD",
            "HEADER_LEN_CTR_WORD",
            "HEADER_LEN_FILL_WORD",
        ],
        default_value="HEADER_LEN_CTR_WORD",
        help="",
    ).tag(config=True)
    in_ep_number = Integer(1, help="Ingoing USB reply endpoint number (IN-EP for RES/ERR, DAQ, and EV/SERV).").tag(config=True)
    in_ep_transfer_type = Enum(
        values=["BULK_TRANSFER", "INTERRUPT_TRANSFER"], default_value="BULK_TRANSFER", help="Ingoing: Supported USB transfer types."
    ).tag(config=True)
    in_ep_max_packet_size = Integer(512, help="Ingoing: Maximum packet size of endpoint in bytes.").tag(config=True)
    in_ep_polling_interval = Integer(0, help="Ingoing: Polling interval of endpoint.").tag(config=True)
    in_ep_message_packing = Enum(
        values=["MESSAGE_PACKING_SINGLE", "MESSAGE_PACKING_MULTIPLE", "MESSAGE_PACKING_STREAMING"],
        default_value="MESSAGE_PACKING_SINGLE",
        help="Ingoing: Packing of XCP Messages.",
    ).tag(config=True)
    in_ep_alignment = Enum(
        values=["ALIGNMENT_8_BIT", "ALIGNMENT_16_BIT", "ALIGNMENT_32_BIT", "ALIGNMENT_64_BIT"],
        default_value="ALIGNMENT_8_BIT",
        help="Ingoing: Alignment border.",
    ).tag(config=True)
    in_ep_recommended_host_bufsize = Integer(0, help="Ingoing: Recommended host buffer size.").tag(config=True)
    out_ep_number = Integer(0, help="Outgoing USB command endpoint number (OUT-EP for CMD and STIM).").tag(config=True)
    out_ep_transfer_type = Enum(
        values=["BULK_TRANSFER", "INTERRUPT_TRANSFER"],
        default_value="BULK_TRANSFER",
        help="Outgoing: Supported USB transfer types.",
    ).tag(config=True)
    out_ep_max_packet_size = Integer(512, help="Outgoing: Maximum packet size of endpoint in bytes.").tag(config=True)
    out_ep_polling_interval = Integer(0, help="Outgoing: Polling interval of endpoint.").tag(config=True)
    out_ep_message_packing = Enum(
        values=["MESSAGE_PACKING_SINGLE", "MESSAGE_PACKING_MULTIPLE", "MESSAGE_PACKING_STREAMING"],
        default_value="MESSAGE_PACKING_SINGLE",
        help="Outgoing: Packing of XCP Messages.",
    ).tag(config=True)
    out_ep_alignment = Enum(
        values=["ALIGNMENT_8_BIT", "ALIGNMENT_16_BIT", "ALIGNMENT_32_BIT", "ALIGNMENT_64_BIT"],
        default_value="ALIGNMENT_8_BIT",
        help="Outgoing: Alignment border.",
    ).tag(config=True)
    out_ep_recommended_host_bufsize = Integer(0, help="Outgoing: Recommended host buffer size.").tag(config=True)


class Transport(Configurable):
    """ """

    classes = List([Can, Eth, SxI, Usb])

    layer = Enum(
        values=["CAN", "ETH", "SXI", "USB"],
        default_value=None,
        allow_none=True,
        help="Choose one of the supported XCP transport layers.",
    ).tag(config=True)
    create_daq_timestamps = Bool(True, help="Record time of frame reception or set timestamp to 0.").tag(config=True)
    timeout = Float(
        2.0,
        help="""raise `XcpTimeoutError` after `timeout` seconds
if there is no response to a command.""",
    ).tag(config=True)
    alignment = Enum(values=[1, 2, 4, 8], default_value=1).tag(config=True)

    can = Instance(Can).tag(config=True)
    eth = Instance(Eth).tag(config=True)
    sxi = Instance(SxI).tag(config=True)
    usb = Instance(Usb).tag(config=True)

    def __init__(self, **kws):
        super().__init__(**kws)
        self.can = Can(config=self.config, parent=self)
        self.eth = Eth(config=self.config, parent=self)
        self.sxi = SxI(config=self.config, parent=self)
        self.usb = Usb(config=self.config, parent=self)


class CustomArgs(Configurable):
    """Class to handle custom command-line arguments."""

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self._custom_args = {}

    def add_argument(self, short_opt, long_opt="", dest="", help="", type=None, default=None, action=None):
        """Add a custom argument dynamically.

        This mimics the argparse.ArgumentParser.add_argument method.
        """
        if not dest and long_opt:
            dest = long_opt.lstrip("-").replace("-", "_")

        # Store the argument definition
        self._custom_args[dest] = {
            "short_opt": short_opt,
            "long_opt": long_opt,
            "help": help,
            "type": type,
            "default": default,
            "action": action,
            "value": default,
        }

        # Dynamically add a trait for this argument
        trait_type = Any()
        if type == bool or action == "store_true" or action == "store_false":
            trait_type = Bool(default)
        elif type == int:
            trait_type = Integer(default)
        elif type == float:
            trait_type = Float(default)
        elif type == str:
            trait_type = Unicode(default)

        # Add the trait to this instance
        self.add_trait(dest, trait_type)
        setattr(self, dest, default)

    def update_from_options(self, options):
        """Update trait values from parsed options."""
        for option in options:
            if option.dest and option.dest in self._custom_args:
                if option.default is not None:
                    setattr(self, option.dest, option.default)
                    self._custom_args[option.dest]["value"] = option.default

    def get_args(self):
        """Return an object with all custom arguments as attributes."""

        class Args:
            pass

        args = Args()
        for name, arg_def in self._custom_args.items():
            setattr(args, name, arg_def["value"])

        return args


class General(Configurable):
    """ """

    disable_error_handling = Bool(False, help="Disable XCP error-handler for performance reasons.").tag(config=True)
    disconnect_response_optional = Bool(False, help="Ignore missing response on DISCONNECT request.").tag(config=True)
    connect_retries = Integer(help="Number of CONNECT retries (None for infinite retries).", allow_none=True, default_value=3).tag(
        config=True
    )
    seed_n_key_dll = Unicode("", allow_none=False, help="Dynamic library used for slave resource unlocking.").tag(config=True)
    seed_n_key_dll_same_bit_width = Bool(False, help="").tag(config=True)
    custom_dll_loader = Unicode(allow_none=True, default_value=None, help="Use an custom seed and key DLL loader.").tag(config=True)
    seed_n_key_function = Callable(
        default_value=None,
        allow_none=True,
        help="""Python function used for slave resource unlocking.
Could be used if seed-and-key algorithm is known instead of `seed_n_key_dll`.""",
    ).tag(config=True)
    stim_support = Bool(False, help="").tag(config=True)


class ProfileCreate(Application):
    description = "\nCreate a new profile"

    dest_file = Unicode(default_value=None, allow_none=True, help="destination file name").tag(config=True)
    aliases = Dict(  # type:ignore[assignment]
        dict(
            d="ProfileCreate.dest_file",
            o="ProfileCreate.dest_file",
        )
    )

    def start(self):
        pyxcp = self.parent.parent
        if self.dest_file:
            dest = Path(self.dest_file)
            if dest.exists():
                if not Confirm.ask(f"Destination file [green]{dest.name!r}[/green] already exists. Do you want to overwrite it?"):
                    print("Aborting...")
                    self.exit(1)
            with dest.open("w", encoding="latin1") as out_file:
                pyxcp.generate_config_file(out_file)
        else:
            pyxcp.generate_config_file(sys.stdout)


class ProfileConvert(Application):
    description = "\nConvert legacy configuration file (.json/.toml) to new Python based format."

    config_file = Unicode(help="Name of legacy config file (.json/.toml).", default_value=None, allow_none=False).tag(
        config=True
    )  # default_value="pyxcp_conf.py",

    dest_file = Unicode(default_value=None, allow_none=True, help="destination file name").tag(config=True)

    aliases = Dict(  # type:ignore[assignment]
        dict(
            c="ProfileConvert.config_file",
            d="ProfileConvert.dest_file",
            o="ProfileConvert.dest_file",
        )
    )

    def start(self):
        pyxcp = self.parent.parent
        pyxcp._read_configuration(self.config_file, emit_warning=False)
        if self.dest_file:
            dest = Path(self.dest_file)
            if dest.exists():
                if not Confirm.ask(f"Destination file [green]{dest.name!r}[/green] already exists. Do you want to overwrite it?"):
                    print("Aborting...")
                    self.exit(1)
            with dest.open("w", encoding="latin1") as out_file:
                pyxcp.generate_config_file(out_file)
        else:
            pyxcp.generate_config_file(sys.stdout)


class ProfileApp(Application):
    subcommands = Dict(
        dict(
            create=(ProfileCreate, ProfileCreate.description.splitlines()[0]),
            convert=(ProfileConvert, ProfileConvert.description.splitlines()[0]),
        )
    )

    def start(self):
        if self.subapp is None:
            print(f"No subcommand specified. Must specify one of: {self.subcommands.keys()}")
            print()
            self.print_description()
            self.print_subcommands()
            self.exit(1)
        else:
            self.subapp.start()


class PyXCP(Application):
    description = "pyXCP application"
    config_file = Unicode(default_value="pyxcp_conf.py", help="base name of config file").tag(config=True)

    # Add callout function support
    callout = Callable(default_value=None, allow_none=True, help="Callback function to be called with master and args").tag(
        config=True
    )

    classes = List([General, Transport, CustomArgs])

    subcommands = dict(
        profile=(
            ProfileApp,
            """
            Profile stuff
            """.strip(),
        )
    )

    def start(self):
        if self.subapp:
            self.subapp.start()
            exit(2)
        else:
            has_handlers = logging.getLogger().hasHandlers()
            if has_handlers:
                self.log = logging.getLogger()
                self._read_configuration(self.config_file)
            else:
                self._read_configuration(self.config_file)
                self._setup_logger()
        self.log.debug(f"pyxcp version: {self.version}")

    def _setup_logger(self):
        from pyxcp.types import Command

        # Remove any handlers installed by `traitlets`.
        for hdl in self.log.handlers:
            self.log.removeHandler(hdl)

        # formatter = logging.Formatter(fmt=self.log_format, datefmt=self.log_datefmt)

        keywords = list(Command.__members__.keys()) + ["ARGS", "KWS"]  # Syntax highlight XCP commands and other stuff.
        rich_handler = RichHandler(
            rich_tracebacks=True,
            tracebacks_show_locals=True,
            log_time_format=self.log_datefmt,
            level=self.log_level,
            keywords=keywords,
        )
        # rich_handler.setFormatter(formatter)
        self.log.addHandler(rich_handler)

    def initialize(self, argv=None):
        from pyxcp import __version__ as pyxcp_version

        PyXCP.version = pyxcp_version
        PyXCP.name = Path(sys.argv[0]).name
        self.parse_command_line(argv[1:])

    def _read_configuration(self, file_name: str, emit_warning: bool = True) -> None:
        self.read_configuration_file(file_name, emit_warning)
        self.general = General(config=self.config, parent=self)
        self.transport = Transport(parent=self)
        self.custom_args = CustomArgs(config=self.config, parent=self)

    def read_configuration_file(self, file_name: str, emit_warning: bool = True):
        self.legacy_config: bool = False

        pth = Path(file_name)
        if not pth.exists():
            raise FileNotFoundError(f"Configuration file {file_name!r} does not exist.")
        suffix = pth.suffix.lower()
        if suffix == ".py":
            self.load_config_file(pth)
        else:
            self.legacy_config = True
            if suffix == ".json":
                reader = json
            elif suffix == ".toml":
                reader = toml
            else:
                raise ValueError(f"Unknown file type for config: {suffix}")
            with pth.open("r") as f:
                if emit_warning:
                    self.log.warning(f"Legacy configuration file format ({suffix}), please use Python based configuration.")
                cfg = reader.loads(f.read())
                if cfg:
                    cfg = legacy.convert_config(cfg, self.log)
                    self.config = cfg
            return cfg

    flags = Dict(  # type:ignore[assignment]
        dict(
            debug=({"PyXCP": {"log_level": 10}}, "Set loglevel to DEBUG"),
        )
    )

    @default("log_level")
    def _default_value(self):
        return logging.INFO  # traitlets default is logging.WARN

    aliases = Dict(  # type:ignore[assignment]
        dict(
            c="PyXCP.config_file",  # Application
            log_level="PyXCP.log_level",
            l="PyXCP.log_level",
        )
    )

    def _iterate_config_class(self, klass, class_names: typing.List[str], config, out_file: io.IOBase = sys.stdout) -> None:
        sub_classes = []
        class_path = ".".join(class_names)
        print(
            f"""\n# ------------------------------------------------------------------------------
# {class_path} configuration
# ------------------------------------------------------------------------------""",
            end="\n\n",
            file=out_file,
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
                print(f"#{commented_lines}", file=out_file)
                value = tr.default()
                if isinstance(tr, Instance) and tr.__class__.__name__ not in ("Dict", "List"):
                    continue
                if isinstance(tr, Enum):
                    print(f"#  Choices: {tr.info()}", file=out_file)
                else:
                    print(f"#  Type: {tr.info()}", file=out_file)
                print(f"#  Default: {value!r}", file=out_file)
                if name in config:
                    cfg_value = config[name]
                    print(f"c.{class_path!s}.{name!s} = {cfg_value!r}", end="\n\n", file=out_file)
                else:
                    print(f"#  c.{class_path!s}.{name!s} = {value!r}", end="\n\n", file=out_file)
        if class_names is None:
            class_names = []
        for sub_klass in sub_classes:
            self._iterate_config_class(
                sub_klass, class_names + [sub_klass.__name__], config=config.get(sub_klass.__name__, {}), out_file=out_file
            )

    def generate_config_file(self, file_like: io.IOBase, config=None) -> None:
        print("#", file=file_like)
        print("# Configuration file for pyXCP.", file=file_like)
        print("#", file=file_like)
        print("c = get_config()  # noqa", end="\n\n", file=file_like)

        for klass in self._classes_with_config_traits():
            self._iterate_config_class(
                klass, [klass.__name__], config=self.config.get(klass.__name__, {}) if config is None else {}, out_file=file_like
            )


application: typing.Optional[PyXCP] = None


def create_application(options: typing.Optional[typing.List[typing.Any]] = None, callout=None) -> PyXCP:
    global application
    if options is None:
        options = []
    if application is not None:
        return application
    application = PyXCP()
    application.initialize(sys.argv)
    application.start()

    # Set callout function if provided
    if callout is not None:
        application.callout = callout

    # Process custom arguments if provided
    if options and hasattr(application, "custom_args"):
        application.custom_args.update_from_options(options)

    return application


def get_application(options: typing.Optional[typing.List[typing.Any]] = None, callout=None) -> PyXCP:
    if options is None:
        options = []
    global application
    if application is None:
        application = create_application(options, callout)
    return application


def reset_application() -> None:
    global application
    del application
    application = None

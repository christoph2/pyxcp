#
# Configuration file for pyXCP.
#
c = get_config()  # noqa


# ------------------------------------------------------------------------------
# Application configuration
# ------------------------------------------------------------------------------

## The date format used by logging formatters for %(asctime)s
#  Type: a unicode string
#  Default: '%Y-%m-%d %H:%M:%S'
#  c.Application.log_datefmt = '%Y-%m-%d %H:%M:%S'

## The Logging format template
#  Type: a unicode string
#  Default: '[%(name)s]%(highlevel)s %(message)s'
#  c.Application.log_format = '[%(name)s]%(highlevel)s %(message)s'

## Set the log level by value or name.
#  Choices: any of [0, 10, 20, 30, 40, 50, 'DEBUG', 'INFO', 'WARN', 'ERROR', 'CRITICAL']
#  Default: 30
#  c.Application.log_level = 30

## Configure additional log handlers.
#
#             The default stderr logs handler is configured by the
#             log_level, log_datefmt and log_format settings.
#
#             This configuration can be used to configure additional handlers
#             (e.g. to output the log to a file) or for finer control over the
#             default handlers.
#
#             If provided this should be a logging configuration dictionary, for
#             more information see:
#             https://docs.python.org/3/library/logging.config.html#logging-config-dictschema
#
#             This dictionary is merged with the base logging configuration which
#             defines the following:
#
#             * A logging formatter intended for interactive use called
#               ``console``.
#             * A logging handler that writes to stderr called
#               ``console`` which uses the formatter ``console``.
#             * A logger with the name of this application set to ``DEBUG``
#               level.
#
#             This example adds a new handler that writes to a file:
#
#             .. code-block:: python
#
#                c.Application.logging_config = {
#                    'handlers': {
#                        'file': {
#                            'class': 'logging.FileHandler',
#                            'level': 'DEBUG',
#                            'filename': '<path/to/file>',
#                        }
#                    },
#                    'loggers': {
#                        '<application-name>': {
#                            'level': 'DEBUG',
#                            # NOTE: if you don't list the default "console"
#                            # handler here then it will be disabled
#                            'handlers': ['console', 'file'],
#                        },
#                    }
#                }
#
#
#  Type: a dict
#  Default: {}
#  c.Application.logging_config = {}

## Instead of starting the Application, dump configuration to stdout
#  Type: a boolean
#  Default: False
#  c.Application.show_config = False

## Instead of starting the Application, dump configuration to stdout (as JSON)
#  Type: a boolean
#  Default: False
#  c.Application.show_config_json = False


# ------------------------------------------------------------------------------
# PyXCP configuration
# ------------------------------------------------------------------------------

## base name of config file
#  Type: a unicode string
#  Default: 'pyxcp_conf.py'
#  c.PyXCP.config_file = 'pyxcp_conf.py'


# ------------------------------------------------------------------------------
# General configuration
# ------------------------------------------------------------------------------

## Disable XCP error-handler for performance reasons.
#  Type: a boolean
#  Default: False
#  c.General.disable_error_handling = False

## Ignore missing response on DISCONNECT request.
#  Type: a boolean
#  Default: False
#  c.General.disconnect_response_optional = False

## Dynamic library used for slave resource unlocking.
#  Type: a unicode string
#  Default: ''
#  c.General.seed_n_key_dll = ''

##
#  Type: a boolean
#  Default: False
#  c.General.seed_n_key_dll_same_bit_width = False

## Python function used for slave resource unlocking.
# Could be used if seed-and-key algorithm is known instead of `seed_n_key_dll`.
#  Type: a callable
#  Default: None
#  c.General.seed_n_key_function = None

##
#  Type: a boolean
#  Default: False
#  c.General.stim_support = False


# ------------------------------------------------------------------------------
# Transport configuration
# ------------------------------------------------------------------------------

##
#  Choices: any of [1, 2, 4, 8]
#  Default: 1
#  c.Transport.alignment = 1

##
## Record time of frame reception or set timestamp to 0.
#  Type: a boolean
#  Default: False
#  c.Transport.create_daq_timestamps = False

##
## Choose one of the supported XCP transport layers.
#  Choices: any of ['CAN', 'ETH', 'SXI', 'USB'] or None
#  Default: None
c.Transport.layer = "ETH"

##
## raise `XcpTimeoutError` after `timeout` seconds
# if there is no response to a command.
#  Type: a float
#  Default: 2.0
#  c.Transport.timeout = 2.0

##

# ------------------------------------------------------------------------------
# Transport.Can configuration
# ------------------------------------------------------------------------------

## CAN bitrate in bits/s (arbitration phase, if CAN FD).
#  Type: an int
#  Default: 250000
#  c.Transport.Can.bitrate = 250000

## Auto detection CAN-ID (Bit31= 1: extended identifier)
#  Type: an int
#  Default: None
#  c.Transport.Can.can_id_broadcast = None

## CAN-ID master -> slave (Bit31= 1: extended identifier)
#  Type: an int
#  Default: 0
#  c.Transport.Can.can_id_master = 0

## CAN-ID slave -> master (Bit31= 1: extended identifier)
#  Type: an int
#  Default: 0
#  c.Transport.Can.can_id_slave = 0

## Channel identification. Expected type and value is backend dependent.
#  Type: any value
#  Default: None
#  c.Transport.Can.channel = None

## One CAN identifier per DAQ-list.
#  Type: a list or None
#  Default: []
#  c.Transport.Can.daq_identifier = []

## Which bitrate to use for data phase in CAN FD.
#  Type: an int
#  Default: None
#  c.Transport.Can.data_bitrate = None

## If CAN-FD frames should be supported.
#  Type: a boolean
#  Default: False
#  c.Transport.Can.fd = False

## CAN interface supported by python-can
#  Choices: any of ['etas', 'neousys', 'slcan', 'iscan', 'usb2can', 'pcan', 'ixxat', 'nican', 'nixnet', 'vector', 'systec', 'robotell', 'gs_usb', 'canalystii', 'socketcan', 'serial', 'neovi', 'cantact', 'udp_multicast', 'kvaser', 'socketcand', 'seeedstudio', 'virtual'] or None
#  Default: None
#  c.Transport.Can.interface = None

## Master to slave frames always to have DLC = MAX_DLC = 8
#  Type: a boolean
#  Default: False
#  c.Transport.Can.max_dlc_required = False

## Fill value, if max_dlc_required == True and DLC < MAX_DLC
#  Type: an int
#  Default: 0
#  c.Transport.Can.padding_value = 0

## Poll interval in seconds when reading messages.
#  Type: a float
#  Default: None
#  c.Transport.Can.poll_interval = None

## Enable self-reception of sent messages.
#  Type: a boolean
#  Default: False
#  c.Transport.Can.receive_own_messages = False

## Bus timing value sample jump width (arbitration, SJW if CAN classic).
#  Type: an int
#  Default: None
#  c.Transport.Can.sjw_abr = None

## Bus timing value sample jump width (data).
#  Type: an int
#  Default: None
#  c.Transport.Can.sjw_dbr = None

## Custom bit timing settings.
# (.s https://github.com/hardbyte/python-can/blob/develop/can/bit_timing.py)
# If this parameter is provided, it takes precedence over all other
# timing-related parameters.
#
#  Type: a BitTiming or a BitTimingFd
#  Default: None
#  c.Transport.Can.timing = None

## Bus timing value tseg1 (arbitration, TSEG1 if CAN classic).
#  Type: an int
#  Default: None
#  c.Transport.Can.tseg1_abr = None

## Bus timing value tseg1 (data).
#  Type: an int
#  Default: None
#  c.Transport.Can.tseg1_dbr = None

## Bus timing value tseg2 (arbitration, TSEG2, if CAN classic)
#  Type: an int
#  Default: None
#  c.Transport.Can.tseg2_abr = None

## Bus timing value tseg2 (data).
#  Type: an int
#  Default: None
#  c.Transport.Can.tseg2_dbr = None

##
#  Type: a boolean
#  Default: True
#  c.Transport.Can.use_default_listener = True


# ------------------------------------------------------------------------------
# Transport.Can.CanAlystii configuration
# ------------------------------------------------------------------------------

## Optional USB device number.
#  Type: an int
#  Default: None
#  c.Transport.Can.CanAlystii.device = None

## If set, software received message queue can only grow to this many
# messages (for all channels) before older messages are dropped
#  Type: an int
#  Default: None
#  c.Transport.Can.CanAlystii.rx_queue_size = None


# ------------------------------------------------------------------------------
# Transport.Can.CanTact configuration
# ------------------------------------------------------------------------------

## If true, operate in listen-only monitoring mode
#  Type: a boolean
#  Default: False
#  c.Transport.Can.CanTact.monitor = False


# ------------------------------------------------------------------------------
# Transport.Can.Etas configuration
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Transport.Can.Gs_Usb configuration
# ------------------------------------------------------------------------------

## address of the device on the bus it is connected to
#  Type: an int
#  Default: None
#  c.Transport.Can.Gs_Usb.address = None

## number of the bus that the device is connected to
#  Type: an int
#  Default: None
#  c.Transport.Can.Gs_Usb.bus = None

## device number if using automatic scan, starting from 0.
# If specified, bus/address shall not be provided.
#  Type: an int
#  Default: None
#  c.Transport.Can.Gs_Usb.index = None


# ------------------------------------------------------------------------------
# Transport.Can.Neovi configuration
# ------------------------------------------------------------------------------

## Absolute path or relative path to the library including filename.
#  Type: a unicode string
#  Default: None
#  c.Transport.Can.Neovi.override_library_name = None

## Serial to connect (optional, will use the first found if not supplied)
#  Type: a unicode string
#  Default: None
#  c.Transport.Can.Neovi.serial = None

## Use system timestamp for can messages instead of the hardware timestamp
#  Type: a boolean
#  Default: None
#  c.Transport.Can.Neovi.use_system_timestamp = None


# ------------------------------------------------------------------------------
# Transport.Can.IsCan configuration
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Transport.Can.Ixxat configuration
# ------------------------------------------------------------------------------

## Enables the capability to use extended IDs.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.Ixxat.extended = None

## Receive fifo size
#  Type: an int
#  Default: None
#  c.Transport.Can.Ixxat.rx_fifo_size = None

## Secondary sample point (data). Only takes effect with fd and bitrate switch enabled.
#  Type: an int
#  Default: None
#  c.Transport.Can.Ixxat.ssp_dbr = None

## Transmit fifo size
#  Type: an int
#  Default: None
#  c.Transport.Can.Ixxat.tx_fifo_size = None

## UniqueHardwareId to connect (optional, will use the first found if not supplied)
#  Type: an int
#  Default: None
#  c.Transport.Can.Ixxat.unique_hardware_id = None


# ------------------------------------------------------------------------------
# Transport.Can.Kvaser configuration
# ------------------------------------------------------------------------------

## If virtual channels should be accepted.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.Kvaser.accept_virtual = None

## Silent or normal.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.Kvaser.driver_mode = None

## Either 1 or 3. Some CAN controllers can also sample each bit three times.
# In this case, the bit will be sampled three quanta in a row,
# with the last sample being taken in the edge between TSEG1 and TSEG2.
# Three samples should only be used for relatively slow baudrates
#  Choices: any of [1, 3] or None
#  Default: None
#  c.Transport.Can.Kvaser.no_samp = None

## Use one Kvaser CANLIB bus handle for both reading and writing.
# This can be set if reading and/or writing is done from one thread.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.Kvaser.single_handle = None


# ------------------------------------------------------------------------------
# Transport.Can.NeouSys configuration
# ------------------------------------------------------------------------------

## Device number
#  Type: an int
#  Default: None
#  c.Transport.Can.NeouSys.device = None


# ------------------------------------------------------------------------------
# Transport.Can.NiCan configuration
# ------------------------------------------------------------------------------

## If True, communication errors will appear as CAN messages with
# ``is_error_frame`` set to True and ``arbitration_id`` will identify
# the error.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.NiCan.log_errors = None


# ------------------------------------------------------------------------------
# Transport.Can.NixNet configuration
# ------------------------------------------------------------------------------


# ------------------------------------------------------------------------------
# Transport.Can.PCan configuration
# ------------------------------------------------------------------------------

## Enable automatic recovery in bus off scenario.
# Resetting the driver takes ~500ms during which
# it will not be responsive.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.PCan.auto_reset = None

## Clock prescaler for fast data time quantum.
# Ignored if not using CAN-FD.
#  Type: an int
#  Default: None
#  c.Transport.Can.PCan.data_brp = None

## Select the PCAN interface based on its ID. The device ID is a 8/32bit
# value that can be configured for each PCAN device. If you set the
# device_id parameter, it takes precedence over the channel parameter.
# The constructor searches all connected interfaces and initializes the
# first one that matches the parameter value. If no device is found,
# an exception is raised.
#  Type: an int
#  Default: None
#  c.Transport.Can.PCan.device_id = None

## Ignored if not using CAN-FD.
# Pass either f_clock or f_clock_mhz.
#  Choices: any of [20000000, 24000000, 30000000, 40000000, 60000000, 80000000] or None
#  Default: None
#  c.Transport.Can.PCan.f_clock = None

## Ignored if not using CAN-FD.
# Pass either f_clock or f_clock_mhz.
#  Choices: any of [20, 24, 30, 40, 60, 80] or None
#  Default: None
#  c.Transport.Can.PCan.f_clock_mhz = None

## Clock prescaler for nominal time quantum.
# Ignored if not using CAN-FD.
#  Type: an int
#  Default: None
#  c.Transport.Can.PCan.nom_brp = None

## BusState of the channel.

# ------------------------------------------------------------------------------
# Transport.Can.Robotell configuration
# ------------------------------------------------------------------------------

## turn hardware handshake (RTS/CTS) on and off.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.Robotell.rtscts = None

## baudrate of underlying serial or usb device
# (Ignored if set via the `channel` parameter, e.g. COM7@11500).
#  Type: an int
#  Default: None
#  c.Transport.Can.Robotell.ttyBaudrate = None


# ------------------------------------------------------------------------------
# Transport.Can.SeeedStudio configuration
# ------------------------------------------------------------------------------

## Baud rate of the serial device in bit/s.
#  Type: an int
#  Default: None
#  c.Transport.Can.SeeedStudio.baudrate = None

## To select standard or extended messages.
#  Choices: any of ['STD', 'EXT'] or None
#  Default: None
#  c.Transport.Can.SeeedStudio.frame_type = None

##
#  Choices: any of ['normal', 'loopback', 'silent', 'loopback_and_silent'] or None
#  Default: None
#  c.Transport.Can.SeeedStudio.operation_mode = None

## Timeout for the serial device in seconds.
#  Type: a float
#  Default: None
#  c.Transport.Can.SeeedStudio.timeout = None


# ------------------------------------------------------------------------------
# Transport.Can.Serial configuration
# ------------------------------------------------------------------------------

## Baud rate of the serial device in bit/s.
#  Type: an int
#  Default: None
#  c.Transport.Can.Serial.baudrate = None

## turn hardware handshake (RTS/CTS) on and off.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.Serial.rtscts = None

## Timeout for the serial device in seconds.
#  Type: a float
#  Default: None
#  c.Transport.Can.Serial.timeout = None


# ------------------------------------------------------------------------------
# Transport.Can.SlCan configuration
# ------------------------------------------------------------------------------

## BTR register value to set custom can speed.
#  Type: an int
#  Default: None
#  c.Transport.Can.SlCan.btr = None

## turn hardware handshake (RTS/CTS) on and off.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.SlCan.rtscts = None

## Time to wait in seconds after opening serial connection.
#  Type: a float
#  Default: None
#  c.Transport.Can.SlCan.sleep_after_open = None

## Timeout for the serial device in seconds.
#  Type: a float
#  Default: None
#  c.Transport.Can.SlCan.timeout = None

## Baud rate of the serial device in bit/s.
#  Type: an int
#  Default: None
#  c.Transport.Can.SlCan.ttyBaudrate = None


# ------------------------------------------------------------------------------
# Transport.Can.SocketCan configuration
# ------------------------------------------------------------------------------

## If local loopback should be enabled on this bus.
# Please note that local loopback does not mean that messages sent
# on a socket will be readable on the same socket, they will only
# be readable on other open sockets on the same machine. More info
# can be read on the socketcan documentation:
# See https://www.kernel.org/doc/html/latest/networking/can.html#socketcan-local-loopback1
#  Type: a boolean
#  Default: None
#  c.Transport.Can.SocketCan.local_loopback = None


# ------------------------------------------------------------------------------
# Transport.Can.SocketCanD configuration
# ------------------------------------------------------------------------------

##
#  Type: a unicode string
#  Default: None
#  c.Transport.Can.SocketCanD.host = None

##
#  Type: an int
#  Default: None
#  c.Transport.Can.SocketCanD.port = None


# ------------------------------------------------------------------------------
# Transport.Can.Systec configuration
# ------------------------------------------------------------------------------

## The device number of the USB-CAN.
#  Type: an int
#  Default: None
#  c.Transport.Can.Systec.device_number = None

## The maximum number of entries in the receive buffer.
#  Type: an int
#  Default: None
#  c.Transport.Can.Systec.rx_buffer_entries = None

## BusState of the channel.
## The maximum number of entries in the transmit buffer.
#  Type: an int
#  Default: None
#  c.Transport.Can.Systec.tx_buffer_entries = None


# ------------------------------------------------------------------------------
# Transport.Can.Udp_Multicast configuration
# ------------------------------------------------------------------------------

## The hop limit in IPv6 or in IPv4 the time to live (TTL).
#  Type: an int
#  Default: None
#  c.Transport.Can.Udp_Multicast.hop_limit = None

## The IP port to read from and write to.
#  Type: an int
#  Default: None
#  c.Transport.Can.Udp_Multicast.port = None


# ------------------------------------------------------------------------------
# Transport.Can.Usb2Can configuration
# ------------------------------------------------------------------------------

## Path to the DLL with the CANAL API to load.
#  Type: a unicode string
#  Default: None
#  c.Transport.Can.Usb2Can.dll = None

## Flags to directly pass to open function of the usb2can abstraction layer.
#  Type: an int
#  Default: None
#  c.Transport.Can.Usb2Can.flags = None

## Alias for `channel` that is provided for legacy reasons.
#  Type: a unicode string
#  Default: None
#  c.Transport.Can.Usb2Can.serial = None


# ------------------------------------------------------------------------------
# Transport.Can.Vector configuration
# ------------------------------------------------------------------------------

## Name of application in *Vector Hardware Config*.
#  Type: a unicode string
#  Default: None
#  c.Transport.Can.Vector.app_name = None

## Number of messages in receive queue (power of 2).
#  Type: an int
#  Default: None
#  c.Transport.Can.Vector.rx_queue_size = None

## Serial number of the hardware to be used.
# If set, the channel parameter refers to the channels ONLY on the specified hardware.
# If set, the `app_name` does not have to be previously defined in
# *Vector Hardware Config*.
#  Type: an int
#  Default: None
#  c.Transport.Can.Vector.serial = None


# ------------------------------------------------------------------------------
# Transport.Can.Virtual configuration
# ------------------------------------------------------------------------------

## If set to True, messages transmitted via
# will keep the timestamp set in the
# :class:`~can.Message` instance. Otherwise, the timestamp value
# will be replaced with the current system time.
#  Type: a boolean
#  Default: None
#  c.Transport.Can.Virtual.preserve_timestamps = None

## The size of the reception queue. The reception
# queue stores messages until they are read. If the queue reaches
# its capacity, it will start dropping the oldest messages to make
# room for new ones. If set to 0, the queue has an infinite capacity.
# Be aware that this can cause memory leaks if messages are read
# with a lower frequency than they arrive on the bus.
#  Type: an int
#  Default: None
#  c.Transport.Can.Virtual.rx_queue_size = None


# ------------------------------------------------------------------------------
# Transport.Eth configuration
# ------------------------------------------------------------------------------

## Bind to specific local address.
#  Type: a unicode string
#  Default: None
#  c.Transport.Eth.bind_to_address = None

## Bind to specific local port.
#  Type: an int
#  Default: None
#  c.Transport.Eth.bind_to_port = None

## Hostname or IP address of XCP slave.
#  Type: a unicode string
#  Default: 'localhost'
c.Transport.Eth.host = "localhost"

## Use IPv6 if `True` else IPv4.
#  Type: a boolean
#  Default: False
#  c.Transport.Eth.ipv6 = False

## TCP/UDP port to connect.
#  Type: an int
#  Default: 5555
c.Transport.Eth.port = 5555

##
#  Choices: any of ['TCP', 'UDP']
#  Default: 'UDP'
c.Transport.Eth.protocol = "UDP"

## *** Expert option *** -- Disable Nagle's algorithm if `True`.
#  Type: a boolean
#  Default: False
#  c.Transport.Eth.tcp_nodelay = False


# ------------------------------------------------------------------------------
# Transport.SxI configuration
# ------------------------------------------------------------------------------

## Connection bitrate
#  Type: an int
#  Default: 38400
#  c.Transport.SxI.bitrate = 38400

## Size of byte.
#  Choices: any of [5, 6, 7, 8]
#  Default: 8
#  c.Transport.SxI.bytesize = 8

## SCI framing protocol character ESC.
#  Type: an int
#  Default: 0
#  c.Transport.SxI.esc_esc = 0

## SCI framing protocol character SYNC.
#  Type: an int
#  Default: 1
#  c.Transport.SxI.esc_sync = 1

## Enable SCI framing mechanism (ESC chars).
#  Type: a boolean
#  Default: False
#  c.Transport.SxI.framing = False

## XCPonSxI header format.
# Number of bytes:
#
#                             LEN CTR FILL
# ______________________________________________________________
# HEADER_LEN_BYTE         |   1   X   X
# HEADER_LEN_CTR_BYTE     |   1   1   X
# HEADER_LEN_FILL_BYTE    |   1   X   1
# HEADER_LEN_WORD         |   2   X   X
# HEADER_LEN_CTR_WORD     |   2   2   X
# HEADER_LEN_FILL_WORD    |   2   X   2
#
#  Choices: any of ['HEADER_LEN_BYTE', 'HEADER_LEN_CTR_BYTE', 'HEADER_LEN_FILL_BYTE', 'HEADER_LEN_WORD', 'HEADER_LEN_CTR_WORD', 'HEADER_LEN_FILL_WORD']
#  Default: 'HEADER_LEN_CTR_WORD'
#  c.Transport.SxI.header_format = 'HEADER_LEN_CTR_WORD'

## Asynchronous (SCI) or synchronous (SPI) communication mode.
#  Choices: any of ['ASYNCH_FULL_DUPLEX_MODE', 'SYNCH_FULL_DUPLEX_MODE_BYTE', 'SYNCH_FULL_DUPLEX_MODE_WORD', 'SYNCH_FULL_DUPLEX_MODE_DWORD', 'SYNCH_MASTER_SLAVE_MODE_BYTE', 'SYNCH_MASTER_SLAVE_MODE_WORD', 'SYNCH_MASTER_SLAVE_MODE_DWORD']
#  Default: 'ASYNCH_FULL_DUPLEX_MODE'
#  c.Transport.SxI.mode = 'ASYNCH_FULL_DUPLEX_MODE'

## Paritybit calculation.
#  Choices: any of ['N', 'E', 'O', 'M', 'S']
#  Default: 'N'
#  c.Transport.SxI.parity = 'N'

## Name of communication interface.
#  Type: a unicode string
#  Default: 'COM1'
#  c.Transport.SxI.port = 'COM1'

## Number of stopbits.
#  Choices: any of [1, 1.5, 2]
#  Default: 1
#  c.Transport.SxI.stopbits = 1

## XCPonSxI tail format.
#  Choices: any of ['NO_CHECKSUM', 'CHECKSUM_BYTE', 'CHECKSUM_WORD']
#  Default: 'NO_CHECKSUM'
#  c.Transport.SxI.tail_format = 'NO_CHECKSUM'


# ------------------------------------------------------------------------------
# Transport.Usb configuration
# ------------------------------------------------------------------------------

## USB configuration number.
#  Type: an int
#  Default: 1
#  c.Transport.Usb.configuration_number = 1

##
#  Choices: any of ['HEADER_LEN_BYTE', 'HEADER_LEN_CTR_BYTE', 'HEADER_LEN_FILL_BYTE', 'HEADER_LEN_WORD', 'HEADER_LEN_CTR_WORD', 'HEADER_LEN_FILL_WORD']
#  Default: 'HEADER_LEN_CTR_WORD'
#  c.Transport.Usb.header_format = 'HEADER_LEN_CTR_WORD'

## Ingoing: Alignment border.
#  Choices: any of ['ALIGNMENT_8_BIT', 'ALIGNMENT_16_BIT', 'ALIGNMENT_32_BIT', 'ALIGNMENT_64_BIT']
#  Default: 'ALIGNMENT_8_BIT'
#  c.Transport.Usb.in_ep_alignment = 'ALIGNMENT_8_BIT'

## Ingoing: Maximum packet size of endpoint in bytes.
#  Type: an int
#  Default: 512
#  c.Transport.Usb.in_ep_max_packet_size = 512

## Ingoing: Packing of XCP Messages.
#  Choices: any of ['MESSAGE_PACKING_SINGLE', 'MESSAGE_PACKING_MULTIPLE', 'MESSAGE_PACKING_STREAMING']
#  Default: 'MESSAGE_PACKING_SINGLE'
#  c.Transport.Usb.in_ep_message_packing = 'MESSAGE_PACKING_SINGLE'

## Ingoing USB reply endpoint number (IN-EP for RES/ERR, DAQ, and EV/SERV).
#  Type: an int
#  Default: 1
#  c.Transport.Usb.in_ep_number = 1

## Ingoing: Polling interval of endpoint.
#  Type: an int
#  Default: 0
#  c.Transport.Usb.in_ep_polling_interval = 0

## Ingoing: Recommended host buffer size.
#  Type: an int
#  Default: 0
#  c.Transport.Usb.in_ep_recommended_host_bufsize = 0

## Ingoing: Supported USB transfer types.
#  Choices: any of ['BULK_TRANSFER', 'INTERRUPT_TRANSFER']
#  Default: 'BULK_TRANSFER'
#  c.Transport.Usb.in_ep_transfer_type = 'BULK_TRANSFER'

## USB interface number.
#  Type: an int
#  Default: 2
#  c.Transport.Usb.interface_number = 2

## Absolute path to USB shared library.
#  Type: a unicode string
#  Default: ''
#  c.Transport.Usb.library = ''

## Outgoing: Alignment border.
#  Choices: any of ['ALIGNMENT_8_BIT', 'ALIGNMENT_16_BIT', 'ALIGNMENT_32_BIT', 'ALIGNMENT_64_BIT']
#  Default: 'ALIGNMENT_8_BIT'
#  c.Transport.Usb.out_ep_alignment = 'ALIGNMENT_8_BIT'

## Outgoing: Maximum packet size of endpoint in bytes.
#  Type: an int
#  Default: 512
#  c.Transport.Usb.out_ep_max_packet_size = 512

## Outgoing: Packing of XCP Messages.
#  Choices: any of ['MESSAGE_PACKING_SINGLE', 'MESSAGE_PACKING_MULTIPLE', 'MESSAGE_PACKING_STREAMING']
#  Default: 'MESSAGE_PACKING_SINGLE'
#  c.Transport.Usb.out_ep_message_packing = 'MESSAGE_PACKING_SINGLE'

## Outgoing USB command endpoint number (OUT-EP for CMD and STIM).
#  Type: an int
#  Default: 0
#  c.Transport.Usb.out_ep_number = 0

## Outgoing: Polling interval of endpoint.
#  Type: an int
#  Default: 0
#  c.Transport.Usb.out_ep_polling_interval = 0

## Outgoing: Recommended host buffer size.
#  Type: an int
#  Default: 0
#  c.Transport.Usb.out_ep_recommended_host_bufsize = 0

## Outgoing: Supported USB transfer types.
#  Choices: any of ['BULK_TRANSFER', 'INTERRUPT_TRANSFER']
#  Default: 'BULK_TRANSFER'
#  c.Transport.Usb.out_ep_transfer_type = 'BULK_TRANSFER'

## USB product ID.
#  Type: an int
#  Default: 0
#  c.Transport.Usb.product_id = 0

## Device serial number.
#  Type: a unicode string
#  Default: ''
#  c.Transport.Usb.serial_number = ''

## USB vendor ID.
#  Type: an int
#  Default: 0
#  c.Transport.Usb.vendor_id = 0

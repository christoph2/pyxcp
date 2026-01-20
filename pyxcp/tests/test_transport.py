import selectors
import socket
import struct
import threading
from unittest import mock

import pytest
import serial
from can.bus import BusABC

import pyxcp.transport.base as tr
from pyxcp import types


class MockSocket(mock.MagicMock):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._mock_send = mock.Mock()
        self.data = bytearray()
        self.ctr = 0
        self.has_data_event = threading.Event()
        self.family = socket.AF_INET
        self.type = socket.SOCK_STREAM
        self.proto = 0

    def make_header(self, size: int) -> bytes:
        return struct.pack("<HH", size, self.ctr)

    def make_frame(self, data: bytes) -> bytes:
        return self.make_header(len(data)) + data

    def push_frame(self, frame):
        try:
            self.data.extend(frame)
        except TypeError:
            self.data.extend(bytes.fromhex(frame))
        self.ctr += 1
        self.has_data_event.set()

    def push_packet(self, data):
        try:
            data = bytes.fromhex(data)
        except TypeError:
            pass
        self.push_frame(self.make_frame(data))

    def recv(self, bufsize):
        r = self.data[:bufsize]
        self.data = self.data[bufsize:]
        if not self.data:
            self.has_data_event.clear()
        return bytes(r)

    def recvfrom(self, bufsize):
        return self.recv(bufsize), ("localhost", 5555)

    def select(self, timeout):
        if self.data:
            key = selectors.SelectorKey(self, 0, selectors.EVENT_READ, None)
            return [(key, selectors.EVENT_READ)]
        else:
            res = self.has_data_event.wait(timeout if (timeout is not None and timeout > 0) else 0.1)
            if res or self.data:
                key = selectors.SelectorKey(self, 0, selectors.EVENT_READ, None)
                return [(key, selectors.EVENT_READ)]
            return []

    def fileno(self):
        return 0

    def getsockname(self):
        return ("127.0.0.1", 5555)

    def getpeername(self):
        return ("127.0.0.1", 5555)

    def register(self, fileobj, events, data=None):
        pass

    def unregister(self, fileobj):
        pass

    def send(self, data):
        self._mock_send(data)

    def close(self):
        pass

    def setsockopt(self, level, optname, value):
        pass

    def settimeout(self, value):
        pass

    def connect(self, addr=None):
        pass


def create_mock_serial():
    """Create a mock serial port for testing."""
    mock_serial = mock.MagicMock(spec=serial.Serial)
    mock_serial.portstr = "MOCK_PORT"
    mock_serial.in_waiting = 0
    mock_serial.read.return_value = b""
    mock_serial.is_open = True
    return mock_serial


def create_mock_can_interface():
    """Create a mock CAN interface for testing."""
    mock_can = mock.MagicMock(spec=BusABC)
    mock_can.filters = []
    mock_can.state = "ACTIVE"
    mock_can.recv.return_value = None
    return mock_can


# Mock CAN interface configuration class
class MockCanInterfaceConfig:
    OPTIONAL_BASE_PARAMS = []
    CAN_PARAM_MAP = {}

    @classmethod
    def class_own_traits(cls):
        return {}


def create_config():
    # Create a class to simulate the config structure
    class EthConfig:
        def __init__(self):
            self.host = "localhost"
            self.port = 5555
            self.bind_to_address = ""
            self.bind_to_port = 0
            self.protocol = "UDP"
            self.ipv6 = False
            self.tcp_nodelay = False

    class SxiConfig:
        def __init__(self):
            self.port = "MOCK_PORT"  # This won't be used with the mock
            self.bitrate = 115200
            self.bytesize = 8
            self.parity = "N"
            self.stopbits = 1
            self.mode = "NORMAL"
            self.header_format = "HEADER_LEN_BYTE"
            self.tail_format = "NO_CHECKSUM"
            self.framing = 0
            self.esc_sync = 0
            self.esc_esc = 0

    class CanConfig:
        def __init__(self):
            self.can_id_master = 1
            self.can_id_slave = 2
            self.interface = "MockCanInterface"
            self.channel = "vcan0"
            self.use_default_listener = False  # Don't start the listener
            self.fd = False
            self.max_dlc_required = False
            self.padding_value = 0
            self.timeout = 1.0
            self.daq_identifier = []  # Empty list for DAQ identifiers

            # Add the MockCanInterface attribute
            self.MockCanInterface = MockCanInterfaceConfig()

            # Special flag for testing
            self.testing = True

    class Config:
        def __init__(self):
            # Set attributes directly on the class for BaseTransport.load_config
            self.eth = EthConfig()
            self.sxi = SxiConfig()
            self.can = CanConfig()

            # Set attributes for BaseTransport.__init__
            self.create_daq_timestamps = False
            self.alignment = 1
            self.timeout = 1.0

    return Config()


@mock.patch("pyxcp.transport.can.detect_available_configs")
@mock.patch("pyxcp.transport.can.CAN_INTERFACE_MAP")
def test_factory_works(mock_can_interface_map, mock_detect_configs):
    # Mock the detect_available_configs function to return an empty list
    mock_detect_configs.return_value = []

    # Mock the CAN_INTERFACE_MAP to return an instance of our MockCanInterfaceConfig for any key
    mock_can_interface_map.__getitem__.return_value = MockCanInterfaceConfig()

    config = create_config()
    mock_serial_port = create_mock_serial()
    mock_can_interface = create_mock_can_interface()

    # Test ETH transport
    assert isinstance(tr.create_transport("eth", config=config), tr.BaseTransport)

    # Test SXI transport with mock serial port
    assert isinstance(tr.create_transport("sxi", config=config, transport_layer_interface=mock_serial_port), tr.BaseTransport)

    # Test CAN transport with mock CAN interface
    assert isinstance(
        tr.create_transport("can", config=config, transport_layer_interface=mock_can_interface),
        tr.BaseTransport,
    )


@mock.patch("pyxcp.transport.can.detect_available_configs")
@mock.patch("pyxcp.transport.can.CAN_INTERFACE_MAP")
def test_factory_works_case_insensitive(mock_can_interface_map, mock_detect_configs):
    # Mock the detect_available_configs function to return an empty list
    mock_detect_configs.return_value = []

    # Mock the CAN_INTERFACE_MAP to return an instance of our MockCanInterfaceConfig for any key
    mock_can_interface_map.__getitem__.return_value = MockCanInterfaceConfig()

    config = create_config()
    mock_serial_port = create_mock_serial()
    mock_can_interface = create_mock_can_interface()

    # Test ETH transport with uppercase name
    assert isinstance(tr.create_transport("ETH", config=config), tr.BaseTransport)

    # Test SXI transport with uppercase name and mock serial port
    assert isinstance(tr.create_transport("SXI", config=config, transport_layer_interface=mock_serial_port), tr.BaseTransport)

    # Test CAN transport with uppercase name and mock CAN interface
    assert isinstance(
        tr.create_transport("CAN", config=config, transport_layer_interface=mock_can_interface),
        tr.BaseTransport,
    )


def test_factory_invalid_transport_name_raises():
    with pytest.raises(ValueError):
        tr.create_transport("xCp")


def test_transport_names():
    transports = tr.available_transports()

    assert "can" in transports
    assert "eth" in transports
    assert "sxi" in transports


def test_transport_names_are_lower_case_only():
    transports = tr.available_transports()

    assert "CAN" not in transports
    assert "ETH" not in transports
    assert "SXI" not in transports


def test_transport_classes():
    transports = tr.available_transports()

    assert issubclass(transports.get("can"), tr.BaseTransport)
    assert issubclass(transports.get("eth"), tr.BaseTransport)
    assert issubclass(transports.get("sxi"), tr.BaseTransport)


@mock.patch("pyxcp.transport.eth.socket.socket")
@mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
def test_eth_request(mock_selector, mock_socket):
    ms = MockSocket()
    mock_socket.return_value = ms
    mock_selector.return_value = ms

    config = create_config()
    transport = tr.create_transport("eth", config=config)
    transport.parent = mock.MagicMock()

    ms.push_packet("FF 00")

    ms.recv(1024)

    transport.resQueue.append(b"\xff\x00")

    response = transport.request(types.Command.CONNECT, 0x00)

    # request() returns xcpPDU[1:], so for b"\xFF\x00" it should return b"\x00"
    assert response == b"\x00"
    # Header is 4 bytes (len=2, ctr=0), then CONNECT(0xFF) and mode(0x00)
    ms._mock_send.assert_called_with(b"\x02\x00\x00\x00\xff\x00")
    transport.close()


@mock.patch("pyxcp.transport.eth.socket.socket")
@mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
def test_eth_request_timeout(mock_selector, mock_socket):
    ms = MockSocket()
    mock_socket.return_value = ms
    mock_selector.return_value = ms

    config = create_config()
    config.timeout = 0.1
    transport = tr.create_transport("eth", config=config)
    transport.parent = mock.MagicMock()

    with pytest.raises(types.XcpTimeoutError):
        transport.request(types.Command.CONNECT, 0x00)


def test_eth_initialization_with_custom_interface():
    ms = MockSocket()
    config = create_config()
    transport = tr.create_transport("eth", config=config, transport_layer_interface=ms)
    assert transport.transport_layer_interface == ms


@mock.patch("pyxcp.transport.can.detect_available_configs")
@mock.patch("pyxcp.transport.can.CAN_INTERFACE_MAP")
def test_can_request(mock_can_interface_map, mock_detect_configs):
    mock_detect_configs.return_value = []
    mock_can_interface_map.__getitem__.return_value = MockCanInterfaceConfig()

    mock_can = create_mock_can_interface()
    config = create_config()
    transport = tr.create_transport("can", config=config, transport_layer_interface=mock_can)
    transport.parent = mock.MagicMock()

    # The issue was that PythonCanWrapper expects to be connected to set up its can_interface.
    # In the mock case, it should already be set if passed in, but the Can class
    # wraps it in a PythonCanWrapper which might not be fully initialized.
    # Actually, if transport_layer_interface is provided, it's used.

    # Fix for: AttributeError: 'PythonCanWrapper' object has no attribute 'can_interface'
    # In Can.__init__:
    # if transport_layer_interface:
    #    self.can_interface = PythonCanWrapper(self, self.config.interface, self.config.timeout, transport_layer_interface=transport_layer_interface)
    #    self.can_interface.connect()
    # In PythonCanWrapper.connect():
    # if self.transport_layer_interface:
    #     self.can_interface = self.transport_layer_interface

    transport.resQueue.append(b"\xff\x00")

    # We must call connect() to initialize PythonCanWrapper.can_interface
    transport.can_interface.connect()

    response = transport.request(types.Command.CONNECT, 0x00)
    assert response == b"\x00"

    # Verify send was called on mock_can
    mock_can.send.assert_called()
    sent_msg = mock_can.send.call_args[0][0]
    assert sent_msg.arbitration_id == config.can.can_id_master
    assert sent_msg.data == b"\xff\x00"


@mock.patch("pyxcp.transport.eth.socket.socket")
@mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
def test_request_optional_response(mock_selector, mock_socket):
    ms = MockSocket()
    mock_socket.return_value = ms
    mock_selector.return_value = ms

    config = create_config()
    transport = tr.create_transport("eth", config=config)
    transport.parent = mock.MagicMock()

    # Test with response
    transport.resQueue.append(b"\xff\x00")
    response = transport.request_optional_response(types.Command.CONNECT, 0x00)
    assert response == b"\x00"

    # Test without response (should return None on timeout if ignore_timeout=True)
    # BaseTransport.request_optional_response calls _request_internal(cmd, True, *data)
    # which returns None if get() raises EmptyFrameError.
    response = transport.request_optional_response(types.Command.CONNECT, 0x00)
    assert response is None
    transport.close()


@mock.patch("pyxcp.transport.eth.socket.socket")
@mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
def test_block_receive(mock_selector, mock_socket):
    ms = MockSocket()
    mock_socket.return_value = ms
    mock_selector.return_value = ms

    config = create_config()
    transport = tr.create_transport("eth", config=config)

    # block_receive(length_required) pops from resQueue and concatenates [1:]
    transport.resQueue.append(b"\xff\x01\x02")
    transport.resQueue.append(b"\xff\x03\x04")

    response = transport.block_receive(4)
    assert response == b"\x01\x02\x03\x04"
    transport.close()


@mock.patch("pyxcp.transport.eth.socket.socket")
@mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
def test_block_receive_timeout(mock_selector, mock_socket):
    ms = MockSocket()
    mock_socket.return_value = ms
    mock_selector.return_value = ms

    config = create_config()
    config.timeout = 0.1
    transport = tr.create_transport("eth", config=config)

    with pytest.raises(types.XcpTimeoutError):
        transport.block_receive(1)
    transport.close()


def test_parse_header_format():
    assert tr.parse_header_format("HEADER_LEN_BYTE") == (1, 0, 0)
    assert tr.parse_header_format("HEADER_LEN_CTR_BYTE") == (1, 1, 0)
    assert tr.parse_header_format("HEADER_LEN_FILL_BYTE") == (1, 0, 1)
    assert tr.parse_header_format("HEADER_LEN_WORD") == (2, 0, 0)
    assert tr.parse_header_format("HEADER_LEN_CTR_WORD") == (2, 2, 0)
    assert tr.parse_header_format("HEADER_LEN_FILL_WORD") == (2, 0, 2)
    with pytest.raises(ValueError):
        tr.parse_header_format("INVALID")


@mock.patch("pyxcp.transport.eth.socket.socket")
@mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
def test_eth_process_response_daq(mock_selector, mock_socket):
    ms = MockSocket()
    mock_socket.return_value = ms
    mock_selector.return_value = ms

    config = create_config()
    transport = tr.create_transport("eth", config=config)

    # DAQ packet (PID < 0xFC)
    daq_packet = b"\x00\x11\x22"
    transport.process_response(daq_packet, len(daq_packet), 0, 123456789)

    # DAQ packets should not go to resQueue but should be handled by the acquisition policy
    assert len(transport.resQueue) == 0
    transport.close()


@mock.patch("pyxcp.transport.eth.socket.socket")
@mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
def test_eth_process_response_serv(mock_selector, mock_socket):
    ms = MockSocket()
    mock_socket.return_value = ms
    mock_selector.return_value = ms

    config = create_config()
    transport = tr.create_transport("eth", config=config)

    # SERV packet (PID == 0xFC)
    serv_packet = b"\xfc\x01\x02"
    transport.process_response(serv_packet, len(serv_packet), 0, 123456789)

    # SERV packets currently don't go to resQueue either in base.py (only >= 0xFE)
    assert len(transport.resQueue) == 0
    transport.close()


@mock.patch("pyxcp.transport.eth.socket.socket")
@mock.patch("pyxcp.transport.eth.selectors.DefaultSelector")
def test_eth_process_response_event(mock_selector, mock_socket):
    ms = MockSocket()
    mock_socket.return_value = ms
    mock_selector.return_value = ms

    config = create_config()
    transport = tr.create_transport("eth", config=config)

    # EVENT packet (PID == 0xFD)
    # EV_CMD_PENDING is 0x05 for this version of XCP/PyXCP
    # PID(FD) + EventCode(05)
    event_packet = b"\xfd\x05"  # EV_CMD_PENDING
    transport.process_response(event_packet, len(event_packet), 0, 123456789)

    assert transport.timer_restart_event.is_set()
    transport.close()

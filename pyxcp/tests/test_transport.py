from unittest import mock

import pytest
import serial
from can.bus import BusABC

import pyxcp.transport.base as tr


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
            self.tail_format = ""
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
    # assert isinstance(
    #     tr.create_transport("can", config=config, transport_layer_interface=mock_can_interface),
    #     tr.BaseTransport,
    # )


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
    # assert isinstance(
    #     tr.create_transport("CAN", config=config, transport_layer_interface=mock_can_interface),
    #     tr.BaseTransport,
    # )


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

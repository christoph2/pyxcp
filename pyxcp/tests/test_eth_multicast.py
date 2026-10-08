from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pyxcp.cpp_ext.cpp_ext import init_networking
from pyxcp.transport import eth as eth_module
from pyxcp.transport.eth import Eth
from pyxcp.transport.transport_ext import EthMulticastSender


def make_eth() -> Eth:
    transport = Eth.__new__(Eth)
    transport.config = SimpleNamespace(protocol="UDP", ipv6=True)
    transport.logger = Mock()
    transport._multicast_sender = Mock()
    transport._multicast_sender.enabled = False
    transport.framing = Mock()
    transport.framing.prepare_request.return_value = b"request"
    return transport


@pytest.mark.parametrize(
    ("cluster_id", "address"),
    [(0, "239.255.0.0"), (1, "239.255.0.1"), (0xFFFF, "239.255.255.255")],
)
def test_cluster_id_to_multicast_address(cluster_id, address):
    assert Eth.cluster_id_to_multicast_address(cluster_id) == address


@pytest.mark.parametrize("cluster_id", [-1, 0x10000, True, "1", 10**100])
def test_cluster_id_to_multicast_address_rejects_invalid_id(cluster_id):
    with pytest.raises(ValueError, match="cluster_id"):
        Eth.cluster_id_to_multicast_address(cluster_id)


def test_enable_multicast_uses_native_ipv4_sender():
    transport = make_eth()

    transport.enable_multicast(0x0102)

    transport._multicast_sender.enable.assert_called_once_with()
    transport.logger.info.assert_called_once_with("Multicast enabled: cluster_id=0x0102 -> 239.255.1.2:5557")


def test_enable_multicast_propagates_native_setup_error():
    transport = make_eth()
    transport._multicast_sender.enable.side_effect = OSError("setsockopt failed")

    with pytest.raises(OSError, match="setsockopt failed"):
        transport.enable_multicast()

    assert not transport._multicast_sender.enabled


@pytest.mark.parametrize(
    ("cluster_id", "counter"),
    [(-1, 0), (0x10000, 0), (1, -1), (1, 0x100), (True, 0), (1, False)],
)
def test_send_multicast_rejects_out_of_range_values(cluster_id, counter):
    transport = make_eth()
    with pytest.raises(ValueError):
        transport.send_multicast(cluster_id, counter)
    transport._multicast_sender.enable.assert_not_called()


def test_native_packet_builder_encodes_little_endian_cluster_id():
    framing = Mock()
    framing.prepare_request.return_value = b"request"

    packet = EthMulticastSender.build_packet(framing, 0x0102, 0xFE)

    assert packet == b"request"
    framing.prepare_request.assert_called_once_with(0xF2, 0xFA, 0x02, 0x01, 0xFE)


def test_native_multicast_sender_lifecycle():
    init_networking()
    sender = EthMulticastSender()

    sender.enable()
    assert sender.enabled
    sender.enable()
    sender.disable()
    assert not sender.enabled
    sender.disable()


def test_send_multicast_uses_native_sender():
    transport = make_eth()
    transport._multicast_sender.enabled = True

    transport.send_multicast(0x0102, 0xFE)

    transport._multicast_sender.send.assert_called_once_with(transport.framing, 0x0102, 0xFE, eth_module.DEFAULT_XCP_MULTICAST_PORT)


def test_send_multicast_enables_sender_on_demand():
    transport = make_eth()

    def enable_sender():
        transport._multicast_sender.enabled = True

    transport._multicast_sender.enable.side_effect = enable_sender
    transport.send_multicast(0x0102, 0xFE)

    transport._multicast_sender.enable.assert_called_once_with()
    transport._multicast_sender.send.assert_called_once_with(transport.framing, 0x0102, 0xFE, eth_module.DEFAULT_XCP_MULTICAST_PORT)


def test_close_connection_disables_multicast_even_if_backend_close_fails():
    transport = make_eth()
    transport._multicast_sender.enabled = True
    backend = Mock()
    backend.close_connection.side_effect = OSError("backend close failed")
    transport._backend = backend

    with pytest.raises(OSError, match="backend close failed"):
        transport.close_connection()

    transport._multicast_sender.disable.assert_called_once_with()
    backend.close_connection.side_effect = None

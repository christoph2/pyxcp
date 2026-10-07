from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from pyxcp.transport import eth as eth_module
from pyxcp.transport.eth import Eth


def make_eth() -> Eth:
    transport = Eth.__new__(Eth)
    transport.config = SimpleNamespace(protocol="UDP", ipv6=True)
    transport.logger = Mock()
    transport._multicast_sock = None
    transport._multicast_enabled = False
    transport.framing = Mock()
    transport.framing.prepare_request.return_value = b"request"
    return transport


@pytest.mark.parametrize(
    ("cluster_id", "address"),
    [(0, "239.255.0.0"), (1, "239.255.0.1"), (0xFFFF, "239.255.255.255")],
)
def test_cluster_id_to_multicast_address(cluster_id, address):
    assert Eth.cluster_id_to_multicast_address(cluster_id) == address


@pytest.mark.parametrize("cluster_id", [-1, 0x10000, True, "1"])
def test_cluster_id_to_multicast_address_rejects_invalid_id(cluster_id):
    with pytest.raises(ValueError, match="cluster_id"):
        Eth.cluster_id_to_multicast_address(cluster_id)


def test_enable_multicast_uses_ipv4_for_xcp_group(monkeypatch):
    transport = make_eth()
    multicast_sock = Mock()
    create_socket = Mock(return_value=multicast_sock)
    monkeypatch.setattr(eth_module.socket, "socket", create_socket)

    transport.enable_multicast(0x0102)

    create_socket.assert_called_once_with(eth_module.socket.AF_INET, eth_module.socket.SOCK_DGRAM, eth_module.socket.IPPROTO_UDP)
    multicast_sock.setsockopt.assert_called_once_with(eth_module.socket.IPPROTO_IP, eth_module.socket.IP_MULTICAST_TTL, 2)
    assert transport._multicast_sock is multicast_sock
    assert transport._multicast_enabled


def test_enable_multicast_closes_socket_and_propagates_setup_error(monkeypatch):
    transport = make_eth()
    multicast_sock = Mock()
    multicast_sock.setsockopt.side_effect = OSError("setsockopt failed")
    monkeypatch.setattr(eth_module.socket, "socket", Mock(return_value=multicast_sock))

    with pytest.raises(OSError, match="setsockopt failed"):
        transport.enable_multicast()

    multicast_sock.close.assert_called_once_with()
    assert transport._multicast_sock is None
    assert not transport._multicast_enabled


@pytest.mark.parametrize(
    ("cluster_id", "counter"),
    [(-1, 0), (0x10000, 0), (1, -1), (1, 0x100), (True, 0), (1, False)],
)
def test_send_multicast_rejects_out_of_range_values(cluster_id, counter):
    transport = make_eth()
    with pytest.raises(ValueError):
        transport.send_multicast(cluster_id, counter)


def test_send_multicast_encodes_little_endian_cluster_id():
    transport = make_eth()
    multicast_sock = Mock()
    transport._multicast_sock = multicast_sock
    transport._multicast_enabled = True

    transport.send_multicast(0x0102, 0xFE)

    transport.framing.prepare_request.assert_called_once_with(eth_module.types.Command.TRANSPORT_LAYER_CMD, 0xFA, 0x02, 0x01, 0xFE)
    multicast_sock.sendto.assert_called_once_with(b"request", ("239.255.1.2", eth_module.DEFAULT_XCP_MULTICAST_PORT))


def test_close_connection_closes_multicast_even_if_backend_close_fails():
    transport = make_eth()
    multicast_sock = Mock()
    backend = Mock()
    backend.close_connection.side_effect = OSError("backend close failed")
    transport._backend = backend
    transport._multicast_sock = multicast_sock
    transport._multicast_enabled = True

    with pytest.raises(OSError, match="backend close failed"):
        transport.close_connection()

    multicast_sock.close.assert_called_once_with()
    assert transport._multicast_sock is None
    assert not transport._multicast_enabled
    backend.close_connection.side_effect = None

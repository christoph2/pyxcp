from pyxcp import types
from pyxcp.scripts.xcp_discovery import XcpEthDiscovery


def test_frame_it_len_includes_command_byte():
    disc = XcpEthDiscovery()
    payload = bytes([types.TransportLayerCommands.GET_SLAVE_ID]) + bytes(19)
    frame = disc.frame_it(types.Command.TRANSPORT_LAYER_CMD, *payload)
    assert int.from_bytes(frame[:2], "little") == len(frame) - 4 == 21
    counter, body = XcpEthDiscovery._unpack_header_and_payload(frame)
    assert counter == 0
    assert body == bytes([types.Command.TRANSPORT_LAYER_CMD]) + payload

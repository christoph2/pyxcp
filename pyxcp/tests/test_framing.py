from pyxcp.transport.base import XcpFraming, XcpFramingConfig, XcpTransportLayerType, ChecksumType

"""
const uint8_t FRAME0[] = {0x02, 0x00, 0x03, 0x00, 0xff, 0x00, 0x04, 0x01};

const uint8_t FRAME1[] = {0x02, 0x03, 0xff, 0x00, 0x04};
const uint8_t FRAME2[] = {0x02, 0xff, 0x00, 0x01};
const uint8_t FRAME3[] = {0x02, 0xaa, 0xff, 0x00, 0xab};

const uint8_t FRAME4[] = {0x02, 0x00, 0xff, 0x00};

const uint8_t FRAMEtws[] = {0x01, 0x00, 0x05, 0x00, 0xfc, 0x02, 0x02};
const uint8_t FRAMEtwsf[] = {0x01, 0x00, 0x05, 0x00, 0xfc, 0x00, 0x02, 0x01};
"""


def test_prepare_request_sxiL2C2CN():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=2,
        header_ctr=2,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.NO_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    # print("RQ", list(request))
    assert list(request) == [2, 0, 3, 0, 255, 0]


def test_prepare_request_sxiL2C2CB():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=2,
        header_ctr=2,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.BYTE_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    print("RQ", list(request))
    assert list(request) == [2, 0, 3, 0, 255, 0, 4]

from pyxcp.transport.base import XcpFraming, XcpFramingConfig, XcpTransportLayerType, ChecksumType


def test_prepare_request_sxiL1CN():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=1,
        header_ctr=0,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.NO_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    assert list(request) == [0x02, 0xFF, 0x00]


def test_prepare_request_sxiL1CB():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=1,
        header_ctr=0,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.BYTE_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    assert list(request) == [0x02, 0xFF, 0x00, 0x01]


def test_prepare_request_sxiL1CW_1():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=1,
        header_ctr=0,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.WORD_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    assert list(request) == [0x02, 0xFF, 0x00, 0x00, 0x02, 0xFF]


def test_prepare_request_sxiL1CW_2():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=1,
        header_ctr=0,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.WORD_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00, 0x55)
    assert list(request) == [0x03, 0xFF, 0x00, 0x55, 0x03, 0x54]


def test_prepare_request_sxiL1C1CN():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=1,
        header_ctr=1,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.NO_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 0xAA
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    assert list(request) == [0x02, 0xAA, 0xFF, 0x00]


def test_prepare_request_sxiL1C1CB():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=1,
        header_ctr=1,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.BYTE_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 0xAA
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    assert list(request) == [0x02, 0xAA, 0xFF, 0x00, 0xAB]


def test_prepare_request_sxiL1C1CW_1():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=1,
        header_ctr=1,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.WORD_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 0xAA
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    assert list(request) == [0x02, 0xAA, 0xFF, 0x00, 0x01, 0xAB]


def test_prepare_request_sxiL1C1CW_2():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=1,
        header_ctr=1,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.WORD_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 0xAA
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00, 0x55)
    assert list(request) == [0x03, 0xAA, 0xFF, 0x00, 0x55, 0x00, 0x57, 0xAB]


def test_prepare_request_sxiL2CN():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=2,
        header_ctr=0,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.NO_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    # print("RQ", list(request))
    assert list(request) == [0x02, 0x00, 0xFF, 0x00]


def test_prepare_request_sxiL2CB():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=2,
        header_ctr=0,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.BYTE_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    # print("RQ", list(request))
    assert list(request) == [0x02, 0x00, 0xFF, 0x00, 0x01]


def test_prepare_request_sxiL2CW_1():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=2,
        header_ctr=0,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.WORD_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    # print("RQ", list(request))
    assert list(request) == [0x02, 0x00, 0xFF, 0x00, 0x01, 0x01]


def test_prepare_request_sxiL2CW_2():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=2,
        header_ctr=0,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.WORD_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00, 0x00)
    # print("RQ", list(request))
    assert list(request) == [0x03, 0x00, 0xFF, 0x00, 0x00, 0x00, 0x02, 0x01]


# const uint8_t FRAME5[] = {0x02, 0x00, 0x03, 0x00, 0xff, 0x00};  // LEN_CTR_WORD / NO_CS
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
    assert list(request) == [0x02, 0x00, 0x03, 0x00, 0xFF, 0x00]


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
    assert list(request) == [0x02, 0x00, 0x03, 0x00, 0xFF, 0x00, 0x04]


def test_prepare_request_sxiL2C2CW_1():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=2,
        header_ctr=2,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.WORD_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00)
    assert list(request) == [0x02, 0x00, 0x03, 0x00, 0xFF, 0x00, 0x04, 0x01]


def test_prepare_request_sxiL2C2CW_2():
    config = XcpFramingConfig(
        transport_layer_type=XcpTransportLayerType.SXI,
        header_len=2,
        header_ctr=2,
        header_fill=0,
        tail_fill=False,
        tail_cs=ChecksumType.WORD_CHECKSUM,
    )
    framing = XcpFraming(config)
    framing.counter_send = 3
    cmd = 0xFF
    request = framing.prepare_request(cmd, 0x00, 0x55)
    assert list(request) == [0x03, 0x00, 0x03, 0x00, 0xFF, 0x00, 0x55, 0x00, 0x5A, 0x01]

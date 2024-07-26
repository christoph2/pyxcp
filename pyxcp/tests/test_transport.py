import pytest

import pyxcp.transport.base as tr


def test_factory_works():
    assert isinstance(tr.create_transport("eth"), tr.BaseTransport)
    assert isinstance(tr.create_transport("sxi"), tr.BaseTransport)
    assert isinstance(
        tr.create_transport(
            "can",
            config={
                "CAN_ID_MASTER": 1,
                "CAN_ID_SLAVE": 2,
                "CAN_DRIVER": "MockCanInterface",
            },
        ),
        tr.BaseTransport,
    )


def test_factory_works_case_insensitive():
    assert isinstance(tr.create_transport("ETH"), tr.BaseTransport)
    assert isinstance(tr.create_transport("SXI"), tr.BaseTransport)
    assert isinstance(
        tr.create_transport(
            "CAN",
            config={
                "CAN_ID_MASTER": 1,
                "CAN_ID_SLAVE": 2,
                "CAN_DRIVER": "MockCanInterface",
            },
        ),
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

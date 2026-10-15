"""Tests for XCP event parsing and listener event handlers."""

from types import SimpleNamespace

import pytest

from pyxcp.events import (
    ClockFormat,
    DaqStimEventHandler,
    SessionStateEventHandler,
    TimeSyncEvent,
    TimeSyncEventHandler,
    TimeOfTsSampling,
    TriggerInitiator,
    UserEventHandler,
)
from pyxcp.types import ByteOrder, Event


class DummyTransport:
    def __init__(self, max_cto=255, byte_order=ByteOrder.INTEL):
        self.parent = SimpleNamespace(slaveProperties=SimpleNamespace(maxCto=max_cto, byteOrder=byte_order))


def test_legacy_time_sync_can_max_cto():
    packet = bytes([0xFD, 0x08, 0x00, 0x2A, 0x78, 0x56, 0x34, 0x12])

    event = TimeSyncEvent.parse(packet, max_cto=8, byte_order="little")

    assert event.is_legacy
    assert event.trigger_info.initiator == TriggerInitiator.HW_TRIGGER
    assert event.trigger_info.time_of_sampling == TimeOfTsSampling.PROTOCOL_LAYER
    assert event.counter == 0x2A
    assert event.xcp_slave_timestamp == 0x12345678
    assert event.grandmaster_timestamp is None
    assert event.ecu_timestamp is None


def test_extended_time_sync_single_clock():
    packet = bytes([0xFD, 0x08, 0x00, 0x01, 0xAA, 0xBB, 0xCC, 0xDD])

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="little")

    assert not event.is_legacy
    assert event.payload_fmt.xcp_slave_fmt == ClockFormat.DWORD
    assert event.payload_fmt.grandmaster_fmt == ClockFormat.NOT_PRESENT
    assert event.payload_fmt.ecu_fmt == ClockFormat.NOT_PRESENT
    assert event.xcp_slave_timestamp == 0xDDCCBBAA
    assert event.grandmaster_timestamp is None


def test_extended_time_sync_triple_clock():
    packet = bytes(
        [
            0xFD,
            0x08,
            0x02,
            0x15,
            0x11,
            0x22,
            0x33,
            0x44,
            0xAA,
            0xBB,
            0xCC,
            0xDD,
            0xFF,
            0xEE,
            0xDD,
            0xCC,
        ]
    )

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="little")

    assert not event.is_legacy
    assert event.trigger_info.initiator == TriggerInitiator.GET_DAQ_CLOCK_MULTICAST
    assert event.xcp_slave_timestamp == 0x44332211
    assert event.grandmaster_timestamp == 0xDDCCBBAA
    assert event.ecu_timestamp == 0xCCDDEEFF


def test_extended_with_cluster_id():
    packet = bytes([0xFD, 0x08, 0x02, 0x41, 0x11, 0x22, 0x33, 0x44, 0xAB, 0xCD, 0x99])

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="little")

    assert event.cluster_id == 0xCDAB
    assert event.counter == 0x99


def test_extended_with_sync_state():
    packet = bytes([0xFD, 0x08, 0x04, 0x05, 0x11, 0x22, 0x33, 0x44, 0xAA, 0xBB, 0xCC, 0xDD, 0x42])

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="little")

    assert event.trigger_info.initiator == TriggerInitiator.SYNC_STATE_CHANGE
    assert event.sync_state == 0x42


def test_time_sync_handler_uses_slave_properties_for_can_legacy():
    handler = TimeSyncEventHandler(DummyTransport(max_cto=8, byte_order=ByteOrder.INTEL))
    packet = bytes([0xFD, 0x08, 0x00, 0x2A, 0x78, 0x56, 0x34, 0x12])

    assert handler.handle(Event.EV_TIME_SYNC, packet) is True
    assert handler.last_sync_event.counter == 0x2A
    assert handler.last_sync_event.xcp_slave_timestamp == 0x12345678


def test_time_sync_handler_uses_slave_properties_for_motorola():
    handler = TimeSyncEventHandler(DummyTransport(max_cto=255, byte_order=ByteOrder.MOTOROLA))
    packet = bytes([0xFD, 0x08, 0x00, 0x01, 0x12, 0x34, 0x56, 0x78])

    assert handler.handle(Event.EV_TIME_SYNC, packet) is True
    assert handler.last_sync_event.xcp_slave_timestamp == 0x12345678


def test_time_sync_handler_logs_zero_timestamp_as_present(caplog):
    caplog.set_level("INFO")
    handler = TimeSyncEventHandler(DummyTransport(max_cto=255, byte_order=ByteOrder.INTEL))
    packet = bytes([0xFD, 0x08, 0x00, 0x01, 0x00, 0x00, 0x00, 0x00])

    assert handler.handle(Event.EV_TIME_SYNC, packet) is True
    assert handler.last_sync_event.xcp_slave_timestamp == 0
    assert "XCP=0x0" in caplog.text


@pytest.mark.parametrize(
    ("handler_cls", "event_code", "packet"),
    [
        (SessionStateEventHandler, Event.EV_RESUME_MODE, bytes([0xFD, 0x00, 0x01])),
        (DaqStimEventHandler, Event.EV_STIM_TIMEOUT, bytes([0xFD, 0x09, 0x01])),
        (UserEventHandler, Event.EV_ECU_STATE_CHANGE, bytes([0xFD, 0x0C])),
    ],
)
def test_short_event_packets_are_consumed_with_warning(handler_cls, event_code, packet, caplog):
    handler = handler_cls(DummyTransport())

    assert handler.handle(event_code, packet) is True
    assert "Malformed" in caplog.text

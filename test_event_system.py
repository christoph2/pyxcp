#!/usr/bin/env python
"""
Test script for XCP 1.5 Event System - EV_TIME_SYNC parsing
"""

from pyxcp.events import TimeSyncEvent, TriggerInitiator, TimeOfTsSampling, ClockFormat


def test_legacy_time_sync():
    """Test legacy EV_TIME_SYNC parsing (MAX_CTO=8 or PAYLOAD_FMT=0)"""
    print("\n=== Test 1: Legacy Mode (MAX_CTO=8) ===")

    # Legacy packet: [PID=0xFD][Code=0x08][TRIGGER=0x00][Counter=42][Timestamp=0x12345678]
    packet = bytes([0xFD, 0x08, 0x00, 0x2A, 0x78, 0x56, 0x34, 0x12])

    event = TimeSyncEvent.parse(packet, max_cto=8, byte_order="little")

    assert event.is_legacy
    assert event.trigger_info.initiator == TriggerInitiator.HW_TRIGGER
    assert event.trigger_info.time_of_sampling == TimeOfTsSampling.PROTOCOL_LAYER
    assert event.counter == 0x2A
    assert event.xcp_slave_timestamp == 0x12345678
    assert event.grandmaster_timestamp is None
    assert event.ecu_timestamp is None

    print(f"✓ Legacy mode parsed successfully:")
    print(f"  Timestamp: {event.xcp_slave_timestamp:#x}")
    print(f"  Counter: {event.counter}")


def test_extended_time_sync_single_clock():
    """Test extended EV_TIME_SYNC with single clock"""
    print("\n=== Test 2: Extended Mode - Single Clock (XCP_SLV) ===")

    # Extended packet: [PID][Code][TRIGGER][PAYLOAD_FMT][XCP_SLV_TS:DWORD]
    # PAYLOAD_FMT = 0x01 (FMT_XCP_SLV=1=DWORD)
    packet = bytes(
        [
            0xFD,
            0x08,
            0x00,  # TRIGGER_INFO = 0 (HW_TRIGGER)
            0x01,  # PAYLOAD_FMT = 0x01 (XCP_SLV=DWORD)
            0xAA,
            0xBB,
            0xCC,
            0xDD,  # XCP Slave timestamp
        ]
    )

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="little")

    assert not event.is_legacy
    assert event.payload_fmt.xcp_slave_fmt == ClockFormat.DWORD
    assert event.payload_fmt.grandmaster_fmt == ClockFormat.NOT_PRESENT
    assert event.payload_fmt.ecu_fmt == ClockFormat.NOT_PRESENT
    assert event.xcp_slave_timestamp == 0xDDCCBBAA
    assert event.grandmaster_timestamp is None

    print(f"✓ Extended single clock parsed:")
    print(f"  XCP Slave: {event.xcp_slave_timestamp:#x}")


def test_extended_time_sync_triple_clock():
    """Test extended EV_TIME_SYNC with all 3 clocks (XCP, Grandmaster, ECU)"""
    print("\n=== Test 3: Extended Mode - Triple Clock ===")

    # PAYLOAD_FMT = 0x15 = 0b00010101
    # FMT_XCP_SLV=1 (DWORD), FMT_GRANDM=1 (DWORD), FMT_ECU=1 (DWORD)
    packet = bytes(
        [
            0xFD,
            0x08,
            0x02,  # TRIGGER_INFO = 0x02 (GET_DAQ_CLOCK_MULTICAST)
            0x15,  # PAYLOAD_FMT = 0x15
            0x11,
            0x22,
            0x33,
            0x44,  # XCP Slave TS
            0xAA,
            0xBB,
            0xCC,
            0xDD,  # Grandmaster TS
            0xFF,
            0xEE,
            0xDD,
            0xCC,  # ECU TS
        ]
    )

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="little")

    assert not event.is_legacy
    assert event.trigger_info.initiator == TriggerInitiator.GET_DAQ_CLOCK_MULTICAST
    assert event.xcp_slave_timestamp == 0x44332211
    assert event.grandmaster_timestamp == 0xDDCCBBAA
    assert event.ecu_timestamp == 0xCCDDEEFF

    print(f"✓ Extended triple clock parsed:")
    print(f"  XCP Slave: {event.xcp_slave_timestamp:#x}")
    print(f"  Grandmaster: {event.grandmaster_timestamp:#x}")
    print(f"  ECU: {event.ecu_timestamp:#x}")


def test_extended_with_cluster_id():
    """Test extended EV_TIME_SYNC with Cluster ID + Counter"""
    print("\n=== Test 4: Extended Mode - With Cluster ID ===")

    # PAYLOAD_FMT = 0x41 = 0b01000001
    # FMT_XCP_SLV=1 (DWORD), CLUSTER_IDENTIFIER=1
    packet = bytes(
        [
            0xFD,
            0x08,
            0x02,  # TRIGGER_INFO = GET_DAQ_CLOCK_MULTICAST
            0x41,  # PAYLOAD_FMT with CLUSTER_IDENTIFIER set
            0x11,
            0x22,
            0x33,
            0x44,  # XCP Slave TS
            0xAB,
            0xCD,  # Cluster ID (WORD)
            0x99,  # Counter (BYTE)
        ]
    )

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="little")

    assert event.cluster_id == 0xCDAB
    assert event.counter == 0x99

    print(f"✓ Cluster ID packet parsed:")
    print(f"  Cluster ID: {event.cluster_id:#x}")
    print(f"  Counter: {event.counter}")


def test_extended_with_sync_state():
    """Test extended EV_TIME_SYNC with SYNC_STATE byte"""
    print("\n=== Test 5: Extended Mode - With SYNC_STATE ===")

    # PAYLOAD_FMT = 0x05 = FMT_XCP_SLV=1, FMT_GRANDM=1
    packet = bytes(
        [
            0xFD,
            0x08,
            0x04,  # TRIGGER_INFO = SYNC_STATE_CHANGE
            0x05,  # PAYLOAD_FMT
            0x11,
            0x22,
            0x33,
            0x44,  # XCP Slave TS
            0xAA,
            0xBB,
            0xCC,
            0xDD,  # Grandmaster TS
            0x42,  # SYNC_STATE
        ]
    )

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="little")

    assert event.trigger_info.initiator == TriggerInitiator.SYNC_STATE_CHANGE
    assert event.sync_state == 0x42

    print(f"✓ SYNC_STATE packet parsed:")
    print(f"  Trigger: {event.trigger_info.initiator.name}")
    print(f"  Sync State: {event.sync_state:#x}")


def test_motorola_byte_order():
    """Test Motorola (big-endian) byte order"""
    print("\n=== Test 6: Motorola Byte Order ===")

    packet = bytes(
        [
            0xFD,
            0x08,
            0x00,
            0x01,  # PAYLOAD_FMT = XCP_SLV=DWORD
            0x12,
            0x34,
            0x56,
            0x78,  # Timestamp (big-endian)
        ]
    )

    event = TimeSyncEvent.parse(packet, max_cto=255, byte_order="big")

    assert event.xcp_slave_timestamp == 0x12345678  # Direct, not swapped

    print(f"✓ Motorola byte order parsed:")
    print(f"  Timestamp: {event.xcp_slave_timestamp:#x}")


if __name__ == "__main__":
    print("=" * 70)
    print("XCP 1.5 EV_TIME_SYNC Parser Test Suite")
    print("=" * 70)

    try:
        test_legacy_time_sync()
        test_extended_time_sync_single_clock()
        test_extended_time_sync_triple_clock()
        test_extended_with_cluster_id()
        test_extended_with_sync_state()
        test_motorola_byte_order()

        print("\n" + "=" * 70)
        print("✅ ALL TESTS PASSED!")
        print("=" * 70)

    except AssertionError as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback

        traceback.print_exc()
    except Exception as e:
        print(f"\n❌ ERROR: {e}")
        import traceback

        traceback.print_exc()

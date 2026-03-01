#!/usr/bin/env python
"""
WP-18: DAQ Issues Investigation Script
Test against localhost:5555 XCP server

Issues to investigate:
- #210: max_odt_entry_size calculation with interleavedMode
- #208: REINIT_DAQ / ERR_MEMORY_OVERFLOW
- #156: Getting DAQ data (should be working)
"""

import logging
from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")

# Test configuration based on Issue #210
# User had: maxDto=1033, maxCto=128, interleavedMode=False
# localhost:5555 has: maxDto=1468, maxCto=252, interleavedMode=True

test_measurements = [
    ("signal_0", 0x1000, 0, "F32"),
    ("signal_1", 0x1004, 0, "F32"),
    ("signal_2", 0x1008, 0, "F32"),
    ("signal_3", 0x100C, 0, "F32"),
]

daq_list = DaqList(
    name="test_daq",
    event_num=0,
    stim=False,
    enable_timestamps=False,
    measurements=test_measurements,
    priority=0,
    prescaler=1,
)

print("=" * 80)
print("WP-18: DAQ Issues Investigation")
print("=" * 80)

ap = ArgumentParser(description="WP-18 DAQ test")
with ap.run() as xm:
    xm.connect()

    print("\n--- Slave Properties (after connect) ---")
    props = xm.slaveProperties
    print(f"maxDto: {props.maxDto}")
    print(f"maxCto: {props.maxCto}")
    print(f"byteOrder: {props.byteOrder}")
    print(f"addressGranularity: {props.addressGranularity}")
    print(f"supportsDaq: {props.supportsDaq}")

    # interleavedMode is set by getCommModeInfo(), check if it's been called
    if "interleavedMode" in props:
        print(f"interleavedMode: {props.interleavedMode}")
        print(f"masterBlockMode: {props.masterBlockMode}")
    else:
        print("interleavedMode: NOT YET SET (need getCommModeInfo())")
        # Call it now
        print("\n--- Calling getCommModeInfo() ---")
        xm.getCommModeInfo()
        print(f"interleavedMode: {props.interleavedMode}")
        print(f"masterBlockMode: {props.masterBlockMode}")

    # Get DAQ info
    print("\n--- DAQ Resolution Info ---")
    daq_info = xm.getDaqInfo()
    print(f"DAQ info: {daq_info}")

    processor = daq_info.get("processor", {})
    resolution = daq_info.get("resolution", {})

    print("\nProcessor:")
    print(f"  keyByte: {processor.get('keyByte')}")
    print(f"  properties: {processor.get('properties')}")

    print("\nResolution:")
    print(f"  maxOdtEntrySizeDaq: {resolution.get('maxOdtEntrySizeDaq')}")
    print(f"  maxDaq: {resolution.get('maxDaq')}")
    print(f"  maxEventChannel: {resolution.get('maxEventChannel')}")

    # Calculate header_len like pyxcp does
    key_byte = processor.get("keyByte", {})
    id_field = key_byte.get("identificationField", "IDF_ABS_ODT_NUMBER")

    DAQ_ID_FIELD_SIZE = {
        "IDF_ABS_ODT_NUMBER": 1,
        "IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_BYTE": 2,
        "IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_WORD": 3,
        "IDF_REL_ODT_NUMBER_ABS_DAQ_LIST_NUMBER_WORD_ALIGNED": 4,
    }

    header_len = DAQ_ID_FIELD_SIZE.get(id_field, 1)
    max_odt_entry_size = resolution.get("maxOdtEntrySizeDaq", 0)
    max_dto = props.maxDto

    print("\n--- Calculated Values ---")
    print(f"identificationField: {id_field}")
    print(f"header_len (DAQ_ID_FIELD_SIZE): {header_len}")
    print(f"max_odt_entry_size (from slave): {max_odt_entry_size}")
    print(f"max_dto (from slave): {max_dto}")
    print(
        f"max_payload_size = min({max_odt_entry_size}, {max_dto} - {header_len}) = {min(max_odt_entry_size, max_dto - header_len)}"
    )

    # Check if interleavedMode affects this
    print("\n--- InterleavedMode Analysis ---")
    print(f"interleavedMode: {props.interleavedMode}")
    if props.interleavedMode:
        print("  → InterleavedMode is TRUE")
        print("  → DAQ frames will have: PID (1) + Sequence counter (1) + Data (N)")
        print("  → Effective payload = maxDto - header_len - 1 (for sequence)")
        print(f"  → Effective max_payload_size = {max_dto} - {header_len} - 1 = {max_dto - header_len - 1}")
    else:
        print("  → InterleavedMode is FALSE")
        print("  → DAQ frames will have: PID (1) + Data (N)")
        print(f"  → Effective max_payload_size = {max_dto} - {header_len} = {max_dto - header_len}")

    print("\n--- Current pyxcp calculation ---")
    print("max_payload_size = min(max_odt_entry_size, max_dto - header_len)")
    print(f"                 = min({max_odt_entry_size}, {max_dto - header_len})")
    print(f"                 = {min(max_odt_entry_size, max_dto - header_len)}")
    print("\n⚠️  This calculation does NOT consider interleavedMode!")
    print("    If interleavedMode=True, we should subtract another 1 byte for sequence counter")

    xm.disconnect()

print("\n" + "=" * 80)
print("Test complete!")
print("=" * 80)

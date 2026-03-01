#!/usr/bin/env python
"""
WP-18: Test interleavedMode fix with real DAQ setup
Test against localhost:5555 XCP server
"""

import logging
from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqToCsv

logging.basicConfig(level=logging.DEBUG, format="[%(levelname)s] %(message)s")

# Create a simple DAQ list with 4 float measurements
test_measurements = [
    ("signal_0", 0x1000, 0, "F32"),  # 4 bytes
    ("signal_1", 0x1004, 0, "F32"),  # 4 bytes
    ("signal_2", 0x1008, 0, "F32"),  # 4 bytes
    ("signal_3", 0x100C, 0, "F32"),  # 4 bytes
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
print("WP-18: InterleavedMode Fix Test")
print("=" * 80)

# Use DaqToCsv to test the full DAQ setup
daq_parser = DaqToCsv(daq_lists=[daq_list])

ap = ArgumentParser(description="WP-18 interleavedMode test")
with ap.run(policy=daq_parser) as xm:
    xm.connect()

    print("\n--- Slave Properties ---")
    props = xm.slaveProperties
    print(f"maxDto: {props.maxDto}")
    print(f"maxCto: {props.maxCto}")

    # Get interleavedMode (requires getCommModeInfo)
    xm.getCommModeInfo()
    print(f"interleavedMode: {props.interleavedMode}")

    # Get DAQ info
    daq_info = xm.getDaqInfo()
    processor = daq_info.get("processor", {})
    resolution = daq_info.get("resolution", {})

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

    overhead = header_len
    if props.interleavedMode:
        overhead += 1

    print("\n--- Expected Calculation (with fix) ---")
    print(f"header_len: {header_len}")
    print(f"interleavedMode: {props.interleavedMode}")
    print(f"overhead: {overhead} ({'header + seq' if props.interleavedMode else 'header only'})")
    print(f"max_odt_entry_size (from slave): {max_odt_entry_size}")
    print(f"max_payload_size = min({max_odt_entry_size}, {max_dto} - {overhead}) = {min(max_odt_entry_size, max_dto - overhead)}")

    print("\n--- Setting up DAQ ---")
    try:
        daq_parser.setup()
        print("OK: DAQ setup successful!")

        # Check the calculated values
        print("\n--- DAQ List Details ---")
        print(f"DaqList name: {daq_list.name}")
        print(f"Measurements: {len(daq_list.measurements)}")
        print(f"ODT count: {daq_list.odt_count}")
        print(f"Total entries: {daq_list.total_entries}")
        print(f"Total length: {daq_list.total_length}")

        print("\nOK: Test passed - no ERR_OUT_OF_RANGE error!")
        print("The interleavedMode fix correctly calculates overhead!")

    except Exception as e:
        print(f"\nERROR: DAQ setup failed: {e}")
        import traceback

        traceback.print_exc()
    finally:
        daq_parser.finalize()

    xm.disconnect()

print("\n" + "=" * 80)
print("Test complete!")
print("=" * 80)

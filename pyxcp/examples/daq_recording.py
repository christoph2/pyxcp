#!/usr/bin/env python
"""DAQ Recording Example - Measurements to CSV.

This example demonstrates complete DAQ workflow:
1. Connect and configure DAQ
2. Setup measurement lists
3. Start recording
4. Save to CSV
5. Optional: Plot results

Use Case: Continuous measurement logging for calibration or testing.

Note: For symbolic measurement names, see a2l_integration.py
"""

import struct
import time
from datetime import datetime

from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqToCsv

# === Configuration ===
RECORDING_DURATION = 10  # seconds
EVENT_CHANNEL = 0  # DAQ event (from getDaqEventInfo)

# Measurements (replace with your ECU addresses)
MEASUREMENTS = [
    {
        "name": "EngineSpeed",
        "address": 0x1A2000,
        "ext": 0,
        "size": 4,  # uint32
        "unit": "RPM",
        "scale": 0.25,  # Raw * 0.25 = RPM
        "offset": 0,
    },
    {
        "name": "EngineTemp",
        "address": 0x1A2004,
        "ext": 0,
        "size": 4,  # uint32
        "unit": "°C",
        "scale": 0.1,
        "offset": -40.0,  # (Raw * 0.1) - 40 = °C
    },
    {
        "name": "ThrottlePosition",
        "address": 0x1A2008,
        "ext": 0,
        "size": 2,  # uint16
        "unit": "%",
        "scale": 0.1,
        "offset": 0,  # Raw * 0.1 = %
    },
    {
        "name": "VehicleSpeed",
        "address": 0x1A200A,
        "ext": 0,
        "size": 2,  # uint16
        "unit": "km/h",
        "scale": 0.01,
        "offset": 0,
    },
]


def create_conversion_function(scale, offset):
    """Create conversion function for measurement."""

    def convert(raw_bytes):
        # Determine format based on size
        size = len(raw_bytes)
        if size == 1:
            fmt = "<B"
        elif size == 2:
            fmt = "<H"
        elif size == 4:
            fmt = "<I"
        else:
            return float("nan")

        raw = struct.unpack(fmt, raw_bytes)[0]
        return (raw * scale) + offset

    return convert


ap = ArgumentParser(description="XCP DAQ Recording Example")

with ap.run() as xcp:
    print("=" * 70)
    print("XCP DAQ Recording Example")
    print("=" * 70)

    # 1. Connect
    print("\n[Step 1/6] Connecting to ECU...")
    xcp.connect()
    print(f"✓ Connected to: {xcp.getId(0x01)}")

    # 2. Get DAQ capabilities
    print("\n[Step 2/6] Checking DAQ capabilities...")
    daq_info = xcp.getDaqInfo()
    print(f"DAQ config type: {daq_info.daqConfigType}")
    print(f"Max DAQ: {daq_info.maxDaq}")
    print(f"Max event channel: {daq_info.maxEventChannel}")

    if daq_info.maxDaq == 0:
        print("✗ ECU does not support DAQ!")
        xcp.disconnect()
        exit(1)

    # 3. Configure DAQ list
    print("\n[Step 3/6] Configuring DAQ list...")

    # Build measurement list with conversions
    daq_measurements = []
    for m in MEASUREMENTS:
        measurement = {"address": m["address"], "ext": m["ext"], "size": m["size"]}
        # Add conversion function if scaling/offset present
        if m["scale"] != 1.0 or m["offset"] != 0:
            measurement["conversion"] = create_conversion_function(m["scale"], m["offset"])
        daq_measurements.append(measurement)

    # Create DAQ list
    daq_list = DaqList(name="Engine_Measurements", event=EVENT_CHANNEL, measurements=daq_measurements)

    print(f"✓ DAQ list configured with {len(MEASUREMENTS)} measurements:")
    for m in MEASUREMENTS:
        print(f"  - {m['name']:20s} @ 0x{m['address']:08X} ({m['size']} bytes) [{m['unit']}]")

    # 4. Setup recording policy
    print("\n[Step 4/6] Setting up CSV recording...")

    # DaqToCsv automatically creates timestamped CSV file
    policy = DaqToCsv([daq_list])

    # Setup DAQ with policy
    xcp.setupDaq([daq_list], policy)
    print("✓ DAQ configured and ready")

    # 5. Start recording
    print(f"\n[Step 5/6] Starting DAQ recording for {RECORDING_DURATION} seconds...")
    start_time = datetime.now()

    xcp.startDaq()
    print(f"✓ Recording started at {start_time.strftime('%H:%M:%S')}")
    print(f"\n{'Progress:':<15} [", end="", flush=True)

    # Progress bar
    for i in range(RECORDING_DURATION):
        time.sleep(1)
        print("█", end="", flush=True)

    print("] Done!")

    # 6. Stop DAQ
    print("\n[Step 6/6] Stopping DAQ...")
    xcp.stopDaq()
    end_time = datetime.now()
    print(f"✓ Recording stopped at {end_time.strftime('%H:%M:%S')}")

    duration = (end_time - start_time).total_seconds()
    print(f"✓ Total recording time: {duration:.1f} seconds")

    # Disconnect
    print("\nDisconnecting...")
    xcp.disconnect()
    print("✓ Disconnected")

    print("\n" + "=" * 70)
    print("Recording Summary")
    print("=" * 70)
    print(f"Duration: {duration:.1f} seconds")
    print(f"Measurements: {len(MEASUREMENTS)}")
    print(f"Event channel: {EVENT_CHANNEL}")
    print("=" * 70)

print("\n✨ DAQ recording completed!")
print("\nOutput:")
print("- CSV file created in current directory")
print("- Filename format: [timestamp]_[daq_list_name].csv")
print("\nNext steps:")
print("1. Open CSV in Excel/LibreOffice for analysis")
print("2. Use Python pandas for data processing:")
print("   >>> import pandas as pd")
print("   >>> df = pd.read_csv('your_file.csv')")
print("   >>> df.plot(x='timestamp', y='EngineSpeed')")
print("\nSee docs/quickstart.md for plotting examples")

#!/usr/bin/env python
"""Calibration Workflow Example - Complete Parameter Modification.

This example demonstrates a typical calibration workflow:
1. Connect to ECU
2. Read current parameter value
3. Unlock calibration (if protected)
4. Modify parameter
5. Verify write
6. Optionally store to non-volatile memory

Use Case: Production-grade parameter calibration with verification.

Note: This example uses raw addresses. For symbolic access, see a2l_integration.py
"""

import struct
import sys

from pyxcp.cmdline import ArgumentParser

# === Configuration ===
# Replace these with your ECU's addresses
PARAM_ADDRESS = 0x1A2000  # Example: Engine speed limiter
PARAM_SIZE = 4  # 4 bytes = 32-bit integer
PARAM_NAME = "EngineSpeedLimit"

# Example values
OLD_VALUE = 6000  # Current RPM limit
NEW_VALUE = 6500  # New RPM limit


def read_uint32(data):
    """Convert 4 bytes to uint32 (little-endian)."""
    return struct.unpack("<I", data)[0]


def write_uint32(value):
    """Convert uint32 to 4 bytes (little-endian)."""
    return struct.pack("<I", value)


ap = ArgumentParser(description="XCP Calibration Workflow Example")

with ap.run() as xcp:
    print("=" * 70)
    print("XCP Calibration Workflow Example")
    print("=" * 70)

    # 1. Connect
    print("\n[Step 1/7] Connecting to ECU...")
    xcp.connect()
    ecu_id = xcp.getId(0x01)
    print(f"✓ Connected to: {ecu_id}")

    # 2. Read current value
    print(f"\n[Step 2/7] Reading current value of {PARAM_NAME}...")
    print(f"  Address: 0x{PARAM_ADDRESS:08X}")
    print(f"  Size: {PARAM_SIZE} bytes")

    current_data = xcp.upload(address=PARAM_ADDRESS, length=PARAM_SIZE)
    current_value = read_uint32(current_data)
    print(f"✓ Current value: {current_value}")

    # 3. Check if calibration is locked
    print("\n[Step 3/7] Checking calibration protection...")
    protection = xcp.getCurrentProtectionStatus()

    if protection.get("cal_pag", True):  # Default to locked if not present
        print("⚠ Calibration is LOCKED - attempting unlock...")

        try:
            # Get seed for unlock
            seed = xcp.getSeed(mode=0x01)  # Mode 0x01 = CAL/PAG
            print(f"  Seed received: {seed.hex()}")

            # In production, compute key from seed using OEM algorithm
            # For this example, we use a dummy key
            print("  Computing key from seed...")
            key = b"DummyKey1234"  # Replace with actual key computation

            # Unlock
            result = xcp.unlock(key)
            if result.currentProtectionStatus.cal_pag:
                print("✗ Unlock failed - incorrect key")
                print("Aborting calibration")
                xcp.disconnect()
                sys.exit(1)
            else:
                print("✓ Calibration unlocked successfully!")

        except Exception as e:
            print(f"✗ Unlock failed: {e}")
            print("Note: Adjust seed/key algorithm for your ECU")
            xcp.disconnect()
            sys.exit(1)
    else:
        print("✓ Calibration already unlocked")

    # 4. Write new value
    print(f"\n[Step 4/7] Writing new value: {NEW_VALUE}")
    new_data = write_uint32(NEW_VALUE)
    print(f"  Binary: {new_data.hex()}")

    xcp.download(address=PARAM_ADDRESS, data=new_data)
    print("✓ Write completed")

    # 5. Verify write
    print("\n[Step 5/7] Verifying write...")
    verify_data = xcp.upload(address=PARAM_ADDRESS, length=PARAM_SIZE)
    verify_value = read_uint32(verify_data)

    if verify_value == NEW_VALUE:
        print(f"✓ Verification successful: {verify_value}")
    else:
        print("✗ Verification FAILED!")
        print(f"  Expected: {NEW_VALUE}")
        print(f"  Read back: {verify_value}")
        print("⚠ Value may not have been written correctly")

    # 6. Store to non-volatile memory (optional)
    print("\n[Step 6/7] Storing to non-volatile memory...")
    try:
        # Not all ECUs support COPY_CAL_PAGE
        # This stores calibration to flash/EEPROM
        xcp.copyCalPage(
            src_segment=0,  # RAM segment
            src_page=0,  # Active page
            dest_segment=0,  # Flash segment
            dest_page=1,  # Flash page
        )
        print("✓ Stored to non-volatile memory")
    except Exception as e:
        print(f"ℹ Non-volatile storage not available: {e}")
        print("  (Change will be lost on ECU reset)")

    # 7. Summary
    print("\n[Step 7/7] Calibration Summary")
    print("=" * 70)
    print(f"Parameter: {PARAM_NAME}")
    print(f"Address: 0x{PARAM_ADDRESS:08X}")
    print(f"Old value: {current_value}")
    print(f"New value: {NEW_VALUE}")
    print(f"Delta: {NEW_VALUE - current_value:+d}")
    print("=" * 70)

    # Disconnect
    print("\nDisconnecting...")
    xcp.disconnect()
    print("✓ Disconnected")

print("\n✨ Calibration workflow completed!")
print("\nProduction Tips:")
print("1. Always verify writes with readback")
print("2. Implement proper seed/key algorithm")
print("3. Use A2L files for symbolic access (see a2l_integration.py)")
print("4. Log all calibration changes for traceability")
print("5. Test in controlled environment before production")

#!/usr/bin/env python
"""Basic CAN Connection Example - XCP Master Basics.

This example demonstrates the simplest possible XCP connection via CAN:
- Connect to ECU
- Read slave information
- Check protection status
- Disconnect cleanly

Use Case: Quick connectivity test or info dump for debugging.
"""

from pyxcp.cmdline import ArgumentParser

# Create argument parser for CLI configuration
ap = ArgumentParser(description="Basic CAN connection example")

# Context manager handles connection lifecycle
with ap.run() as xcp:
    print("=" * 60)
    print("XCP Basic Connection Example")
    print("=" * 60)

    # 1. Connect to slave
    print("\n[1/5] Connecting to ECU...")
    xcp.connect()
    print("✓ Connected!")

    # 2. Read ECU identification
    print("\n[2/5] Reading ECU identification...")
    ecu_id = xcp.getId(0x01)  # Type 0x01 = ASCII text
    print(f"ECU ID: {ecu_id}")

    # 3. Get slave properties
    print("\n[3/5] Reading slave properties...")
    props = xcp.slaveProperties
    print(f"Protocol Layer: {props.protocolLayerVersion}")
    print(f"Transport Layer: {props.transportLayerVersion}")
    print(f"Max CTO: {props.maxCto} bytes")
    print(f"Max DTO: {props.maxDto} bytes")
    print(f"Byte Order: {'MSB' if props.byteOrder else 'LSB'} first")

    # 4. Check optional communication mode
    if props.optionalCommMode:
        print("\n[4/5] Reading communication mode info...")
        comm_mode = xcp.getCommModeInfo()
        print(f"Max BS: {comm_mode.maxBs}")
        print(f"Min ST: {comm_mode.minSt}")
        print(f"Queue size: {comm_mode.queueSize}")
    else:
        print("\n[4/5] Optional comm mode not supported")

    # 5. Check protection status
    print("\n[5/5] Checking protection status...")
    protection = xcp.getCurrentProtectionStatus()
    print("Protection Status:")
    for resource, locked in protection.items():
        status = "🔒 LOCKED" if locked else "🔓 UNLOCKED"
        print(f"  {resource:10s}: {status}")

    # Disconnect (also happens automatically via context manager)
    print("\n" + "=" * 60)
    print("Disconnecting...")
    xcp.disconnect()
    print("✓ Disconnected cleanly")
    print("=" * 60)

print("\n✨ Example completed successfully!")
print("\nNext steps:")
print("- Try xcp_unlock.py to unlock calibration")
print("- Try run_daq.py for data acquisition")
print("- See docs/quickstart.md for more examples")

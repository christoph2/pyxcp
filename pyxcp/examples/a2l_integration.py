#!/usr/bin/env python
"""A2L Integration Example - Symbolic Access to ECU Parameters.

This example demonstrates using A2L files (ASAM MCD-2 MC) with pyXCP:
1. Load A2L file with pya2ldb
2. Query measurements and characteristics by name
3. Read/write parameters symbolically
4. Auto-generate DAQ lists from A2L
5. Convert raw values to engineering units

Use Case: Production-grade calibration with symbolic names and units.

Requirements:
    pip install pyxcp pya2ldb
"""

import struct
import sys

try:
    from pya2ldb import DB
except ImportError:
    print("✗ pya2ldb not installed")
    print("\nInstall with:")
    print("  pip install pya2ldb")
    sys.exit(1)

from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqToCsv

# === Configuration ===
A2L_FILE = "my_ecu.a2l"  # Replace with your A2L file path


def load_a2l(a2l_path):
    """Load A2L file and return database."""
    print(f"Loading A2L file: {a2l_path}")
    try:
        db = DB()
        db.import_a2l(a2l_path)
        print("✓ A2L loaded successfully")
        return db
    except FileNotFoundError:
        print(f"✗ A2L file not found: {a2l_path}")
        print("\nPlease update A2L_FILE with path to your ECU's A2L file")
        return None
    except Exception as e:
        print(f"✗ Failed to load A2L: {e}")
        return None


def explore_a2l(db):
    """Explore A2L database contents."""
    print("\n" + "=" * 70)
    print("A2L Database Contents")
    print("=" * 70)

    # Get module info
    module = db.session.query(db.Module).first()
    if module:
        print(f"\nModule: {module.name}")

        # Count objects
        characteristics = db.session.query(db.Characteristic).count()
        measurements = db.session.query(db.Measurement).count()

        print(f"  Characteristics: {characteristics}")
        print(f"  Measurements: {measurements}")

        # Show some examples
        print("\n  Example Measurements:")
        for meas in db.session.query(db.Measurement).limit(5):
            print(f"    - {meas.name:30s} @ 0x{meas.address:08X}")

        print("\n  Example Characteristics:")
        for char in db.session.query(db.Characteristic).limit(5):
            print(f"    - {char.name:30s} @ 0x{char.address:08X}")


def read_measurement_by_name(xcp, db, name):
    """Read measurement value by symbolic name."""
    print(f"\n[Reading Measurement: {name}]")

    # Query A2L database
    meas = db.session.query(db.Measurement).filter_by(name=name).first()
    if not meas:
        print(f"✗ Measurement '{name}' not found in A2L")
        return None

    print(f"  Address: 0x{meas.address:08X}")
    print(f"  Type: {meas.datatype}")
    print(f"  Unit: {meas.unit or 'N/A'}")

    # Determine size from datatype
    size_map = {"UBYTE": 1, "SBYTE": 1, "UWORD": 2, "SWORD": 2, "ULONG": 4, "SLONG": 4, "FLOAT32_IEEE": 4, "FLOAT64_IEEE": 8}
    size = size_map.get(meas.datatype, 4)

    # Read from ECU
    data = xcp.upload(address=meas.address, length=size)

    # Convert based on datatype
    format_map = {
        "UBYTE": "<B",
        "SBYTE": "<b",
        "UWORD": "<H",
        "SWORD": "<h",
        "ULONG": "<I",
        "SLONG": "<i",
        "FLOAT32_IEEE": "<f",
        "FLOAT64_IEEE": "<d",
    }
    fmt = format_map.get(meas.datatype, "<I")
    raw_value = struct.unpack(fmt, data)[0]

    # Apply conversion (COMPU_METHOD)
    # Simplified: assumes linear conversion
    # Full implementation would handle all COMPU_METHOD types
    conversion = getattr(meas, "conversion", None)
    if conversion and hasattr(conversion, "coeffs"):
        # Linear: y = ax + b
        a = conversion.coeffs.a if hasattr(conversion.coeffs, "a") else 1.0
        b = conversion.coeffs.b if hasattr(conversion.coeffs, "b") else 0.0
        eng_value = (raw_value * a) + b
    else:
        eng_value = raw_value

    print(f"  Raw value: {raw_value}")
    print(f"  Engineering value: {eng_value} {meas.unit or ''}")

    return eng_value


def write_characteristic_by_name(xcp, db, name, value):
    """Write characteristic value by symbolic name."""
    print(f"\n[Writing Characteristic: {name} = {value}]")

    # Query A2L database
    char = db.session.query(db.Characteristic).filter_by(name=name).first()
    if not char:
        print(f"✗ Characteristic '{name}' not found in A2L")
        return False

    print(f"  Address: 0x{char.address:08X}")
    print(f"  Type: {char.datatype}")
    print(f"  Unit: {char.unit or 'N/A'}")

    # Apply inverse conversion
    conversion = getattr(char, "conversion", None)
    if conversion and hasattr(conversion, "coeffs"):
        a = conversion.coeffs.a if hasattr(conversion.coeffs, "a") else 1.0
        b = conversion.coeffs.b if hasattr(conversion.coeffs, "b") else 0.0
        raw_value = int((value - b) / a)
    else:
        raw_value = int(value)

    print(f"  Engineering value: {value}")
    print(f"  Raw value: {raw_value}")

    # Pack based on datatype
    format_map = {"UBYTE": "<B", "SBYTE": "<b", "UWORD": "<H", "SWORD": "<h", "ULONG": "<I", "SLONG": "<i"}
    fmt = format_map.get(char.datatype, "<I")
    data = struct.pack(fmt, raw_value)

    # Write to ECU
    xcp.download(address=char.address, data=data)
    print("✓ Written successfully")

    return True


def create_daq_from_a2l(db, measurement_names):
    """Create DAQ list from measurement names in A2L."""
    print("\n[Creating DAQ List from A2L]")
    print(f"  Measurements: {len(measurement_names)}")

    measurements = []
    for name in measurement_names:
        meas = db.session.query(db.Measurement).filter_by(name=name).first()
        if not meas:
            print(f"  ⚠ Measurement '{name}' not found - skipping")
            continue

        # Determine size
        size_map = {"UBYTE": 1, "SBYTE": 1, "UWORD": 2, "SWORD": 2, "ULONG": 4, "SLONG": 4, "FLOAT32_IEEE": 4}
        size = size_map.get(meas.datatype, 4)

        measurements.append({"address": meas.address, "ext": 0, "size": size, "name": meas.name})
        print(f"    ✓ {meas.name:30s} @ 0x{meas.address:08X} ({size} bytes)")

    if not measurements:
        print("✗ No valid measurements found")
        return None

    daq_list = DaqList(name="A2L_Measurements", event=0, measurements=measurements)

    print(f"✓ DAQ list created with {len(measurements)} measurements")
    return daq_list


# === Main Example ===
if __name__ == "__main__":
    print("=" * 70)
    print("XCP A2L Integration Example")
    print("=" * 70)

    # Load A2L
    db = load_a2l(A2L_FILE)
    if not db:
        print("\n⚠ A2L file required for this example")
        print("\nTo use your own A2L:")
        print("1. Update A2L_FILE variable with your file path")
        print("2. Update measurement/characteristic names below")
        print("3. Run example again")
        sys.exit(1)

    # Explore A2L contents
    explore_a2l(db)

    # Connect to ECU
    ap = ArgumentParser(description="XCP A2L Integration Example")

    with ap.run() as xcp:
        print("\n" + "=" * 70)
        print("XCP Connection")
        print("=" * 70)

        xcp.connect()
        print(f"✓ Connected to: {xcp.getId(0x01)}")

        # Example 1: Read measurement by name
        # Replace with actual measurement names from your A2L
        read_measurement_by_name(xcp, db, "EngineSpeed")
        read_measurement_by_name(xcp, db, "EngineTemp")

        # Example 2: Write characteristic by name
        # Uncomment and adjust for your calibration parameter
        # write_characteristic_by_name(xcp, db, "EngineSpeedLimit", 6500)

        # Example 3: Create DAQ from A2L
        measurement_names = ["EngineSpeed", "EngineTemp", "ThrottlePosition", "VehicleSpeed"]

        daq_list = create_daq_from_a2l(db, measurement_names)
        if daq_list:
            print("\n[DAQ Recording]")
            policy = DaqToCsv([daq_list])
            xcp.setupDaq([daq_list], policy)

            print("  Starting 5-second recording...")
            xcp.startDaq()

            import time

            time.sleep(5)

            xcp.stopDaq()
            print("  ✓ Recording complete")

        xcp.disconnect()
        print("\n✓ Disconnected")

print("\n" + "=" * 70)
print("A2L Integration Benefits")
print("=" * 70)
print("\n✓ Symbolic access (names instead of addresses)")
print("✓ Automatic unit conversion")
print("✓ Type-safe read/write operations")
print("✓ Self-documenting code")
print("✓ ECU-independent scripts (A2L handles addresses)")

print("\n✨ Example completed!")
print("\nProduction Tips:")
print("1. Use A2L files for all calibration tools")
print("2. Version control A2L files with ECU software")
print("3. Validate A2L accuracy with readback tests")
print("4. Handle all COMPU_METHOD types properly")
print("5. Consider using pya2ldb's query API for complex lookups")

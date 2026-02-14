#!/usr/bin/env python
"""
CAN-FD XCP Example

Demonstrates CAN-FD (Flexible Data-Rate) configuration and usage with pyXCP.
Supports both "mixed mode" (classic + FD) and "pure FD" (AUTOSAR compliant).

Requirements:
- CAN-FD capable hardware (e.g., PEAK PCAN-USB FD, Vector VN1610, SocketCAN with FD)
- CAN-FD enabled ECU (maxCto > 8)
- For Linux: Kernel with CAN-FD support (4.0+)

Setup (Linux SocketCAN):
    sudo ip link set can0 down
    sudo ip link set can0 type can bitrate 500000 dbitrate 2000000 fd on
    sudo ip link set can0 up

Setup (Windows Vector):
    - Use Vector Hardware Config to enable CAN-FD on channel
    - Ensure VN-series hardware (VN1610, VN1630, etc.)
"""

import sys
import logging
from pyxcp.cmdline import ArgumentParser

# ============================================================================
# CONFIGURATION
# ============================================================================

# Choose configuration mode:
# - False: Mixed mode (FD only when needed)
# - True: Pure FD mode (all frames FD with max DLC)
PURE_FD_MODE = False

# CAN-FD timing parameters
ARBITRATION_BITRATE = 500000  # 500 kbps for arbitration phase
DATA_BITRATE = 2000000  # 2 Mbps for data phase (FD only)

# CAN identifiers
CAN_ID_MASTER = 0x700  # Master → Slave
CAN_ID_SLAVE = 0x701  # Slave → Master

# ============================================================================
# CONFIGURATION FILE (Alternative to command-line)
# ============================================================================


def create_canfd_config():
    """Create a CAN-FD configuration programmatically."""
    from pyxcp.config import create_application_from_config

    config = {
        "Transport": {
            "CAN": {
                "interface": "socketcan",  # or "vector", "pcan", etc.
                "channel": "can0",  # or channel number for Vector
                "bitrate": ARBITRATION_BITRATE,
                "fd": True,  # Enable CAN-FD
                "data_bitrate": DATA_BITRATE,  # FD data phase bitrate
                "can_id_master": CAN_ID_MASTER,
                "can_id_slave": CAN_ID_SLAVE,
                "max_dlc_required": PURE_FD_MODE,  # True = pure FD, False = mixed
                "padding_value": 0,  # Padding byte value (AUTOSAR default)
            }
        }
    }

    return create_application_from_config(config, log_level=logging.INFO)


# ============================================================================
# MAIN EXAMPLE
# ============================================================================


def main():
    """Main example: CAN-FD connection and data transfer."""

    # Setup logging to see FD frame details
    logging.basicConfig(level=logging.INFO, format="[%(levelname)s] %(message)s")

    print("=" * 70)
    print("CAN-FD XCP Example")
    print("=" * 70)
    print(f"Configuration Mode: {'Pure FD (AUTOSAR)' if PURE_FD_MODE else 'Mixed (FD on-demand)'}")
    print(f"Arbitration: {ARBITRATION_BITRATE} bps")
    print(f"Data Phase:  {DATA_BITRATE} bps")
    print("=" * 70)
    print()

    # Create argument parser with CAN-FD config
    ap = ArgumentParser(description="CAN-FD XCP Example", epilog="Requires CAN-FD capable hardware and ECU")

    with ap.run() as xm:
        # ====================================================================
        # 1. Connect and verify FD capability
        # ====================================================================
        print("1. Connecting to XCP slave...")
        xm.connect()

        max_cto = xm.slaveProperties.maxCto
        max_dto = xm.slaveProperties.maxDto

        print("   ✓ Connected!")
        print(f"   Max CTO: {max_cto} bytes (command → slave)")
        print(f"   Max DTO: {max_dto} bytes (slave → master)")

        if max_cto <= 8 and max_dto <= 8:
            print("\n   ⚠ WARNING: ECU reports maxCto/maxDto ≤ 8")
            print("   This ECU may not support CAN-FD or is configured for classic CAN.")
            print("   FD frames may still be sent, but ECU won't use them.")
        else:
            print("\n   ✓ ECU supports extended frames (CAN-FD capable)")

        print()

        # ====================================================================
        # 2. Test small transfer (may use classic CAN in mixed mode)
        # ====================================================================
        print("2. Testing small data transfer (8 bytes)...")

        # GET_ID typically returns small data
        try:
            id_info = xm.identifier(0)  # Get ASCII text
            print(f"   ID Response: {len(id_info)} bytes")
            if len(id_info) <= 8:
                print("   → Likely sent as classic CAN frame (8 bytes)")
            else:
                print("   → Sent as CAN-FD frame (DLC > 8)")
        except Exception as e:
            print(f"   ⚠ GET_ID failed: {e}")

        print()

        # ====================================================================
        # 3. Test large transfer (should use CAN-FD)
        # ====================================================================
        print("3. Testing large data transfer (> 8 bytes)...")

        try:
            # Set memory transfer address to some readable location
            # Note: Adjust address for your ECU
            xm.setMta(0x40000000)  # Example address

            # Fetch large block (should trigger CAN-FD if supported)
            large_data = xm.fetch(64)  # Request 64 bytes

            print(f"   ✓ Fetched {len(large_data)} bytes")
            print("   → Used CAN-FD frames for transfer")

            # Show first few bytes
            preview = " ".join(f"{b:02X}" for b in large_data[:16])
            print(f"   Data preview: {preview}...")

        except Exception as e:
            print(f"   ⚠ Large transfer failed: {e}")
            print("   This may be normal if address is not readable.")

        print()

        # ====================================================================
        # 4. Check CAN-FD statistics (if transport supports it)
        # ====================================================================
        print("4. CAN-FD Statistics:")

        if hasattr(xm.transport, "can_interface"):
            print(f"   Interface: {xm.transport.interface_name}")
            print(f"   FD Enabled: {xm.transport.fd}")
            print(f"   Max DLC Required: {xm.transport.max_dlc_required}")
            print(f"   Padding Value: 0x{xm.transport.padding_value:02X}")
        else:
            print("   (Statistics not available for this transport)")

        print()

        # ====================================================================
        # 5. Disconnect
        # ====================================================================
        print("5. Disconnecting...")
        xm.disconnect()
        print("   ✓ Disconnected")

    print()
    print("=" * 70)
    print("CAN-FD Example Complete!")
    print("=" * 70)
    print()
    print("Tips:")
    print("- Mixed mode (default): Uses FD only when needed (efficient)")
    print("- Pure FD mode (AUTOSAR): Always uses FD with max DLC (strict)")
    print("- Check ECU maxCto/maxDto to verify FD support")
    print("- Use wireshark/candump to observe CAN-FD frames on bus")


# ============================================================================
# HELPER: Verify CAN-FD Interface
# ============================================================================


def check_canfd_interface():
    """Check if CAN interface supports CAN-FD."""
    print("\nChecking CAN-FD interface capabilities...")
    print()

    import platform

    if platform.system() == "Linux":
        # Check SocketCAN configuration
        import subprocess  # nosec

        try:
            result = subprocess.run(["ip", "-details", "link", "show", "can0"], capture_output=True, text=True)  # nosec
            if result.returncode == 0:
                output = result.stdout
                if "canfd on" in output:
                    print("✓ SocketCAN interface supports CAN-FD")

                    # Extract bitrates
                    if "dbitrate" in output:
                        print(f"  {output.split('dbitrate')[1].split()[0]} bps data rate detected")
                else:
                    print("✗ CAN-FD not enabled on interface")
                    print("  Run: sudo ip link set can0 type can bitrate 500000 dbitrate 2000000 fd on")
            else:
                print("✗ can0 interface not found")
                print("  Check: ip link show")
        except FileNotFoundError:
            print("⚠ 'ip' command not found - cannot check interface")

    elif platform.system() == "Windows":
        print("Windows detected:")
        print("- Vector: Ensure VN-series hardware (VN1610, VN1630, etc.)")
        print("- PEAK: Ensure PCAN-USB FD or PCAN-PCI FD")
        print("- Check vendor tools to verify FD support")

    else:
        print(f"{platform.system()} detected:")
        print("- Check hardware vendor documentation for CAN-FD support")

    print()


# ============================================================================
# ENTRY POINT
# ============================================================================

if __name__ == "__main__":
    # Optional: Check interface before running
    if "--check" in sys.argv:
        check_canfd_interface()
        sys.exit(0)

    try:
        main()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
    except Exception as e:
        print(f"\n\nError: {e}")
        logging.exception("Detailed traceback:")
        sys.exit(1)

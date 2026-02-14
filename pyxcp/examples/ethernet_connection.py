#!/usr/bin/env python
"""Ethernet Connection Example - TCP and UDP.

This example demonstrates XCP over Ethernet:
- TCP connection (reliable, connection-oriented)
- UDP connection (fast, connectionless)
- IPv4 and IPv6
- Timeout configuration
- Error recovery

Use Case: High-bandwidth ECU communication for rapid prototyping.
"""

import sys

from pyxcp import Master
from pyxcp.config import create_application_from_config, set_application
from pyxcp.types import XcpResponseError, XcpTimeoutError

# === Configuration ===
ECU_IP = "192.168.1.100"  # Replace with your ECU IP
ECU_PORT = 5555  # Standard XCP port
PROTOCOL = "TCP"  # or "UDP"
TIMEOUT = 2.0  # seconds


def connect_tcp(host, port, timeout=2.0):
    """Connect via TCP (reliable, connection-oriented)."""
    print(f"\nConnecting via TCP to {host}:{port}...")

    config = {
        "Transport": {
            "Eth": {
                "host": host,
                "port": port,
                "protocol": "TCP",
                "ipv6": False,
                "tcp_nodelay": True,  # Disable Nagle's algorithm for low latency
            }
        }
    }

    app = create_application_from_config(config)
    set_application(app)

    with Master("eth") as xcp:
        xcp.connect()
        print("✓ Connected via TCP")

        # Read slave info
        ecu_id = xcp.getId(0x01)
        props = xcp.slaveProperties

        print(f"  ECU ID: {ecu_id}")
        print(f"  Max CTO: {props.maxCto} bytes")
        print(f"  Max DTO: {props.maxDto} bytes")

        # Test communication
        print("\n  Testing communication...")
        for i in range(5):
            xcp.getId(0x01)
            print(f"    Request {i + 1}/5: OK")

        xcp.disconnect()
        print("✓ Disconnected")

    return True


def connect_udp(host, port, timeout=2.0):
    """Connect via UDP (fast, connectionless)."""
    print(f"\nConnecting via UDP to {host}:{port}...")

    config = {"Transport": {"Eth": {"host": host, "port": port, "protocol": "UDP", "ipv6": False}}}

    app = create_application_from_config(config)
    set_application(app)

    with Master("eth") as xcp:
        xcp.connect()
        print("✓ Connected via UDP")

        # Read slave info
        ecu_id = xcp.getId(0x01)
        props = xcp.slaveProperties

        print(f"  ECU ID: {ecu_id}")
        print(f"  Max CTO: {props.maxCto} bytes")
        print(f"  Max DTO: {props.maxDto} bytes")

        # Test communication
        print("\n  Testing communication...")
        for i in range(5):
            xcp.getId(0x01)
            print(f"    Request {i + 1}/5: OK")

        xcp.disconnect()
        print("✓ Disconnected")

    return True


def connect_ipv6(host, port):
    """Connect via IPv6."""
    print(f"\nConnecting via IPv6 to [{host}]:{port}...")

    config = {
        "Transport": {
            "Eth": {
                "host": host,
                "port": port,
                "protocol": "TCP",
                "ipv6": True,  # Enable IPv6
            }
        }
    }

    app = create_application_from_config(config)
    set_application(app)

    with Master("eth") as xcp:
        xcp.connect()
        print("✓ Connected via IPv6")

        ecu_id = xcp.getId(0x01)
        print(f"  ECU ID: {ecu_id}")

        xcp.disconnect()
        print("✓ Disconnected")

    return True


def test_error_recovery(host, port):
    """Demonstrate error handling and recovery."""
    print("\nTesting error recovery...")

    config = {"Transport": {"Eth": {"host": host, "port": port, "protocol": "TCP", "ipv6": False}}}

    app = create_application_from_config(config)
    set_application(app)

    try:
        with Master("eth") as xcp:
            xcp.connect()
            print("✓ Connected")

            # Try to access invalid address (should fail)
            print("  Attempting invalid memory access...")
            try:
                xcp.upload(address=0xFFFFFFFF, length=4)
                print("    Unexpected success!")
            except XcpResponseError as e:
                print(f"    Expected error: {e.error_code} - {e.error_text}")
                print("    ✓ Error handled, connection still alive")

            # Verify connection is still working
            print("  Verifying connection...")
            xcp.getId(0x01)
            print("    ✓ Connection recovered successfully")

            xcp.disconnect()
            print("✓ Disconnected")

        return True

    except XcpTimeoutError:
        print("✗ Timeout - ECU not responding")
        return False
    except ConnectionRefusedError:
        print("✗ Connection refused - check IP/port and ECU power")
        return False
    except Exception as e:
        print(f"✗ Unexpected error: {e}")
        return False


if __name__ == "__main__":
    print("=" * 70)
    print("XCP Ethernet Connection Example")
    print("=" * 70)

    # Test connectivity first
    print("\n[Connectivity Test]")
    print(f"Target: {ECU_IP}:{ECU_PORT}")

    import socket

    print("\nChecking network connectivity...")
    try:
        # Try to ping (ICMP)
        import subprocess  # nosec B404 - Safe use for network connectivity test

        result = subprocess.run(  # nosec B603 - Hardcoded command, ECU_IP is config
            ["ping", "-n", "1", "-w", "1000", ECU_IP] if sys.platform == "win32" else ["ping", "-c", "1", "-W", "1", ECU_IP],
            capture_output=True,
            text=True,
        )
        if result.returncode == 0:
            print(f"✓ Host {ECU_IP} is reachable")
        else:
            print(f"⚠ Host {ECU_IP} is not responding to ping")
            print("  (This may be OK if ICMP is blocked)")
    except Exception:
        print("  (Ping test not available)")

    # Try TCP socket connection
    print(f"\nTrying TCP connection to {ECU_IP}:{ECU_PORT}...")
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(2)
        sock.connect((ECU_IP, ECU_PORT))
        sock.close()
        print(f"✓ TCP port {ECU_PORT} is open")
    except (socket.timeout, ConnectionRefusedError):
        print(f"✗ TCP port {ECU_PORT} is closed or filtered")
        print("\nTroubleshooting:")
        print("1. Verify ECU IP address")
        print("2. Check ECU is powered and XCP server running")
        print("3. Check firewall rules (both host and ECU)")
        print("4. Try different port (common: 5555, 5656)")
        sys.exit(1)
    except Exception as e:
        print(f"✗ Network error: {e}")
        sys.exit(1)

    # Run examples
    print("\n" + "=" * 70)
    print("Running Connection Examples")
    print("=" * 70)

    # TCP Connection
    try:
        connect_tcp(ECU_IP, ECU_PORT, TIMEOUT)
    except Exception as e:
        print(f"✗ TCP connection failed: {e}")

    # UDP Connection
    try:
        connect_udp(ECU_IP, ECU_PORT, TIMEOUT)
    except Exception as e:
        print(f"✗ UDP connection failed: {e}")

    # Error Recovery
    try:
        test_error_recovery(ECU_IP, ECU_PORT)
    except Exception as e:
        print(f"✗ Error recovery test failed: {e}")

    # IPv6 (optional - uncomment if you have IPv6)
    # IPV6_HOST = "fe80::1"  # Link-local example
    # try:
    #     connect_ipv6(IPV6_HOST, ECU_PORT)
    # except Exception as e:
    #     print(f"✗ IPv6 connection failed: {e}")

    print("\n" + "=" * 70)
    print("Summary")
    print("=" * 70)
    print("\nTCP vs UDP:")
    print("  TCP: Reliable, ordered, connection-oriented")
    print("       - Use for: Critical commands, firmware updates")
    print("       - Overhead: Higher (3-way handshake, ACKs)")
    print("  UDP: Fast, connectionless, no guarantees")
    print("       - Use for: DAQ streaming, high-frequency measurements")
    print("       - Overhead: Lower (no handshake, no retransmission)")
    print("\nRecommendation:")
    print("  - Development/Testing: TCP (easier debugging)")
    print("  - Production DAQ: UDP (lower latency)")

    print("\n✨ Example completed!")
    print("\nNext steps:")
    print("- Adjust ECU_IP and ECU_PORT for your setup")
    print("- Try different protocols (TCP vs UDP)")
    print("- See docs/quickstart.md for more examples")

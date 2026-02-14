#!/usr/bin/env python
"""
Robust Error Handling with Configurable Retries (WP-8)

Demonstrates:
1. Configuring max_retries for production vs development
2. Handling XcpTimeoutError and XcpResponseError
3. Best practices for production code

Author: pyXCP Contributors
License: LGPL-3.0
"""

from pyxcp.cmdline import ArgumentParser
from pyxcp.types import XcpResponseError, XcpTimeoutError


def production_mode_example():
    """Production mode: Limited retries to prevent infinite loops."""
    ap = ArgumentParser(description="Production XCP connection")

    # Configure for production: fail fast!
    ap.config.general.max_retries = 3  # Max 3 attempts
    ap.config.transport.timeout = 2.0  # 2 second timeout

    try:
        with ap.run() as x:
            # This will NOT block forever if ECU is unresponsive
            x.connect()

            # Read calibration parameter
            result = x.fetch(address=0x1000, length=4)
            print(f"Value: {result.hex()}")

            x.disconnect()

    except XcpTimeoutError as e:
        print(f"ECU not responding: {e}")
        print("Check: 1) ECU power, 2) Network cable, 3) CAN termination")
        return False

    except XcpResponseError as e:
        print(f"ECU returned error: {e}")
        print(f"Error code: {e.error_code}")
        return False

    return True


def development_mode_example():
    """Development mode: XCP standard compliance with infinite retries."""
    ap = ArgumentParser(description="Development XCP connection")

    # Configure for development: follow XCP spec
    ap.config.general.max_retries = -1  # Infinite (XCP standard)
    ap.config.transport.timeout = 5.0  # Longer timeout for debugging

    try:
        with ap.run(loglevel="DEBUG") as x:
            # Will retry forever per XCP spec
            x.connect()

            # Your development/test code here
            result = x.fetch(address=0x1000, length=4)
            print(f"Value: {result.hex()}")

            x.disconnect()

    except KeyboardInterrupt:
        print("\nUser interrupted (Ctrl+C)")
        return False

    return True


def automated_test_example():
    """Automated testing: No retries for fast failures."""
    ap = ArgumentParser(description="Automated test")

    # Configure for automated testing: fail immediately
    ap.config.general.max_retries = 0  # No retries!
    ap.config.transport.timeout = 1.0  # Short timeout

    try:
        with ap.run() as x:
            x.connect()

            # Test code here
            result = x.fetch(address=0x1000, length=4)
            assert len(result) == 4, "Invalid response length"  # nosec B101 - intentional for testing

            x.disconnect()

    except (XcpTimeoutError, XcpResponseError) as e:
        print(f"Test failed: {e}")
        return False

    return True


def retry_with_fallback_example():
    """Advanced: Try multiple configurations with fallback."""
    configs = [
        {"timeout": 1.0, "retries": 1},  # Fast first attempt
        {"timeout": 2.0, "retries": 3},  # More patient second attempt
        {"timeout": 5.0, "retries": 5},  # Very patient final attempt
    ]

    for idx, config in enumerate(configs, 1):
        print(f"Attempt {idx}/{len(configs)}: timeout={config['timeout']}s, retries={config['retries']}")

        ap = ArgumentParser(description="Fallback example")
        ap.config.general.max_retries = config["retries"]
        ap.config.transport.timeout = config["timeout"]

        try:
            with ap.run() as x:
                x.connect()
                print(f"Connected successfully on attempt {idx}!")

                result = x.fetch(address=0x1000, length=4)
                print(f"Value: {result.hex()}")

                x.disconnect()
                return True

        except (XcpTimeoutError, XcpResponseError) as e:
            print(f"Attempt {idx} failed: {e}")
            if idx == len(configs):
                print("All attempts failed!")
                return False
            print("Trying next configuration...\n")

    return False


if __name__ == "__main__":
    print("=== Production Mode (max_retries=3) ===")
    production_mode_example()

    print("\n=== Development Mode (max_retries=-1, infinite) ===")
    print("(Skipped in demo - would run forever on timeout)")

    print("\n=== Automated Test Mode (max_retries=0) ===")
    automated_test_example()

    print("\n=== Retry with Fallback ===")
    retry_with_fallback_example()

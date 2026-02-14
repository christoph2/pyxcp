#!/usr/bin/env python
"""Multi-ECU Setup Example - Sequential and Parallel Access.

This example demonstrates working with multiple ECUs:
1. Sequential access (one ECU at a time)
2. Parallel DAQ from multiple ECUs
3. Error handling per ECU
4. Synchronized measurements

Use Case: System-level testing with multiple controllers.

Note: Each ECU needs separate transport configuration.
"""

import threading
import time
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from pyxcp import Master
from pyxcp.config import create_application_from_config
from pyxcp.daq_stim import DaqList, DaqToCsv

# === Configuration ===
# Define your ECUs here
ECUS = [
    {
        "name": "Engine_ECU",
        "transport": "CAN",
        "config": {"Transport": {"CAN": {"device": "socketcan", "channel": "can0", "bitrate": 500000}}},
        "measurements": [
            {"address": 0x1A2000, "ext": 0, "size": 4, "name": "EngineSpeed"},
            {"address": 0x1A2004, "ext": 0, "size": 4, "name": "EngineTemp"},
        ],
    },
    {
        "name": "Transmission_ECU",
        "transport": "CAN",
        "config": {"Transport": {"CAN": {"device": "socketcan", "channel": "can1", "bitrate": 500000}}},
        "measurements": [
            {"address": 0x1B3000, "ext": 0, "size": 2, "name": "GearPosition"},
            {"address": 0x1B3002, "ext": 0, "size": 4, "name": "OilTemp"},
        ],
    },
]


def connect_ecu_sequential(ecu_config):
    """Connect to single ECU and read info (sequential pattern)."""
    name = ecu_config["name"]
    print(f"\n[{name}]")
    print("  Connecting...")

    try:
        # Create application with ECU-specific config
        app = create_application_from_config(
            ecu_config["config"],
            log_level=20,  # INFO
        )

        # Use transport specified in config
        with Master(ecu_config["transport"], config=app) as xcp:
            xcp.connect()

            # Read ECU info
            ecu_id = xcp.getId(0x01)
            props = xcp.slaveProperties

            print("  ✓ Connected")
            print(f"    ID: {ecu_id}")
            print(f"    Max CTO: {props.maxCto} bytes")
            print(f"    Max DTO: {props.maxDto} bytes")

            xcp.disconnect()

            return {"name": name, "success": True, "id": ecu_id, "properties": props}

    except Exception as e:
        print(f"  ✗ Failed: {e}")
        return {"name": name, "success": False, "error": str(e)}


def record_daq_from_ecu(ecu_config, duration=10):
    """Record DAQ from single ECU (for parallel execution)."""
    name = ecu_config["name"]

    try:
        # Create application
        app = create_application_from_config(ecu_config["config"])

        # Thread-local Master instance (IMPORTANT!)
        with Master(ecu_config["transport"], config=app) as xcp:
            xcp.connect()

            # Configure DAQ
            daq_list = DaqList(name=f"{name}_DAQ", event=0, measurements=ecu_config["measurements"])

            policy = DaqToCsv([daq_list])
            xcp.setupDaq([daq_list], policy)

            # Start recording
            start_time = datetime.now()
            xcp.startDaq()

            # Record for specified duration
            time.sleep(duration)

            # Stop recording
            xcp.stopDaq()
            end_time = datetime.now()

            xcp.disconnect()

            return {
                "name": name,
                "success": True,
                "start_time": start_time,
                "end_time": end_time,
                "duration": (end_time - start_time).total_seconds(),
            }

    except Exception as e:
        return {"name": name, "success": False, "error": str(e)}


def sequential_access():
    """Example 1: Sequential ECU access (one at a time)."""
    print("\n" + "=" * 70)
    print("Example 1: Sequential ECU Access")
    print("=" * 70)
    print("\nConnecting to ECUs one at a time...")

    results = []
    for ecu in ECUS:
        result = connect_ecu_sequential(ecu)
        results.append(result)

    # Summary
    print("\n" + "-" * 70)
    print("Summary:")
    successful = sum(1 for r in results if r["success"])
    print(f"  Connected: {successful}/{len(ECUS)} ECUs")

    for result in results:
        status = "✓" if result["success"] else "✗"
        print(f"  {status} {result['name']}")

    return results


def parallel_daq_recording(duration=10):
    """Example 2: Parallel DAQ from multiple ECUs."""
    print("\n" + "=" * 70)
    print("Example 2: Parallel DAQ Recording")
    print("=" * 70)
    print(f"\nRecording from {len(ECUS)} ECUs in parallel for {duration} seconds...")

    # Use ThreadPoolExecutor for parallel execution
    results = []

    with ThreadPoolExecutor(max_workers=len(ECUS)) as executor:
        # Submit tasks
        futures = {executor.submit(record_daq_from_ecu, ecu, duration): ecu["name"] for ecu in ECUS}

        # Progress indicator
        print("\nProgress: [", end="", flush=True)
        for i in range(duration):
            time.sleep(1)
            print("█", end="", flush=True)
        print("] Done!")

        # Collect results
        for future in as_completed(futures):
            ecu_name = futures[future]
            try:
                result = future.result()
                results.append(result)

                if result["success"]:
                    print(f"  ✓ {result['name']}: {result['duration']:.1f}s")
                else:
                    print(f"  ✗ {result['name']}: {result['error']}")

            except Exception as e:
                print(f"  ✗ {ecu_name}: {e}")
                results.append({"name": ecu_name, "success": False, "error": str(e)})

    # Summary
    print("\n" + "-" * 70)
    print("Summary:")
    successful = sum(1 for r in results if r["success"])
    print(f"  Recorded: {successful}/{len(ECUS)} ECUs")

    return results


def synchronized_measurement():
    """Example 3: Synchronized measurement across ECUs."""
    print("\n" + "=" * 70)
    print("Example 3: Synchronized Measurement")
    print("=" * 70)
    print("\nReading synchronized snapshot from all ECUs...")

    # Barrier for synchronization
    barrier = threading.Barrier(len(ECUS))
    results = {}
    lock = threading.Lock()

    def read_synchronized(ecu_config):
        """Read measurement with synchronization."""
        name = ecu_config["name"]

        try:
            app = create_application_from_config(ecu_config["config"])

            with Master(ecu_config["transport"], config=app) as xcp:
                xcp.connect()

                # Wait for all ECUs to connect
                barrier.wait()

                # Synchronized read (happens at same time)
                timestamp = time.time()
                data = xcp.upload(address=ecu_config["measurements"][0]["address"], length=ecu_config["measurements"][0]["size"])

                xcp.disconnect()

                with lock:
                    results[name] = {"success": True, "timestamp": timestamp, "data": data.hex()}

        except Exception as e:
            with lock:
                results[name] = {"success": False, "error": str(e)}

    # Execute synchronized reads
    threads = []
    for ecu in ECUS:
        t = threading.Thread(target=read_synchronized, args=(ecu,))
        t.start()
        threads.append(t)

    # Wait for all threads
    for t in threads:
        t.join()

    # Display results
    print("\nResults:")
    for name, result in results.items():
        if result["success"]:
            print(f"  ✓ {name:20s} @ {result['timestamp']:.6f}: {result['data']}")
        else:
            print(f"  ✗ {name:20s} Error: {result['error']}")

    return results


# === Main Example ===
if __name__ == "__main__":
    print("=" * 70)
    print("XCP Multi-ECU Setup Example")
    print("=" * 70)

    print("\nConfiguration:")
    print(f"  ECUs: {len(ECUS)}")
    for ecu in ECUS:
        print(f"    - {ecu['name']:20s} ({ecu['transport']})")

    # Example 1: Sequential access
    sequential_results = sequential_access()

    # Example 2: Parallel DAQ recording
    parallel_results = parallel_daq_recording(duration=5)

    # Example 3: Synchronized measurement
    sync_results = synchronized_measurement()

    print("\n" + "=" * 70)
    print("Multi-ECU Patterns Summary")
    print("=" * 70)

    print("\n1. Sequential Access:")
    print("   - Simple, reliable")
    print("   - Use for: Configuration, diagnostics")
    print("   - Limitation: Slow for many ECUs")

    print("\n2. Parallel DAQ:")
    print("   - High throughput")
    print("   - Use for: System-level testing, HIL")
    print("   - Limitation: Requires thread-safe code")

    print("\n3. Synchronized Measurement:")
    print("   - Time-correlated data")
    print("   - Use for: Event analysis, cross-ECU debugging")
    print("   - Limitation: Clock skew between ECUs")

    print("\n✨ Example completed!")
    print("\nProduction Tips:")
    print("1. Each Master instance must be thread-local")
    print("2. Use ThreadPoolExecutor for parallel DAQ")
    print("3. Handle per-ECU errors gracefully")
    print("4. Consider ECU discovery/enumeration")
    print("5. Implement ECU health monitoring")
    print("6. Use barriers for synchronized measurements")
    print("\nSee multi_channel_can.py for CAN-specific multi-channel patterns")

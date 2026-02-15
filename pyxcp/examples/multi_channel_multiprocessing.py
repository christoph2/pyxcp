#!/usr/bin/env python
"""
Example: Using multiple CAN channels with multiprocessing

This example demonstrates how to communicate with multiple ECUs using
separate Python processes via multiprocessing. This approach provides:

1. True parallelism (bypasses Python GIL)
2. Process isolation (crashes don't affect other ECUs)
3. Independent memory spaces
4. Production-level robustness for multi-ECU test benches

**NOTE ON WINDOWS:** Subprocess logging may not appear in console due to
multiprocessing behavior. Each subprocess has its own logger. For production
use, consider:
- Using file handlers for subprocess logs
- Using multiprocessing.log_to_stderr()
- Collecting logs via queues
- Testing individual processes separately first

Requirements:
- Multi-channel CAN interface OR multiple transport types
- python-can with appropriate interface driver
- Each ECU needs separate transport configuration file

Usage:
    # Test individual connections first:
    python -c "import sys; sys.argv=['test','-c','conf_eth.py']; ..."

    # Run basic example:
    python multi_channel_multiprocessing.py

    # Run DAQ example:
    python multi_channel_multiprocessing.py daq

Author: pyxcp contributors
License: GPLv2
"""

import logging
import multiprocessing
import time
from datetime import datetime
from pathlib import Path

from pyxcp.cmdline import ArgumentParser

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(processName)s] %(levelname)s: %(message)s")


def xcp_worker_process(ecu_name, config_file, task_queue, result_queue):
    """Worker process for XCP communication.

    Each ECU runs in its own process with its own Master instance.

    Parameters
    ----------
    ecu_name : str
        Name identifier for this ECU (e.g., "Engine_ECU", "Brake_ECU")
    config_file : str
        Path to configuration file for this Master instance
    task_queue : multiprocessing.Queue
        Queue for receiving tasks from main process
    result_queue : multiprocessing.Queue
        Queue for sending results back to main process
    """
    import sys

    logger = logging.getLogger(f"{ecu_name}")
    logger.info(f"Process started for {ecu_name}")

    try:
        # Set sys.argv to pass config file to ArgumentParser
        sys.argv = ["worker", "-c", config_file]

        # Use ArgumentParser to create Master with config file
        ap = ArgumentParser(description=f"{ecu_name} worker")

        # Run XCP session
        with ap.run() as xm:
            xm.connect()
            logger.info(f"Connected to {ecu_name}")

            # Get ECU info
            ecu_id = xm.getId(0x01)
            props = xm.slaveProperties
            logger.info(f"ECU ID: {ecu_id}, Max CTO: {props.maxCto}, Max DTO: {props.maxDto}")

            result_queue.put({"ecu": ecu_name, "status": "connected", "id": ecu_id})

            # Process tasks from queue
            while True:
                try:
                    task = task_queue.get(timeout=1.0)
                except Exception:  # nosec B110, B112 - Queue timeout handling
                    continue

                try:
                    task = task_queue.get(timeout=1.0)

                    if task["command"] == "STOP":
                        logger.info("Received STOP command")
                        break

                    elif task["command"] == "READ":
                        # Upload memory
                        address = task["address"]
                        length = task["length"]
                        data = xm.upload(address=address, length=length)
                        logger.info(f"Read {length} bytes from 0x{address:X}: {data.hex()}")
                        result_queue.put({"ecu": ecu_name, "command": "READ", "data": data.hex(), "address": address})

                    elif task["command"] == "WRITE":
                        # Download memory
                        address = task["address"]
                        data = bytes.fromhex(task["data"])
                        xm.download(address=address, data=data)
                        logger.info(f"Wrote {len(data)} bytes to 0x{address:X}")
                        result_queue.put({"ecu": ecu_name, "command": "WRITE", "success": True, "address": address})

                    elif task["command"] == "PING":
                        # Simple connectivity check
                        logger.info("PING")
                        result_queue.put({"ecu": ecu_name, "command": "PING", "timestamp": time.time()})

                    else:
                        logger.warning(f"Unknown command: {task['command']}")

                except Exception as e:
                    logger.error(f"Error processing task: {e}", exc_info=True)
                    result_queue.put({"ecu": ecu_name, "error": str(e)})
                    break  # Exit loop on error

            xm.disconnect()
            logger.info(f"Disconnected from {ecu_name}")

    except Exception as e:
        logger.error(f"Fatal error in worker process: {e}", exc_info=True)
        result_queue.put({"ecu": ecu_name, "status": "error", "error": str(e)})


def example_basic_multiprocessing():
    """Example 1: Basic multi-process ECU communication."""
    print("\n" + "=" * 80)
    print("Example 1: Basic Multiprocessing - Two ECUs")
    print("=" * 80)

    # Define ECUs with their config files
    # Use the existing example configs from pyxcp/examples/
    examples_dir = Path(__file__).parent

    ecus = [
        {
            "name": "CAN_ECU",
            "config_file": str(examples_dir / "conf_cv.py"),
        },
        {
            "name": "ETH_ECU",
            "config_file": str(examples_dir / "conf_eth.py"),
        },
    ]

    # Create queues for each ECU
    processes = []
    task_queues = {}
    result_queue = multiprocessing.Queue()

    # Start processes
    print("\nStarting ECU processes...")
    for ecu in ecus:
        task_queue = multiprocessing.Queue()
        task_queues[ecu["name"]] = task_queue

        process = multiprocessing.Process(
            target=xcp_worker_process,
            args=(ecu["name"], ecu["config_file"], task_queue, result_queue),
            name=ecu["name"],
        )
        process.start()
        processes.append({"name": ecu["name"], "process": process, "task_queue": task_queue})
        print(f"  Started process for {ecu['name']} (PID: {process.pid})")

    # Wait for connections
    print("\nWaiting for ECUs to connect...")
    connected = 0
    while connected < len(ecus):
        result = result_queue.get(timeout=5.0)
        if result.get("status") == "connected":
            print(f"  [OK] {result['ecu']} connected (ID: {result['id']})")
            connected += 1

    # Send PING to all ECUs
    print("\n--- Sending PING to all ECUs ---")
    for proc in processes:
        proc["task_queue"].put({"command": "PING"})

    # Collect PINGs
    for _ in range(len(processes)):
        result = result_queue.get(timeout=2.0)
        print(f"  [OK] {result['ecu']} responded at {result['timestamp']:.6f}")

    # Send READ command to first ECU
    print("\n--- Reading memory from CAN_ECU ---")
    task_queues["CAN_ECU"].put({"command": "READ", "address": 0x1000, "length": 4})

    result = result_queue.get(timeout=2.0)
    print(f"  [OK] {result['ecu']} returned: {result['data']} from 0x{result['address']:X}")

    # Send STOP to all
    print("\n--- Stopping all ECU processes ---")
    for proc in processes:
        proc["task_queue"].put({"command": "STOP"})

    # Wait for all processes to finish
    for proc in processes:
        proc["process"].join(timeout=3.0)
        if proc["process"].is_alive():
            print(f"  Warning: {proc['name']} did not stop gracefully, terminating...")
            proc["process"].terminate()
            proc["process"].join()
        print(f"  [OK] {proc['name']} stopped")

    print("\n*** Example 1 completed!")


def xcp_daq_worker_process(ecu_name, config_file, duration, result_queue):
    """Worker process for DAQ recording.

    Parameters
    ----------
    ecu_name : str
        Name identifier for this ECU
    config_file : str
        Path to configuration file
    duration : float
        Recording duration in seconds
    result_queue : multiprocessing.Queue
        Queue for sending results back to main process
    """
    import sys

    logger = logging.getLogger(f"DAQ-{ecu_name}")
    logger.info(f"DAQ process started for {ecu_name}")

    try:
        from pyxcp.daq_stim import DaqList, DaqToCsv

        # Set sys.argv to pass config file to ArgumentParser
        sys.argv = ["daq_worker", "-c", config_file]

        ap = ArgumentParser(description=f"{ecu_name} DAQ worker")

        with ap.run() as xm:
            xm.connect()
            logger.info(f"Connected to {ecu_name}")

            # Setup DAQ
            measurements = [
                {"address": 0x1000, "ext": 0, "size": 4, "name": "signal1"},
                {"address": 0x1004, "ext": 0, "size": 2, "name": "signal2"},
            ]

            daq_list = DaqList(name=f"daq_{ecu_name.lower()}", event=0, measurements=measurements)

            policy = DaqToCsv([daq_list], filename=f"{ecu_name.lower()}_daq.csv")
            xm.setupDaq([daq_list], policy)

            # Start recording
            start_time = datetime.now()
            xm.startDaq()
            logger.info(f"DAQ started, recording for {duration}s...")

            time.sleep(duration)

            # Stop recording
            xm.stopDaq()
            end_time = datetime.now()

            xm.disconnect()

            logger.info("DAQ recording completed")
            result_queue.put(
                {
                    "ecu": ecu_name,
                    "success": True,
                    "start_time": start_time.isoformat(),
                    "end_time": end_time.isoformat(),
                    "duration": (end_time - start_time).total_seconds(),
                }
            )

    except Exception as e:
        logger.error(f"DAQ error: {e}", exc_info=True)
        result_queue.put({"ecu": ecu_name, "success": False, "error": str(e)})


def example_parallel_daq_recording():
    """Example 2: Parallel DAQ recording from multiple ECUs."""
    print("\n" + "=" * 80)
    print("Example 2: Parallel DAQ Recording")
    print("=" * 80)

    duration = 5  # seconds

    # Define ECUs with their config files
    examples_dir = Path(__file__).parent

    ecus = [
        {
            "name": "CAN_ECU",
            "config_file": str(examples_dir / "conf_cv.py"),
        },
        {
            "name": "ETH_ECU",
            "config_file": str(examples_dir / "conf_eth.py"),
        },
    ]

    result_queue = multiprocessing.Queue()
    processes = []

    print(f"\nStarting DAQ recording from {len(ecus)} ECUs for {duration} seconds...")

    # Start DAQ processes
    for ecu in ecus:
        process = multiprocessing.Process(
            target=xcp_daq_worker_process,
            args=(ecu["name"], ecu["config_file"], duration, result_queue),
            name=f"DAQ-{ecu['name']}",
        )
        process.start()
        processes.append({"name": ecu["name"], "process": process})
        print(f"  Started DAQ process for {ecu['name']} (PID: {process.pid})")

    # Progress indicator
    print("\nProgress: [", end="", flush=True)
    for _ in range(duration):
        time.sleep(1)
        print("█", end="", flush=True)
    print("] Done!")

    # Collect results
    print("\nResults:")
    for _ in range(len(ecus)):
        result = result_queue.get(timeout=10.0)
        if result["success"]:
            print(f"  [OK] {result['ecu']:15s} recorded for {result['duration']:.1f}s")
        else:
            print(f"  [FAIL] {result['ecu']:15s} failed: {result['error']}")

    # Wait for all processes
    for proc in processes:
        proc["process"].join(timeout=2.0)

    print("\n*** Example 2 completed!")
    print("\nCSV files created:")
    for ecu in ecus:
        print(f"  - {ecu['name'].lower()}_daq.csv")


def main():
    """Main entry point."""
    print("\n" + "=" * 80)
    print("XCP Multi-Channel Multiprocessing Example")
    print("=" * 80)
    print("\nThis example demonstrates TRUE parallel XCP communication using")
    print("separate Python processes (not threads). Benefits:")
    print("  * Bypasses Python GIL (true parallelism)")
    print("  * Process isolation (one ECU crash doesn't affect others)")
    print("  * Independent memory spaces")
    print("  * Production-grade robustness")
    print("\nNote: Adjust ECU configurations (host, channel, CAN IDs) to match your setup!")

    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "daq":
        example_parallel_daq_recording()
    else:
        example_basic_multiprocessing()

    print("\n" + "=" * 80)
    print("Production Tips:")
    print("=" * 80)
    print("1. Each process has its own Master instance (no sharing!)")
    print("2. Use Queues for inter-process communication")
    print("3. Handle process crashes gracefully with timeouts")
    print("4. Consider using multiprocessing.Pool for many ECUs")
    print("5. Use shared memory (multiprocessing.Array) for high-freq data exchange")
    print("6. Set process names for better debugging")
    print("\nCompare with:")
    print("  - multi_channel_can.py: Threading approach (simpler, shares GIL)")
    print("  - multi_ecu_setup.py: ThreadPoolExecutor patterns (more examples)")


if __name__ == "__main__":
    # Required for Windows
    multiprocessing.freeze_support()
    main()

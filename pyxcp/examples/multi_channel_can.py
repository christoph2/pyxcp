#!/usr/bin/env python
"""
Example: Using multiple CAN channels simultaneously with pyxcp

This example demonstrates how to communicate with multiple ECUs on different
CAN channels at the same time using separate Master instances.

Requirements:
- Multi-channel CAN interface (e.g., Vector CANcase, Kvaser with multiple channels)
- Multiple ECUs or one ECU with multiple CAN interfaces
- python-can with appropriate interface driver

Author: pyxcp contributors
License: GPLv2
"""

import logging
import threading
from pyxcp import Master
from pyxcp.config import PyXCP

# Setup logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(name)s] %(levelname)s: %(message)s")
logger = logging.getLogger("multi_channel_example")


def create_can_config(interface="vector", channel="0", can_id_master=0x700, can_id_slave=0x701):
    """Create a CAN configuration for a specific channel.

    Parameters
    ----------
    interface : str
        CAN interface type (e.g., "vector", "kvaser", "socketcan")
    channel : str
        Channel number (e.g., "0", "1", "vcan0")
    can_id_master : int
        CAN ID for Master → Slave messages (Tx)
    can_id_slave : int
        CAN ID for Slave → Master messages (Rx)

    Returns
    -------
    PyXCP
        Configured PyXCP instance
    """
    app = PyXCP()

    # Transport configuration
    app.transport.layer = "CAN"
    app.transport.can.interface = interface
    app.transport.can.channel = channel
    app.transport.can.can_id_master = can_id_master
    app.transport.can.can_id_slave = can_id_slave
    app.transport.can.bitrate = 500_000

    # Optional: Configure for CAN-FD
    # app.transport.can.fd = True
    # app.transport.can.data_bitrate = 2_000_000

    # Optional: Vector-specific settings
    if interface == "vector":
        # app.transport.can.vector.app_name = "XCPsim"  # Use for CANape/XCPsim
        pass

    return app


def daq_session_thread(name, config, measurements_to_read=10):
    """Run a DAQ session on a separate thread.

    Parameters
    ----------
    name : str
        Name identifier for this session (e.g., "ECU1", "ECU2")
    config : PyXCP
        Configuration for this Master instance
    measurements_to_read : int
        Number of DAQ measurements to read before stopping
    """
    logger.info(f"[{name}] Starting DAQ session on channel {config.transport.can.channel}")

    try:
        with Master("can", config=config) as xm:
            # Connect to ECU
            xm.connect()
            logger.info(f"[{name}] Connected to XCP slave")

            # Example: Get basic ECU info
            ecu_id = xm.getId(0x01)  # Get ECU identification
            logger.info(f"[{name}] ECU ID: {ecu_id}")

            # Example: Read memory
            # data = xm.shortUpload(address=0x1000, length=4)
            # logger.info(f"[{name}] Memory read: {data.hex()}")

            # Example: Setup DAQ (commented out - requires configuration)
            # from pyxcp.daq_stim import DaqList, DaqListEntry
            # daq_list = DaqList(
            #     name=f"daq_{name.lower()}",
            #     event_num=0,
            #     entries=[
            #         DaqListEntry(name="signal1", address=0x1000, size=4),
            #         DaqListEntry(name="signal2", address=0x1004, size=2),
            #     ]
            # )
            # xm.setupDaq([daq_list])
            # xm.startDaqList(0)

            # # Read DAQ data
            # for i in range(measurements_to_read):
            #     data = xm.daqQueue.get(timeout=1.0)
            #     logger.info(f"[{name}] DAQ data #{i}: {data}")

            # xm.stopAllDaqLists()

            # Disconnect
            xm.disconnect()
            logger.info(f"[{name}] Session completed successfully")

    except Exception as e:
        logger.error(f"[{name}] Error during DAQ session: {e}", exc_info=True)


def main_sequential():
    """Example 1: Sequential multi-channel access.

    Connect to each ECU one after another. Simpler but slower.
    """
    logger.info("=== Sequential Multi-Channel Example ===")

    # Configuration for ECU 1 on Channel 0
    config_ecu1 = create_can_config(
        interface="vector",
        channel="0",
        can_id_master=0x700,
        can_id_slave=0x701,
    )

    # Configuration for ECU 2 on Channel 1
    config_ecu2 = create_can_config(
        interface="vector",
        channel="1",
        can_id_master=0x710,
        can_id_slave=0x711,
    )

    # Access ECU 1
    logger.info("Connecting to ECU1...")
    daq_session_thread("ECU1", config_ecu1, measurements_to_read=5)

    # Access ECU 2
    logger.info("Connecting to ECU2...")
    daq_session_thread("ECU2", config_ecu2, measurements_to_read=5)

    logger.info("Sequential example completed")


def main_parallel():
    """Example 2: Parallel multi-channel access.

    Connect to multiple ECUs simultaneously using threads.
    Faster but requires careful thread management.
    """
    logger.info("=== Parallel Multi-Channel Example ===")

    # Configuration for ECU 1 on Channel 0
    config_ecu1 = create_can_config(
        interface="vector",
        channel="0",
        can_id_master=0x700,
        can_id_slave=0x701,
    )

    # Configuration for ECU 2 on Channel 1
    config_ecu2 = create_can_config(
        interface="vector",
        channel="1",
        can_id_master=0x710,
        can_id_slave=0x711,
    )

    # Start threads for each ECU
    thread_ecu1 = threading.Thread(
        target=daq_session_thread,
        args=("ECU1", config_ecu1, 10),
        name="ECU1-Thread",
    )
    thread_ecu2 = threading.Thread(
        target=daq_session_thread,
        args=("ECU2", config_ecu2, 10),
        name="ECU2-Thread",
    )

    # Start both threads
    logger.info("Starting parallel DAQ sessions...")
    thread_ecu1.start()
    thread_ecu2.start()

    # Wait for both to complete
    thread_ecu1.join()
    thread_ecu2.join()

    logger.info("Parallel example completed")


if __name__ == "__main__":
    # Choose example to run
    import sys

    if len(sys.argv) > 1 and sys.argv[1] == "parallel":
        main_parallel()
    else:
        logger.info("Usage: python multi_channel_can.py [sequential|parallel]")
        logger.info("Running sequential example (default)...")
        main_sequential()

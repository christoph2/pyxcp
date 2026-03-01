#!/usr/bin/env python
"""
Quick test of XCP 1.5 time correlation features with localhost server.

This is a simplified version for testing without config files.
"""

import sys
import time

import pyxcp
from pyxcp.events import TimeSyncEventHandler
from pyxcp.time_correlation import GetPropertiesRequest, ResponseFormat, TimeSyncBridge


def test_time_correlation():
    """Test XCP 1.5 time correlation features."""
    print("=" * 80)
    print("XCP 1.5 TIME CORRELATION TEST")
    print("=" * 80)

    # Connect to localhost server
    print("\n→ Connecting to 127.0.0.1:5555...")
    with pyxcp.connect(transport="eth", host="127.0.0.1", port=5555) as master:
        print("✓ Connected to XCP slave")
        print(
            f"  Protocol: XCP {master.slaveProperties.protocolLayerVersion >> 8}.{master.slaveProperties.protocolLayerVersion & 0xFF}"
        )

        # Setup event handler
        print("\n→ Setting up TimeSyncEventHandler...")
        time_sync_handler = TimeSyncEventHandler()
        master.add_event_handler(time_sync_handler)
        print("✓ Event handler registered")

        # Try TIME_CORRELATION_PROPERTIES
        print("\n" + "=" * 80)
        print("STEP 1: TIME_CORRELATION_PROPERTIES Command")
        print("=" * 80)

        try:
            response = master.timeCorrelationProperties(
                response_fmt=ResponseFormat.ALL_TRIGGERS,
                time_sync_bridge=TimeSyncBridge.NOT_AVAILABLE,
                set_cluster_id=True,
                cluster_id=0x0001,
                get_clk_info=GetPropertiesRequest.GET_ALL,
            )

            print("\n✓ TIME_CORRELATION_PROPERTIES successful!")
            print("\nSlave Config:")
            print(f"  Response Format:    {response.slave_config.response_format.name}")
            print(f"  Max Cluster ID:     {response.slave_config.max_cluster_id}")
            print(f"  Time Sync Bridge:   {response.slave_config.time_sync_bridge.name}")

            print("\nObservable Clocks:")
            print(f"  XCP_SLV Clock:      {response.observable_clocks.xcp_slv_clk.name}")
            print(f"  Grandmaster Clock:  {response.observable_clocks.grandm_clk.name}")
            print(f"  ECU Clock:          {response.observable_clocks.ecu_clk.name}")

            print("\nSync State:")
            print(f"  Slave Clock:        {response.sync_state.slave_clk_sync_state.name}")
            print(f"  Grandmaster Clock:  {response.sync_state.grandm_clk_sync_state.name}")
            print(f"  ECU Clock:          {response.sync_state.ecu_clk_sync_state.name}")

            print("\nClock Info:")
            print(f"  Info Available:     {response.clock_info.info_available}")
            print(f"  Relation Available: {response.clock_info.relation_available}")
            print(f"  ECU Info Available: {response.clock_info.ecu_info_available}")

        except Exception as e:
            print(f"\n✗ TIME_CORRELATION_PROPERTIES failed: {e}")
            print("\n  This is expected for XCP 1.4 servers")
            print("  Server response indicates no support for this command")

        # Try GET_DAQ_CLOCK_MULTICAST
        print("\n" + "=" * 80)
        print("STEP 2: GET_DAQ_CLOCK_MULTICAST Commands")
        print("=" * 80)

        # Setup multicast socket
        cluster_id = 0x0001
        multicast_addr = f"239.255.{(cluster_id >> 8) & 0xFF}.{cluster_id & 0xFF}"

        print("\n→ Setting up multicast socket...")
        print(f"  Cluster ID:         0x{cluster_id:04X}")
        print(f"  Multicast address:  {multicast_addr}:5557")

        try:
            master.transport.enable_multicast(cluster_id)
            print("✓ Multicast enabled on master transport")
        except Exception as e:
            print(f"✗ Multicast setup failed: {e}")
            return

        # Send a few multicast commands
        print("\n→ Sending 5 GET_DAQ_CLOCK_MULTICAST commands...")

        for i in range(5):
            try:
                print(f"  [{i + 1}/5] Counter {i}... ", end="", flush=True)

                master.getDaqClockMulticast(cluster_id=cluster_id, trigger_mode=0, counter_value=i)

                # Check for event
                last_event = time_sync_handler.get_last_sync_event()
                if last_event:
                    print("✓ EV_TIME_SYNC received")
                else:
                    print("⚠ No EV_TIME_SYNC (expected for XCP 1.4)")

                time.sleep(0.5)

            except Exception as e:
                print(f"✗ Error: {e}")

        print("\n" + "=" * 80)
        print("TEST COMPLETE")
        print("=" * 80)


if __name__ == "__main__":
    try:
        test_time_correlation()
    except KeyboardInterrupt:
        print("\n\nInterrupted by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n\nFatal error: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)

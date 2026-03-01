#!/usr/bin/env python
"""
Test GET_DAQ_CLOCK_MULTICAST against localhost XCP server

Server log shows:
  Listening for TCP connections on 0.0.0.0 port 5555
  Listening for XCP multicast on 239.255.0.1:5557
"""

import time
from pyxcp import Master
from pyxcp.config import create_application_from_config, set_application


def test_multicast():
    print("=" * 70)
    print("XCP 1.5 GET_DAQ_CLOCK_MULTICAST Test")
    print("=" * 70)
    print("\nConnecting to localhost XCP server (TCP on 5555)...")

    # Use modern config format with DEBUG logging
    config = {
        "Transport": {
            "Eth": {
                "host": "localhost",
                "port": 5555,
                "protocol": "TCP",
            }
        },
        "General": {"loglevel": "DEBUG"},
    }

    app = create_application_from_config(config)
    set_application(app)

    # Pass app as config to Master
    with Master("eth", app) as x:
        x.connect()
        print("OK Connected")

        # Get DAQ info
        print("\nQuerying DAQ capabilities...")
        daq_info = x.getDaqInfo(include_event_lists=False)
        print(f"  DAQ Processor: {daq_info['processor']}")
        print(f"  Resolution: {daq_info['resolution']}")

        # Enable multicast on transport
        print("\nEnabling UDP multicast...")
        cluster_id = 0x0001  # → 239.255.0.1
        x.transport.enable_multicast(cluster_id)
        print(f"OK Multicast enabled: cluster_id={cluster_id:#06x}")

        # Send GET_DAQ_CLOCK_MULTICAST commands
        print("\nSending GET_DAQ_CLOCK_MULTICAST commands...")
        for counter in range(3):
            print(f"\n[{counter + 1}/3] Sending multicast (counter={counter})...")
            x.getDaqClockMulticast(cluster_id=cluster_id, counter=counter)

            # Wait for EV_TIME_SYNC response (comes asynchronously)
            print("      Waiting for EV_TIME_SYNC event (2 seconds)...")
            time.sleep(2)

            # Check if TimeSyncEventHandler captured it
            handler = x.transport.event_handler
            while handler:
                if hasattr(handler, "last_sync_event") and handler.last_sync_event:
                    event = handler.last_sync_event
                    print("      OK EV_TIME_SYNC received:")
                    print(f"        - Mode: {'Legacy' if event.is_legacy else 'Extended'}")
                    print(f"        - Trigger: {event.trigger_info.initiator.name}")
                    if event.xcp_slave_timestamp:
                        print(f"        - XCP Slave TS: {event.xcp_slave_timestamp:#x}")
                    if event.counter is not None:
                        print(f"        - Counter: {event.counter} (expected: {counter})")
                        if event.counter != counter:
                            print("          WARNING: Counter mismatch!")
                    break
                handler = handler._next_handler
            else:
                print("      WARNING: No EV_TIME_SYNC event captured (check server logs)")

        print("\n" + "=" * 70)
        print("SUCCESS: Multicast test complete!")
        print("=" * 70)

        x.disconnect()


if __name__ == "__main__":
    try:
        test_multicast()
    except KeyboardInterrupt:
        print("\n\nWARNING: Test interrupted by user")
    except Exception as e:
        print(f"\n\nERROR: Test failed: {e}")
        import traceback

        traceback.print_exc()

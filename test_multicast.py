#!/usr/bin/env python
"""
Test GET_DAQ_CLOCK_MULTICAST against localhost XCP server

This test demonstrates XCP 1.5 advanced time correlation:
1. Enable extended mode via TIME_CORRELATION_PROPERTIES
2. Assign slave to cluster ID
3. Send GET_DAQ_CLOCK_MULTICAST commands
4. Receive EV_TIME_SYNC events with counter correlation

Server log shows:
  Listening for TCP connections on 0.0.0.0 port 5555
  Listening for XCP multicast on 239.255.0.1:5557
"""

import time

from pyxcp import Master
from pyxcp.config import create_application_from_config, set_application


def test_multicast():
    print("=" * 70)
    print("XCP 1.5 TIME_CORRELATION_PROPERTIES + GET_DAQ_CLOCK_MULTICAST Test")
    print("=" * 70)
    print("\nConnecting to localhost XCP server (TCP on 5555)...")

    # Use modern config format
    config = {
        "Transport": {"Eth": {"host": "localhost", "port": 5555, "protocol": "TCP"}},
        "General": {"loglevel": "INFO"},
    }

    app = create_application_from_config(config)
    set_application(app)

    # Pass app as config to Master
    with Master("eth", app) as x:
        x.connect()
        print("OK Connected")

        # Step 1: Enable Advanced Time Correlation Features
        print("\n" + "=" * 70)
        print("STEP 1: Enable Advanced Time Correlation (XCP 1.5)")
        print("=" * 70)

        cluster_id = 0x0001  # Maps to multicast address 239.255.0.1
        print("\nSending TIME_CORRELATION_PROPERTIES...")
        print("  - Response Format: 2 (ALL_TRIGGERS)")
        print(f"  - Cluster ID: {cluster_id:#06x} (assign to logical cluster)")
        print("  - Get Clock Info: True (request clock details)")

        tc_resp = None
        try:
            tc_resp = x.timeCorrelationProperties(
                response_fmt=2,  # ALL_TRIGGERS - enable all EV_TIME_SYNC
                set_cluster_id=True,  # Assign to cluster
                cluster_id=cluster_id,
                get_clk_info=True,  # Request clock info for UPLOAD
            )
            print("\nOK TIME_CORRELATION_PROPERTIES succeeded!")
            print(f"\n{tc_resp}")

        except Exception as e:
            print(f"\nWARNING: TIME_CORRELATION_PROPERTIES failed: {e}")
            print("  Server might not support XCP 1.5 time correlation")
            print("  Continuing with GET_DAQ_CLOCK_MULTICAST anyway...")

        # Step 2: Upload Clock Information (if available)
        print("\n" + "=" * 70)
        print("STEP 2: Upload Clock Information")
        print("=" * 70)

        if tc_resp:
            try:
                if tc_resp.clock_info.slv_clk_info:
                    print("\nUploading XCP slave clock info (24 bytes)...")
                    clk_data = x.upload(24)
                    from pyxcp.time_correlation import ClockInformation

                    slv_clk = ClockInformation.parse(clk_data, has_epoch=False)
                    print(f"\n{slv_clk}")
                else:
                    print("\nNo XCP slave clock info available")

            except Exception as e:
                print(f"\nWARNING: Clock info upload failed: {e}")
        else:
            print("\nSkipping clock info upload (Step 1 failed)")

        # Step 3: Enable UDP Multicast
        print("\n" + "=" * 70)
        print("STEP 3: Enable UDP Multicast Socket")
        print("=" * 70)

        print(f"\nEnabling UDP multicast for cluster {cluster_id:#06x}...")
        x.transport.enable_multicast(cluster_id)
        print("OK Multicast socket bound to 239.255.0.1:5557")

        # Step 4: Send GET_DAQ_CLOCK_MULTICAST Commands
        print("\n" + "=" * 70)
        print("STEP 4: Send GET_DAQ_CLOCK_MULTICAST Commands")
        print("=" * 70)

        print("\nSending 3 multicast commands...")
        for counter in range(3):
            print(f"\n[{counter + 1}/3] GET_DAQ_CLOCK_MULTICAST (counter={counter})...")
            x.getDaqClockMulticast(cluster_id=cluster_id, counter=counter)

            # Wait for EV_TIME_SYNC response (comes asynchronously)
            print("      Waiting for EV_TIME_SYNC event (2 seconds)...")
            time.sleep(2)

            # Check if TimeSyncEventHandler captured it
            handler = x.transport.event_handler
            found = False
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
                        else:
                            print("          OK Counter matches!")
                    found = True
                    break
                handler = handler._next_handler

            if not found:
                print("      WARNING: No EV_TIME_SYNC event captured")
                print("        Possible reasons:")
                print("        - Server doesn't support XCP 1.5 time correlation")
                print("        - Response format not enabled (check Step 1)")
                print("        - Events come too late (increase wait time)")

        # Summary
        print("\n" + "=" * 70)
        print("TEST SUMMARY")
        print("=" * 70)
        print("\nCompleted XCP 1.5 time correlation test:")
        print("  1. TIME_CORRELATION_PROPERTIES: Feature enablement")
        print("  2. Clock information upload: Clock UUID and characteristics")
        print("  3. UDP multicast socket: Bound to 239.255.0.1:5557")
        print("  4. GET_DAQ_CLOCK_MULTICAST: 3 commands sent")
        print("\nIf no EV_TIME_SYNC events received:")
        print("  - Check server supports XCP 1.5 (TIME_CORRELATION_PROPERTIES)")
        print("  - Verify server listening on multicast address")
        print("  - Check firewall allows UDP multicast traffic")
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

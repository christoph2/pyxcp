#!/usr/bin/env python
"""
XCP 1.5 Advanced Time Correlation - Comprehensive Example
==========================================================

This example demonstrates all XCP 1.5 time correlation features:
1. Event Handler System (EV_TIME_SYNC, EV_DAQ_OVERLOAD, etc.)
2. TIME_CORRELATION_PROPERTIES command (feature enablement & clock info)
3. GET_DAQ_CLOCK_MULTICAST (synchronized timestamp sampling)
4. Clock Information Upload (UUID, stratum, epoch)
5. All three time correlation techniques

Prerequisites:
- XCP 1.5 compliant server
- UDP transport configured
- Slave must support TIME_CORRELATION_PROPERTIES (optional feature)

Usage:
    python xcp15_time_correlation.py --host 192.168.1.100 --port 5555
    python xcp15_time_correlation.py --config config.toml
"""

import socket
import time
from datetime import datetime

from pyxcp.cmdline import ArgumentParser
from pyxcp.events import (
    DaqStimEventHandler,
    SessionStateEventHandler,
    TimeSyncEventHandler,
    TransportEventHandler,
    UserEventHandler,
)
from pyxcp.time_correlation import (
    ClockInformation,
    ClockRelation,
    EcuGrandmasterClockInfo,
    GetPropertiesRequest,
    ResponseFormat,
    TimeSyncBridge,
)


class TimeCorrelationDemo:
    """XCP 1.5 Time Correlation demonstration with all features."""

    def __init__(self, master):
        self.master = master
        self.multicast_socket = None
        self.cluster_id = 0x0001  # Default cluster
        self.sync_events = []
        self.clock_info = {}

    def setup_event_handlers(self):
        """Configure all event handlers for comprehensive event monitoring."""
        print("\n" + "=" * 80)
        print("STEP 1: Event Handler Setup")
        print("=" * 80)

        # Transport events (ETH specific)
        transport_handler = TransportEventHandler()
        self.master.add_event_handler(transport_handler)
        print("✓ TransportEventHandler registered (ETH events)")

        # Time sync events (EV_TIME_SYNC)
        time_sync_handler = TimeSyncEventHandler()
        self.master.add_event_handler(time_sync_handler)
        self.time_sync_handler = time_sync_handler
        print("✓ TimeSyncEventHandler registered (EV_TIME_SYNC)")

        # Session state events
        session_handler = SessionStateEventHandler()
        self.master.add_event_handler(session_handler)
        print("✓ SessionStateEventHandler registered (session changes)")

        # DAQ/STIM events (EV_DAQ_OVERLOAD, etc.)
        daq_handler = DaqStimEventHandler()
        self.master.add_event_handler(daq_handler)
        print("✓ DaqStimEventHandler registered (DAQ/STIM events)")

        # Custom user event handler
        user_handler = UserEventHandler()
        self.master.add_event_handler(user_handler)
        print("✓ UserEventHandler registered (custom events)")

        print(f"\n→ {len(self.master.event_handlers)} event handlers active")

    def enable_time_correlation(self):
        """Enable XCP 1.5 time correlation features via TIME_CORRELATION_PROPERTIES."""
        print("\n" + "=" * 80)
        print("STEP 2: Enable XCP 1.5 Time Correlation Features")
        print("=" * 80)

        try:
            # Request extended response format (8 bytes) and full clock info
            print("\n→ Sending TIME_CORRELATION_PROPERTIES command...")
            print("  - Response Format: EXTENDED (8 bytes)")
            print("  - Get Properties: ALL (slave config + clocks + sync state + info)")
            print(f"  - Cluster ID: 0x{self.cluster_id:04X}")

            response = self.master.timeCorrelationProperties(
                response_fmt=ResponseFormat.EXTENDED,
                time_sync_bridge=TimeSyncBridge.NO_BRIDGE,
                set_cluster_id=True,
                cluster_id=self.cluster_id,
                get_clk_info=GetPropertiesRequest.GET_ALL,
            )

            print("\n✓ TIME_CORRELATION_PROPERTIES successful!")
            print("\n" + "-" * 40)
            print("SLAVE CONFIGURATION:")
            print("-" * 40)

            # Parse and display slave config
            slave_cfg = response.slave_config
            print(f"Response Format:     {slave_cfg.response_format.name}")
            print(f"Max Cluster ID:      {slave_cfg.max_cluster_id}")
            print(f"Time Sync Bridge:    {slave_cfg.time_sync_bridge.name}")

            # Parse and display observable clocks
            print("\n" + "-" * 40)
            print("OBSERVABLE CLOCKS:")
            print("-" * 40)
            obs_clocks = response.observable_clocks
            print(f"XCP_SLV Clock:       {obs_clocks.xcp_slv_clk.name}")
            print(f"Grandmaster Clock:   {obs_clocks.grandm_clk.name}")
            print(f"ECU Clock:           {obs_clocks.ecu_clk.name}")

            # Parse and display sync states
            print("\n" + "-" * 40)
            print("SYNCHRONIZATION STATE:")
            print("-" * 40)
            sync_state = response.sync_state
            print(f"Slave Clock:         {sync_state.slave_clk_sync_state.name}")
            print(f"Grandmaster Clock:   {sync_state.grandm_clk_sync_state.name}")
            print(f"ECU Clock:           {sync_state.ecu_clk_sync_state.name}")

            # Check if clock info upload is available
            print("\n" + "-" * 40)
            print("CLOCK INFORMATION:")
            print("-" * 40)
            clock_info = response.clock_info
            print(f"Info Available:      {clock_info.info_available}")
            print(f"Relation Available:  {clock_info.relation_available}")
            print(f"ECU Info Available:  {clock_info.ecu_info_available}")

            if clock_info.info_available:
                print("\n→ Clock information can be uploaded")
                print("  Upload addresses:")
                print(f"  - Clock Info:      0x{clock_info.info_addr:08X} (24 bytes)")
                if clock_info.relation_available:
                    print(f"  - Clock Relation:  0x{clock_info.relation_addr:08X} (16 bytes)")
                if clock_info.ecu_info_available:
                    print(f"  - ECU Grandmaster: 0x{clock_info.ecu_info_addr:08X} (8 bytes)")

            # Store for later
            self.response = response
            return response

        except Exception as e:
            print(f"\n✗ TIME_CORRELATION_PROPERTIES failed: {e}")
            print("\n  Possible reasons:")
            print("  - Server is XCP 1.4 (doesn't support TIME_CORRELATION_PROPERTIES)")
            print("  - Feature not implemented on slave")
            print("  - Slave not in correct state")
            return None

    def upload_clock_information(self):
        """Upload and parse clock information structures."""
        print("\n" + "=" * 80)
        print("STEP 3: Upload Clock Information")
        print("=" * 80)

        if not hasattr(self, "response") or self.response is None:
            print("\n✗ Skipped (TIME_CORRELATION_PROPERTIES not successful)")
            return

        clock_info = self.response.clock_info

        if not clock_info.info_available:
            print("\n→ Clock information not available from slave")
            return

        try:
            # Upload main clock information (24 bytes)
            print(f"\n→ Uploading Clock Information from 0x{clock_info.info_addr:08X}...")
            self.master.setMta(clock_info.info_addr)
            data = self.master.upload(24)
            clk_info = ClockInformation.parse(data)

            print("\n" + "-" * 40)
            print("CLOCK INFORMATION:")
            print("-" * 40)
            print(f"Clock UUID:          {clk_info.uuid_string()}")
            print(f"Stratum Level:       {clk_info.stratum_level}")
            if clk_info.stratum_level == 255:
                print("                     (Unknown/Not synchronized)")
            print(f"Native TS Size:      {clk_info.native_timestamp_size} bytes")
            print(f"TS Ticks per Second: {clk_info.timestamp_ticks_per_second}")
            print(f"Epoch:               {clk_info.epoch.name}")

            self.clock_info["main"] = clk_info

            # Upload clock relation if available (16 bytes)
            if clock_info.relation_available:
                print(f"\n→ Uploading Clock Relation from 0x{clock_info.relation_addr:08X}...")
                self.master.setMta(clock_info.relation_addr)
                data = self.master.upload(16)
                relation = ClockRelation.parse(data)

                print("\n" + "-" * 40)
                print("CLOCK RELATION (Timestamp Tuples):")
                print("-" * 40)
                print(f"XCP Slave TS:        {relation.xcp_slave_timestamp}")
                print(f"Grandmaster TS:      {relation.grandmaster_timestamp}")
                print(f"→ Clock offset:      {relation.grandmaster_timestamp - relation.xcp_slave_timestamp} ticks")

                self.clock_info["relation"] = relation

            # Upload ECU/Grandmaster info if available (8 bytes)
            if clock_info.ecu_info_available:
                print(f"\n→ Uploading ECU Grandmaster Info from 0x{clock_info.ecu_info_addr:08X}...")
                self.master.setMta(clock_info.ecu_info_addr)
                data = self.master.upload(8)
                ecu_info = EcuGrandmasterClockInfo.parse(data)

                print("\n" + "-" * 40)
                print("ECU/GRANDMASTER INFO:")
                print("-" * 40)
                print(f"ECU Clock UUID:      {ecu_info.uuid_string()}")

                self.clock_info["ecu"] = ecu_info

            print("\n✓ Clock information uploaded successfully")

        except Exception as e:
            print(f"\n✗ Clock information upload failed: {e}")

    def setup_multicast(self):
        """Configure UDP multicast socket for GET_DAQ_CLOCK_MULTICAST."""
        print("\n" + "=" * 80)
        print("STEP 4: UDP Multicast Setup")
        print("=" * 80)

        transport = self.master.transport

        # Check if transport supports multicast
        if not hasattr(transport, "enable_multicast"):
            print("\n✗ Transport does not support multicast (need UDP/ETH transport)")
            return False

        try:
            # Enable multicast on master transport
            multicast_addr = transport.cluster_id_to_multicast_address(self.cluster_id)
            print(f"\n→ Enabling multicast for cluster 0x{self.cluster_id:04X}")
            print(f"  Multicast address: {multicast_addr}:5557")

            transport.enable_multicast(self.cluster_id)
            print("✓ Multicast socket bound successfully")

            # Create listener socket for demonstration
            self.multicast_socket = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
            self.multicast_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self.multicast_socket.bind(("", 5557))

            # Join multicast group
            mreq = socket.inet_aton(multicast_addr) + socket.inet_aton("0.0.0.0")  # nosec B104
            self.multicast_socket.setsockopt(socket.IPPROTO_IP, socket.IP_ADD_MEMBERSHIP, mreq)
            self.multicast_socket.settimeout(0.5)  # Non-blocking

            print("✓ Listener socket joined multicast group")
            return True

        except Exception as e:
            print(f"\n✗ Multicast setup failed: {e}")
            return False

    def send_multicast_commands(self, count=10, interval=1.0):
        """Send GET_DAQ_CLOCK_MULTICAST commands and monitor responses."""
        print("\n" + "=" * 80)
        print("STEP 5: GET_DAQ_CLOCK_MULTICAST Commands")
        print("=" * 80)

        print(f"\n→ Sending {count} multicast commands (interval: {interval}s)")
        print(f"  Cluster ID: 0x{self.cluster_id:04X}")
        print("  Trigger Mode: EXT (External)")
        print()

        for i in range(count):
            try:
                # Send multicast command with incrementing counter
                counter = i
                print(f"[{i + 1:2d}/{count}] Counter {counter:3d}: ", end="", flush=True)

                self.master.getDaqClockMulticast(cluster_id=self.cluster_id, trigger_mode=0, counter_value=counter)

                # Check for multicast packet on socket
                if self.multicast_socket:
                    try:
                        data, addr = self.multicast_socket.recvfrom(1024)
                        print(f"Multicast RX from {addr[0]} ({len(data)} bytes) ", end="")
                    except socket.timeout:
                        print("No multicast packet ", end="")

                # Check for EV_TIME_SYNC event
                last_event = self.time_sync_handler.get_last_sync_event()
                if last_event:
                    # Parse counter from event
                    trigger_info = last_event.trigger_info
                    if hasattr(trigger_info, "counter_value"):
                        if trigger_info.counter_value == counter:
                            print(f"✓ EV_TIME_SYNC (counter={counter})")
                            self.sync_events.append(last_event)
                        else:
                            print(f"⚠ EV_TIME_SYNC (counter mismatch: {trigger_info.counter_value})")
                    else:
                        print("✓ EV_TIME_SYNC (legacy format)")
                else:
                    print("⚠ No EV_TIME_SYNC event")

                time.sleep(interval)

            except Exception as e:
                print(f"✗ Error: {e}")
                continue

        print(f"\n→ Received {len(self.sync_events)} EV_TIME_SYNC events")

    def analyze_results(self):
        """Analyze collected time sync events and display statistics."""
        print("\n" + "=" * 80)
        print("STEP 6: Analysis & Statistics")
        print("=" * 80)

        if not self.sync_events:
            print("\n⚠ No EV_TIME_SYNC events received")
            print("\nPossible reasons:")
            print("1. Server is XCP 1.4 (no TIME_CORRELATION_PROPERTIES support)")
            print("2. TIME_CORRELATION_PROPERTIES not called before multicast")
            print("3. response_fmt=0 (legacy mode, no extended events)")
            print("4. Multicast packets filtered by network/firewall")
            print("5. Slave doesn't support GET_DAQ_CLOCK_MULTICAST")
            return

        print(f"\n→ Analyzing {len(self.sync_events)} time sync events...")

        # Extract timestamps
        master_timestamps = []
        slave_timestamps = []
        counters = []

        for event in self.sync_events:
            trigger_info = event.trigger_info
            payload = event.payload

            if hasattr(trigger_info, "counter_value"):
                counters.append(trigger_info.counter_value)

            # Master sent timestamp (from trigger_info)
            if hasattr(trigger_info, "master_timestamp"):
                master_timestamps.append(trigger_info.master_timestamp)

            # Slave sampled timestamp (from payload)
            if payload and hasattr(payload, "xcp_slave_timestamp"):
                slave_timestamps.append(payload.xcp_slave_timestamp)

        # Display statistics
        print("\n" + "-" * 40)
        print("COUNTER CORRELATION:")
        print("-" * 40)
        if counters:
            print(f"Received counters:   {counters}")
            print(f"Counter range:       {min(counters)} - {max(counters)}")
            missing = set(range(min(counters), max(counters) + 1)) - set(counters)
            if missing:
                print(f"Missing counters:    {sorted(missing)}")
            else:
                print("Missing counters:    None (100% reception)")

        print("\n" + "-" * 40)
        print("TIMESTAMP ANALYSIS:")
        print("-" * 40)

        if slave_timestamps:
            print(f"Slave timestamps:    {len(slave_timestamps)} samples")
            print(f"First timestamp:     {slave_timestamps[0]}")
            print(f"Last timestamp:      {slave_timestamps[-1]}")
            duration = slave_timestamps[-1] - slave_timestamps[0]
            print(f"Duration:            {duration} ticks")

            # Calculate tick rate if clock info available
            if "main" in self.clock_info:
                ticks_per_sec = self.clock_info["main"].timestamp_ticks_per_second
                duration_sec = duration / ticks_per_sec
                print(f"Duration (seconds):  {duration_sec:.3f}s")

            # Calculate jitter
            if len(slave_timestamps) > 2:
                intervals = [slave_timestamps[i + 1] - slave_timestamps[i] for i in range(len(slave_timestamps) - 1)]
                avg_interval = sum(intervals) / len(intervals)
                max_jitter = max(abs(iv - avg_interval) for iv in intervals)
                print(f"Avg interval:        {avg_interval:.1f} ticks")
                print(f"Max jitter:          {max_jitter:.1f} ticks")

        # Display first and last events
        if len(self.sync_events) >= 2:
            print("\n" + "-" * 40)
            print("FIRST EVENT:")
            print("-" * 40)
            self._display_event(self.sync_events[0])

            print("\n" + "-" * 40)
            print("LAST EVENT:")
            print("-" * 40)
            self._display_event(self.sync_events[-1])

    def _display_event(self, event):
        """Display detailed information about a time sync event."""
        trigger = event.trigger_info
        payload = event.payload

        print(f"Trigger Initiator:   {trigger.trigger_initiator.name}")
        if hasattr(trigger, "counter_value"):
            print(f"Counter Value:       {trigger.counter_value}")
        if hasattr(trigger, "master_timestamp"):
            print(f"Master Timestamp:    {trigger.master_timestamp}")

        if payload:
            if hasattr(payload, "xcp_slave_timestamp"):
                print(f"XCP Slave TS:        {payload.xcp_slave_timestamp}")
            if hasattr(payload, "grandmaster_timestamp"):
                print(f"Grandmaster TS:      {payload.grandmaster_timestamp}")
            if hasattr(payload, "ecu_timestamp"):
                print(f"ECU TS:              {payload.ecu_timestamp}")

    def cleanup(self):
        """Clean up resources."""
        if self.multicast_socket:
            try:
                self.multicast_socket.close()
            except Exception:  # nosec B110
                pass  # Cleanup errors can be safely ignored

    def run(self):
        """Execute complete time correlation demonstration."""
        print("\n" + "=" * 80)
        print("XCP 1.5 ADVANCED TIME CORRELATION DEMONSTRATION")
        print("=" * 80)
        print(f"Started: {datetime.now()}")

        try:
            # Step 1: Setup event handlers
            self.setup_event_handlers()

            # Step 2: Enable time correlation features
            response = self.enable_time_correlation()

            if response is None:
                print("\n⚠ TIME_CORRELATION_PROPERTIES not supported")
                print("Continuing with legacy XCP mode (limited features)...")

            # Step 3: Upload clock information
            self.upload_clock_information()

            # Step 4: Setup multicast
            if self.setup_multicast():
                # Step 5: Send multicast commands
                self.send_multicast_commands(count=10, interval=1.0)

                # Step 6: Analyze results
                self.analyze_results()

        finally:
            self.cleanup()

        print("\n" + "=" * 80)
        print("DEMONSTRATION COMPLETE")
        print("=" * 80)


def main():
    """Main entry point."""
    parser = ArgumentParser(description="XCP 1.5 Advanced Time Correlation Example")

    # Add custom arguments
    parser.parser.add_argument(
        "--cluster-id", type=lambda x: int(x, 0), default=0x0001, help="Cluster ID (hex or decimal, default: 0x0001)"
    )

    parser.parser.add_argument("--count", type=int, default=10, help="Number of multicast commands to send (default: 10)")

    parser.parser.add_argument("--interval", type=float, default=1.0, help="Interval between commands in seconds (default: 1.0)")

    # Run with XCP connection
    with parser.run() as x:
        print("\n→ Connected to XCP slave")
        print(f"  Transport: {x.transport.__class__.__name__}")
        print(f"  Protocol: XCP {x.slaveProperties.protocolLayerVersion >> 8}.{x.slaveProperties.protocolLayerVersion & 0xFF}")

        # Check protocol version
        version = x.slaveProperties.protocolLayerVersion
        major = version >> 8
        minor = version & 0xFF

        if major < 1 or (major == 1 and minor < 5):
            print(f"\n⚠ WARNING: Slave reports XCP {major}.{minor} (need 1.5+ for full features)")
            print("  Some features may not be available")

        # Create demo instance
        args = parser.parser.parse_args()
        demo = TimeCorrelationDemo(x)
        demo.cluster_id = args.cluster_id

        # Run demonstration
        demo.run()


if __name__ == "__main__":
    main()

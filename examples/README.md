# pyXCP Examples

This directory contains comprehensive examples demonstrating pyXCP features.

## XCP 1.5 Time Correlation

### test_xcp15.py

Quick test script for XCP 1.5 time correlation features (no config file required).

**Features:**
- TIME_CORRELATION_PROPERTIES command
- GET_DAQ_CLOCK_MULTICAST with counter correlation
- TimeSyncEventHandler integration
- Connects directly to localhost:5555

**Usage:**

```bash
python examples/test_xcp15.py
```

This is the simplest way to test XCP 1.5 features. Great for quick validation and learning.

---

### xcp15_time_correlation.py

Comprehensive demonstration of XCP 1.5 Advanced Time Correlation features with full production-ready workflow.

**Features demonstrated:**
- Event Handler System (5 handler types)
- TIME_CORRELATION_PROPERTIES command
- Clock information upload (UUID, stratum, epoch)
- GET_DAQ_CLOCK_MULTICAST with UDP multicast
- EV_TIME_SYNC event processing
- Counter correlation and timestamp analysis

**Requirements:**
- XCP 1.5 compliant server
- UDP/Ethernet transport
- Slave with TIME_CORRELATION_PROPERTIES support

**Usage:**

```bash
# Basic usage with config file
python xcp15_time_correlation.py --config myconfig.toml

# Direct connection with parameters
python xcp15_time_correlation.py --host 192.168.1.100 --port 5555

# Custom cluster ID and command count
python xcp15_time_correlation.py --config myconfig.toml --cluster-id 0x0005 --count 20

# Adjust multicast interval
python xcp15_time_correlation.py --config myconfig.toml --interval 0.5
```

**Command line options:**

```
--config FILE           XCP configuration file (TOML)
--host HOST            Target IP address
--port PORT            Target port
--cluster-id ID        Cluster ID (hex or decimal, default: 0x0001)
--count N              Number of multicast commands (default: 10)
--interval SECONDS     Interval between commands (default: 1.0)
```

**Example output:**

```
================================================================================
XCP 1.5 ADVANCED TIME CORRELATION DEMONSTRATION
================================================================================
Started: 2026-03-01 11:30:00

→ Connected to XCP slave
  Transport: Eth
  Protocol: XCP 1.5

================================================================================
STEP 1: Event Handler Setup
================================================================================
✓ TransportEventHandler registered (ETH events)
✓ TimeSyncEventHandler registered (EV_TIME_SYNC)
✓ SessionStateEventHandler registered (session changes)
✓ DaqStimEventHandler registered (DAQ/STIM events)
✓ UserEventHandler registered (custom events)

→ 5 event handlers active

================================================================================
STEP 2: Enable XCP 1.5 Time Correlation Features
================================================================================

→ Sending TIME_CORRELATION_PROPERTIES command...
  - Response Format: EXTENDED (8 bytes)
  - Get Properties: ALL (slave config + clocks + sync state + info)
  - Cluster ID: 0x0001

✓ TIME_CORRELATION_PROPERTIES successful!

----------------------------------------
SLAVE CONFIGURATION:
----------------------------------------
Response Format:     EXTENDED
Max Cluster ID:      8
Time Sync Bridge:    NO_BRIDGE

----------------------------------------
OBSERVABLE CLOCKS:
----------------------------------------
XCP_SLV Clock:       FREE_RUNNING
Grandmaster Clock:   CAN_READ
ECU Clock:           CAN_READ

----------------------------------------
SYNCHRONIZATION STATE:
----------------------------------------
Slave Clock:         SYNTONIZED
Grandmaster Clock:   SYNCHRONIZED
ECU Clock:           SYNCHRONIZED

----------------------------------------
CLOCK INFORMATION:
----------------------------------------
Info Available:      True
Relation Available:  True
ECU Info Available:  True

→ Clock information can be uploaded
  Upload addresses:
  - Clock Info:      0x00100000 (24 bytes)
  - Clock Relation:  0x00100018 (16 bytes)
  - ECU Grandmaster: 0x00100028 (8 bytes)

================================================================================
STEP 3: Upload Clock Information
================================================================================

→ Uploading Clock Information from 0x00100000...

----------------------------------------
CLOCK INFORMATION:
----------------------------------------
Clock UUID:          01:23:45:67:89:AB:CD:EF
Stratum Level:       3
Native TS Size:      8 bytes
TS Ticks per Second: 1000000000
Epoch:               TAI

→ Uploading Clock Relation from 0x00100018...

----------------------------------------
CLOCK RELATION (Timestamp Tuples):
----------------------------------------
XCP Slave TS:        1234567890
Grandmaster TS:      9876543210
→ Clock offset:      8641975320 ticks

→ Uploading ECU Grandmaster Info from 0x00100028...

----------------------------------------
ECU/GRANDMASTER INFO:
----------------------------------------
ECU Clock UUID:      FE:DC:BA:98:76:54:32:10

✓ Clock information uploaded successfully

================================================================================
STEP 4: UDP Multicast Setup
================================================================================

→ Enabling multicast for cluster 0x0001
  Multicast address: 239.255.0.1:5557
✓ Multicast socket bound successfully
✓ Listener socket joined multicast group

================================================================================
STEP 5: GET_DAQ_CLOCK_MULTICAST Commands
================================================================================

→ Sending 10 multicast commands (interval: 1.0s)
  Cluster ID: 0x0001
  Trigger Mode: EXT (External)

[ 1/10] Counter   0: Multicast RX from 192.168.1.100 (48 bytes) ✓ EV_TIME_SYNC (counter=0)
[ 2/10] Counter   1: Multicast RX from 192.168.1.100 (48 bytes) ✓ EV_TIME_SYNC (counter=1)
[ 3/10] Counter   2: Multicast RX from 192.168.1.100 (48 bytes) ✓ EV_TIME_SYNC (counter=2)
...
[10/10] Counter   9: Multicast RX from 192.168.1.100 (48 bytes) ✓ EV_TIME_SYNC (counter=9)

→ Received 10 EV_TIME_SYNC events

================================================================================
STEP 6: Analysis & Statistics
================================================================================

→ Analyzing 10 time sync events...

----------------------------------------
COUNTER CORRELATION:
----------------------------------------
Received counters:   [0, 1, 2, 3, 4, 5, 6, 7, 8, 9]
Counter range:       0 - 9
Missing counters:    None (100% reception)

----------------------------------------
TIMESTAMP ANALYSIS:
----------------------------------------
Slave timestamps:    10 samples
First timestamp:     1234567890
Last timestamp:      1243567890
Duration:            9000000 ticks
Duration (seconds):  9.000s
Avg interval:        1000000.0 ticks
Max jitter:          127.5 ticks

================================================================================
DEMONSTRATION COMPLETE
================================================================================
```

**Troubleshooting:**

If TIME_CORRELATION_PROPERTIES fails with 7-byte error response:
- Server is XCP 1.4 (doesn't support TIME_CORRELATION_PROPERTIES)
- Check slave protocol version in connection message

If no EV_TIME_SYNC events received:
- Ensure TIME_CORRELATION_PROPERTIES was called successfully
- Verify response_fmt > 0 (extended mode enabled)
- Check network multicast support (firewall, routing)
- Verify slave supports GET_DAQ_CLOCK_MULTICAST

If multicast packets not received:
- Check firewall rules for UDP port 5557
- Verify multicast routing (ttl, interfaces)
- Test with simple multicast listener tool

## Future Examples

More examples will be added for:
- DAQ/STIM configuration
- A2L file integration
- CAN transport with identifier calculation
- Flash programming
- Multi-slave coordination
- Event recording and playback

#!/usr/bin/env python
"""
XCP 1.5 Time Correlation Support

This module implements TIME_CORRELATION_PROPERTIES command and clock information
structures for advanced time correlation features.

XCP 1.5 introduces three time correlation techniques:
1. XCP Native: GET_DAQ_CLOCK_MULTICAST
2. XCP-unrelated Sync: IEEE 1588 PTP
3. Timestamp Tuples: For resource-limited slaves

Key Features:
- Clock information structures (UUID, ticks, unit, stratum, native size)
- Observable clocks: XCP_SLV, GRANDM, ECU
- Synchronization state tracking
- Time Sync Bridge support (multi-transport correlation)
- Cluster ID management

References:
    XCP 1.5 Spec, Section 7.5.6.1: TIME_CORRELATION_PROPERTIES
"""

import enum
import logging
import struct
from dataclasses import dataclass
from typing import Optional

logger = logging.getLogger(__name__)


# ==============================================================================
# ENUMS FOR BITFIELDS
# ==============================================================================


class ResponseFormat(enum.IntEnum):
    """Response Format for EV_TIME_SYNC and GET_DAQ_CLOCK."""

    LEGACY = 0  # Backward compatibility mode
    TRIGGER_2_3_ONLY = 1  # Only TRIGGER_INITIATOR 0, 2, 3
    ALL_TRIGGERS = 2  # All TRIGGER_INITIATOR values
    RESERVED = 3


class TimeSyncBridge(enum.IntEnum):
    """Time Sync Bridge feature state."""

    NOT_AVAILABLE = 0
    AVAILABLE_DISABLED = 1
    AVAILABLE_ENABLED = 2
    RESERVED = 3


class DaqTimestampRelation(enum.IntEnum):
    """Relation of DAQ timestamps to clocks."""

    XCP_SLAVE_CLOCK = 0
    ECU_CLOCK = 1


class ClockAvailability(enum.IntEnum):
    """Availability and characteristics of a clock."""

    # XCP_SLV_CLK
    XCP_FREE_RUNNING = 0  # Free running, can be read randomly
    XCP_SYNC_CAPABLE = 1  # Might be syntonized/synchronized, can be read
    XCP_NOT_AVAILABLE = 2  # No XCP slave clock (DAQ TS might still exist)
    XCP_RESERVED = 3

    # GRANDM_CLK
    GRANDM_NOT_AVAILABLE = 0
    GRANDM_CAN_READ = 1  # Synchronized, can be read randomly
    GRANDM_AUTONOMOUS_EVENTS = 2  # Cannot read, but autonomously sends EV_TIME_SYNC
    GRANDM_RESERVED = 3

    # ECU_CLK
    ECU_NOT_AVAILABLE = 0
    ECU_CAN_READ = 1  # Can read randomly
    ECU_AUTONOMOUS_EVENTS = 2  # Cannot read, autonomous EV_TIME_SYNC
    ECU_CANNOT_READ = 3  # Reports ECU timestamps but cannot read clock


class SlavClockSyncState(enum.IntEnum):
    """Synchronization state of XCP slave's clock."""

    SYNCHRONIZING = 0  # In progress of synchronizing
    SYNCHRONIZED = 1  # Synchronized to grandmaster
    SYNTONIZING = 2  # In progress of syntonizing
    SYNTONIZED = 3  # Syntonized to grandmaster
    NOT_SUPPORTED = 7  # Does not support sync/syntonization
    # 4, 5, 6 = Reserved


class GrandmClockSyncState(enum.IntEnum):
    """Synchronization state of dedicated grandmaster clock."""

    NOT_SYNCHRONIZED = 0
    SYNCHRONIZED = 1


class EcuClockSyncState(enum.IntEnum):
    """Synchronization state of ECU clock."""

    NOT_SYNCHRONIZED = 0
    SYNCHRONIZED = 1
    UNKNOWN = 2
    RESERVED = 3


class TimestampUnit(enum.IntEnum):
    """Timestamp unit (same as DAQ_TIMESTAMP_UNIT)."""

    UNIT_1NS = 0
    UNIT_10NS = 1
    UNIT_100NS = 2
    UNIT_1US = 3
    UNIT_10US = 4
    UNIT_100US = 5
    UNIT_1MS = 6
    UNIT_10MS = 7
    UNIT_100MS = 8
    UNIT_1S = 9
    UNIT_1PS = 10
    UNIT_10PS = 11
    UNIT_100PS = 12


class Epoch(enum.IntEnum):
    """Epoch of grandmaster clock."""

    TAI = 0  # Atomic Time
    UTC = 1  # Universal Coordinated Time
    ARBITRARY = 2  # Unknown


class NativeTimestampSize(enum.IntEnum):
    """Native timestamp size in bytes."""

    DWORD = 4  # 32-bit
    DLONG = 8  # 64-bit


# ==============================================================================
# BITFIELD PARSERS
# ==============================================================================


@dataclass
class SetProperties:
    """Parsed SET_PROPERTIES parameter (byte 1 of command)."""

    response_fmt: ResponseFormat
    time_sync_bridge: TimeSyncBridge
    set_cluster_id: bool

    @staticmethod
    def encode(
        response_fmt: ResponseFormat = ResponseFormat.LEGACY,
        time_sync_bridge: TimeSyncBridge = TimeSyncBridge.NOT_AVAILABLE,
        set_cluster_id: bool = False,
    ) -> int:
        """Encode SET_PROPERTIES byte."""
        value = 0
        value |= response_fmt & 0x03
        value |= (time_sync_bridge & 0x03) << 2
        value |= (1 if set_cluster_id else 0) << 4
        return value


@dataclass
class GetPropertiesRequest:
    """Parsed GET_PROPERTIES_REQUEST parameter (byte 2 of command)."""

    get_clk_info: bool

    @staticmethod
    def encode(get_clk_info: bool = False) -> int:
        """Encode GET_PROPERTIES_REQUEST byte."""
        return 1 if get_clk_info else 0


@dataclass
class SlaveConfig:
    """Parsed SLAVE_CONFIG from response (byte 1)."""

    response_fmt: ResponseFormat
    daq_ts_relation: DaqTimestampRelation
    time_sync_bridge: TimeSyncBridge

    @staticmethod
    def parse(value: int) -> "SlaveConfig":
        """Parse SLAVE_CONFIG byte."""
        return SlaveConfig(
            response_fmt=ResponseFormat(value & 0x03),
            daq_ts_relation=DaqTimestampRelation((value >> 2) & 0x01),
            time_sync_bridge=TimeSyncBridge((value >> 3) & 0x03),
        )


@dataclass
class ObservableClocks:
    """Parsed OBSERVABLE_CLOCKS from response (byte 2)."""

    xcp_slv_clk: ClockAvailability
    grandm_clk: ClockAvailability
    ecu_clk: ClockAvailability

    @staticmethod
    def parse(value: int) -> "ObservableClocks":
        """Parse OBSERVABLE_CLOCKS byte."""
        return ObservableClocks(
            xcp_slv_clk=ClockAvailability(value & 0x03),
            grandm_clk=ClockAvailability((value >> 2) & 0x03),
            ecu_clk=ClockAvailability((value >> 4) & 0x03),
        )


@dataclass
class SyncState:
    """Parsed SYNC_STATE from response (byte 3)."""

    slv_clk_sync_state: SlavClockSyncState
    grandm_clk_sync_state: GrandmClockSyncState
    ecu_clk_sync_state: EcuClockSyncState

    @staticmethod
    def parse(value: int) -> "SyncState":
        """Parse SYNC_STATE byte."""
        return SyncState(
            slv_clk_sync_state=SlavClockSyncState(value & 0x07),
            grandm_clk_sync_state=GrandmClockSyncState((value >> 3) & 0x01),
            ecu_clk_sync_state=EcuClockSyncState((value >> 4) & 0x03),
        )


@dataclass
class ClockInfo:
    """Parsed CLOCK_INFO from response (byte 4)."""

    slv_clk_info: bool
    grandm_clk_info: bool
    clk_relation: bool
    ecu_clk_info: bool
    ecu_grandm_clk_info: bool

    @staticmethod
    def parse(value: int) -> "ClockInfo":
        """Parse CLOCK_INFO byte."""
        return ClockInfo(
            slv_clk_info=bool(value & 0x01),
            grandm_clk_info=bool(value & 0x02),
            clk_relation=bool(value & 0x04),
            ecu_clk_info=bool(value & 0x08),
            ecu_grandm_clk_info=bool(value & 0x10),
        )


# ==============================================================================
# RESPONSE STRUCTURE
# ==============================================================================


@dataclass
class TimeCorrelationPropertiesResponse:
    """
    Parsed TIME_CORRELATION_PROPERTIES positive response.

    Response structure (8 bytes):
        [0xFF][SLAVE_CONFIG][OBSERVABLE_CLOCKS][SYNC_STATE]
        [CLOCK_INFO][RESERVED][CLUSTER_ID:WORD]
    """

    slave_config: SlaveConfig
    observable_clocks: ObservableClocks
    sync_state: SyncState
    clock_info: ClockInfo
    cluster_id: int

    @staticmethod
    def parse(response: bytes) -> "TimeCorrelationPropertiesResponse":
        """
        Parse TIME_CORRELATION_PROPERTIES response packet.

        Args:
            response: Response bytes (minimum 8 bytes)

        Returns:
            Parsed response structure

        Raises:
            ValueError: If response is invalid
        """
        if len(response) < 8:
            raise ValueError(f"Response too short: {len(response)} bytes (expected 8)")

        if response[0] != 0xFF:
            raise ValueError(f"Invalid packet ID: {response[0]:#04x} (expected 0xFF)")

        slave_config = SlaveConfig.parse(response[1])
        observable_clocks = ObservableClocks.parse(response[2])
        sync_state = SyncState.parse(response[3])
        clock_info = ClockInfo.parse(response[4])
        # byte[5] = RESERVED
        cluster_id = struct.unpack("<H", response[6:8])[0]  # Intel byte order

        return TimeCorrelationPropertiesResponse(
            slave_config=slave_config,
            observable_clocks=observable_clocks,
            sync_state=sync_state,
            clock_info=clock_info,
            cluster_id=cluster_id,
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        lines = ["TIME_CORRELATION_PROPERTIES Response:"]
        lines.append(f"  Cluster ID: {self.cluster_id:#06x}")
        lines.append(f"  Response Format: {self.slave_config.response_fmt.name}")
        lines.append(f"  DAQ Timestamps: {self.slave_config.daq_ts_relation.name}")
        lines.append(f"  Time Sync Bridge: {self.slave_config.time_sync_bridge.name}")
        lines.append("")
        lines.append("  Observable Clocks:")
        lines.append(f"    XCP Slave: {self.observable_clocks.xcp_slv_clk.name}")
        lines.append(f"    Grandmaster: {self.observable_clocks.grandm_clk.name}")
        lines.append(f"    ECU: {self.observable_clocks.ecu_clk.name}")
        lines.append("")
        lines.append("  Sync State:")
        lines.append(f"    XCP Slave: {self.sync_state.slv_clk_sync_state.name}")
        lines.append(f"    Grandmaster: {self.sync_state.grandm_clk_sync_state.name}")
        lines.append(f"    ECU: {self.sync_state.ecu_clk_sync_state.name}")
        lines.append("")
        lines.append("  Clock Info Available:")
        lines.append(f"    XCP Slave: {self.clock_info.slv_clk_info}")
        lines.append(f"    Grandmaster: {self.clock_info.grandm_clk_info}")
        lines.append(f"    Clock Relation: {self.clock_info.clk_relation}")
        lines.append(f"    ECU: {self.clock_info.ecu_clk_info}")
        lines.append(f"    ECU Grandmaster: {self.clock_info.ecu_grandm_clk_info}")
        return "\n".join(lines)


# ==============================================================================
# CLOCK INFORMATION STRUCTURES (from UPLOAD)
# ==============================================================================


@dataclass
class ClockInformation:
    """
    Clock information structure (24 bytes) obtained via UPLOAD.

    Common structure for XCP_SLV, GRANDM, and ECU clocks.
    """

    uuid: bytes  # 8 bytes (EUI-64)
    timestamp_ticks: int  # WORD
    timestamp_unit: TimestampUnit  # BYTE
    stratum_level: int  # BYTE (255 if unknown)
    native_timestamp_size: NativeTimestampSize  # BYTE
    epoch: Optional[Epoch]  # BYTE (only for GRANDM)
    max_timestamp_before_wrap: int  # DLONG

    @staticmethod
    def parse(data: bytes, has_epoch: bool = False) -> "ClockInformation":
        """
        Parse clock information structure.

        Args:
            data: 24 bytes of clock info
            has_epoch: True for GRANDM clock (has Epoch field)

        Returns:
            Parsed clock information
        """
        if len(data) < 24:
            raise ValueError(f"Clock info too short: {len(data)} bytes (expected 24)")

        uuid = data[0:8]
        timestamp_ticks = struct.unpack("<H", data[8:10])[0]
        timestamp_unit = TimestampUnit(data[10])
        stratum_level = data[11]
        native_timestamp_size = NativeTimestampSize(data[12])
        epoch = Epoch(data[13]) if has_epoch else None
        # data[14:16] = RESERVED
        max_timestamp_before_wrap = struct.unpack("<Q", data[16:24])[0]

        return ClockInformation(
            uuid=uuid,
            timestamp_ticks=timestamp_ticks,
            timestamp_unit=timestamp_unit,
            stratum_level=stratum_level,
            native_timestamp_size=native_timestamp_size,
            epoch=epoch,
            max_timestamp_before_wrap=max_timestamp_before_wrap,
        )

    def uuid_string(self) -> str:
        """Format UUID as EUI-64 string (XX:XX:XX:XX:XX:XX:XX:XX)."""
        return ":".join(f"{b:02X}" for b in self.uuid)

    def __str__(self) -> str:
        """Human-readable representation."""
        lines = [f"Clock Information (UUID: {self.uuid_string()})"]
        lines.append(f"  Timestamp Ticks: {self.timestamp_ticks}")
        lines.append(f"  Timestamp Unit: {self.timestamp_unit.name}")
        lines.append(f"  Stratum Level: {self.stratum_level if self.stratum_level != 255 else 'Unknown'}")
        lines.append(f"  Native Size: {self.native_timestamp_size.value} bytes")
        if self.epoch is not None:
            lines.append(f"  Epoch: {self.epoch.name}")
        lines.append(f"  Max Before Wrap: {self.max_timestamp_before_wrap:#x}")
        return "\n".join(lines)


@dataclass
class ClockRelation:
    """
    Clock relation structure (16 bytes) obtained via UPLOAD.

    Provides relationship between XCP slave's clock and grandmaster.
    """

    origin_in_grandmaster_domain: int  # DLONG - XCP slave's origin in GM time
    xcp_slave_timestamp: int  # DLONG - Corresponding XCP slave timestamp

    @staticmethod
    def parse(data: bytes) -> "ClockRelation":
        """Parse clock relation structure (16 bytes)."""
        if len(data) < 16:
            raise ValueError(f"Clock relation too short: {len(data)} bytes (expected 16)")

        origin_in_grandmaster_domain = struct.unpack("<Q", data[0:8])[0]
        xcp_slave_timestamp = struct.unpack("<Q", data[8:16])[0]

        return ClockRelation(
            origin_in_grandmaster_domain=origin_in_grandmaster_domain,
            xcp_slave_timestamp=xcp_slave_timestamp,
        )

    def __str__(self) -> str:
        """Human-readable representation."""
        return (
            f"Clock Relation:\n"
            f"  Origin (GM domain): {self.origin_in_grandmaster_domain:#x}\n"
            f"  XCP Slave TS: {self.xcp_slave_timestamp:#x}"
        )


@dataclass
class EcuGrandmasterClockInfo:
    """
    ECU's grandmaster clock information (8 bytes) obtained via UPLOAD.

    Contains only UUID of ECU's grandmaster clock.
    """

    uuid: bytes  # 8 bytes (EUI-64)

    @staticmethod
    def parse(data: bytes) -> "EcuGrandmasterClockInfo":
        """Parse ECU grandmaster clock info (8 bytes)."""
        if len(data) < 8:
            raise ValueError(f"ECU GM info too short: {len(data)} bytes (expected 8)")
        return EcuGrandmasterClockInfo(uuid=data[0:8])

    def uuid_string(self) -> str:
        """Format UUID as EUI-64 string."""
        return ":".join(f"{b:02X}" for b in self.uuid)

    def __str__(self) -> str:
        """Human-readable representation."""
        return f"ECU Grandmaster Clock: {self.uuid_string()}"

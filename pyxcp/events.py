"""
XCP Event System - XCP 1.5 Specification

This module implements the Chain-of-Responsibility pattern for XCP event handling,
with special focus on EV_TIME_SYNC (XCP 1.5 advanced time correlation).
"""

import enum
from abc import ABC, abstractmethod
from typing import NamedTuple, Optional, TYPE_CHECKING
import struct
import logging

if TYPE_CHECKING:
    from pyxcp.transport.base import BaseTransport

# ==============================================================================
# EVENT ENUMS AND BITFIELDS (XCP 1.5 Specification)
# ==============================================================================


class TriggerInitiator(enum.IntEnum):
    """EV_TIME_SYNC TRIGGER_INITIATOR field (bits 0-2)"""

    HW_TRIGGER = 0  # HW trigger, e.g. Vector Syncline
    INDEPENDENT_TIME_SYNC = 1  # Event from XCP-independent time sync (e.g. PPS)
    GET_DAQ_CLOCK_MULTICAST = 2  # Response to GET_DAQ_CLOCK_MULTICAST
    GET_DAQ_CLOCK_VIA_BRIDGE = 3  # GET_DAQ_CLOCK_MULTICAST via Time Sync Bridge
    SYNC_STATE_CHANGE = 4  # Syntonization/synchronization state change
    LEAP_SECOND = 5  # Leap second occurred on grandmaster
    ECU_RESET_RELEASE = 6  # Release of ECU reset
    RESERVED = 7


class TimeOfTsSampling(enum.IntEnum):
    """EV_TIME_SYNC TIME_OF_TS_SAMPLING field (bits 3-4)"""

    PROTOCOL_LAYER = 0  # During command processing at protocol layer
    LOW_JITTER_INTERRUPT = 1  # Low jitter, measured in high-priority interrupt
    PHYSICAL_TRANSMISSION = 2  # Upon physical transmission to XCP master
    PHYSICAL_RECEPTION = 3  # Upon physical reception of command (recommended for multicast)


class ClockFormat(enum.IntEnum):
    """Payload format for clock timestamps (2 bits per clock)"""

    NOT_PRESENT = 0  # Clock not part of payload
    DWORD = 1  # 4 bytes (uint32)
    DLONG = 2  # 8 bytes (uint64)
    RESERVED = 3


# ==============================================================================
# BITFIELD PARSERS
# ==============================================================================


class TriggerInfo(NamedTuple):
    """Parsed TRIGGER_INFO byte (EV_TIME_SYNC)"""

    initiator: TriggerInitiator
    time_of_sampling: TimeOfTsSampling
    raw: int

    @classmethod
    def parse(cls, byte_value: int) -> "TriggerInfo":
        """Parse TRIGGER_INFO byte"""
        initiator = TriggerInitiator(byte_value & 0x07)
        time_of_sampling = TimeOfTsSampling((byte_value >> 3) & 0x03)
        return cls(initiator=initiator, time_of_sampling=time_of_sampling, raw=byte_value)


class PayloadFormat(NamedTuple):
    """Parsed PAYLOAD_FMT byte (EV_TIME_SYNC)"""

    xcp_slave_fmt: ClockFormat
    grandmaster_fmt: ClockFormat
    ecu_fmt: ClockFormat
    cluster_identifier: bool
    raw: int

    @classmethod
    def parse(cls, byte_value: int) -> "PayloadFormat":
        """Parse PAYLOAD_FMT byte"""
        xcp_slave_fmt = ClockFormat(byte_value & 0x03)
        grandmaster_fmt = ClockFormat((byte_value >> 2) & 0x03)
        ecu_fmt = ClockFormat((byte_value >> 4) & 0x03)
        cluster_identifier = bool(byte_value & 0x40)
        return cls(
            xcp_slave_fmt=xcp_slave_fmt,
            grandmaster_fmt=grandmaster_fmt,
            ecu_fmt=ecu_fmt,
            cluster_identifier=cluster_identifier,
            raw=byte_value,
        )


class TimeSyncEvent(NamedTuple):
    """Parsed EV_TIME_SYNC event packet"""

    is_legacy: bool
    trigger_info: TriggerInfo
    payload_fmt: Optional[PayloadFormat]
    counter: Optional[int]  # For GET_DAQ_CLOCK_MULTICAST responses
    xcp_slave_timestamp: Optional[int]
    grandmaster_timestamp: Optional[int]
    ecu_timestamp: Optional[int]
    cluster_id: Optional[int]
    sync_state: Optional[int]

    @classmethod
    def parse(cls, packet: bytes, max_cto: int = 255, byte_order: str = "little") -> "TimeSyncEvent":
        """
        Parse EV_TIME_SYNC event packet.

        Args:
            packet: Full event packet starting with PID=0xFD
            max_cto: Transport layer MAX_CTO (8 for CAN, >8 for ETH/etc.)
            byte_order: 'little' (INTEL) or 'big' (MOTOROLA)

        Returns:
            Parsed TimeSyncEvent structure
        """
        if len(packet) < 8:
            raise ValueError(f"EV_TIME_SYNC packet too short: {len(packet)} bytes")

        if packet[0] != 0xFD or packet[1] != 0x08:
            raise ValueError(f"Not an EV_TIME_SYNC packet: PID={packet[0]:02X}, Code={packet[1]:02X}")

        trigger_info = TriggerInfo.parse(packet[2])

        # Determine format: Legacy vs Extended
        if max_cto == 8:
            # MAX_CTO = 8: Always uses simplified format (even in extended mode)
            # [0xFD][0x08][TRIGGER_INFO][Counter][Timestamp:DWORD]
            counter = packet[3]
            timestamp = struct.unpack("<I" if byte_order == "little" else ">I", packet[4:8])[0]

            return cls(
                is_legacy=True,  # Uses legacy structure
                trigger_info=trigger_info,
                payload_fmt=None,
                counter=counter,
                xcp_slave_timestamp=timestamp,  # DAQ-related clock
                grandmaster_timestamp=None,
                ecu_timestamp=None,
                cluster_id=None,
                sync_state=None,
            )

        # MAX_CTO > 8: Check if extended format is enabled via PAYLOAD_FMT
        payload_fmt = PayloadFormat.parse(packet[3])

        if payload_fmt.raw == 0:
            # PAYLOAD_FMT = 0: Legacy mode (fixed 8-byte structure)
            # [0xFD][0x08][TRIGGER_INFO][reserved][Timestamp:DWORD]
            timestamp = struct.unpack("<I" if byte_order == "little" else ">I", packet[4:8])[0]

            return cls(
                is_legacy=True,
                trigger_info=trigger_info,
                payload_fmt=payload_fmt,
                counter=None,
                xcp_slave_timestamp=timestamp,
                grandmaster_timestamp=None,
                ecu_timestamp=None,
                cluster_id=None,
                sync_state=None,
            )

        # Extended format: Parse variable-length payload
        offset = 4
        xcp_slave_ts = None
        grandmaster_ts = None
        ecu_ts = None
        cluster_id = None
        counter = None
        sync_state = None

        # Helper to read DWORD or DLONG
        def read_timestamp(fmt: ClockFormat) -> Optional[int]:
            nonlocal offset
            if fmt == ClockFormat.NOT_PRESENT:
                return None
            elif fmt == ClockFormat.DWORD:
                if offset + 4 > len(packet):
                    raise ValueError(f"Packet too short at offset {offset}")
                val = struct.unpack("<I" if byte_order == "little" else ">I", packet[offset : offset + 4])[0]
                offset += 4
                return val
            elif fmt == ClockFormat.DLONG:
                if offset + 8 > len(packet):
                    raise ValueError(f"Packet too short at offset {offset}")
                val = struct.unpack("<Q" if byte_order == "little" else ">Q", packet[offset : offset + 8])[0]
                offset += 8
                return val
            return None

        # Parse timestamps in order: XCP_SLV, GRANDM, ECU
        xcp_slave_ts = read_timestamp(payload_fmt.xcp_slave_fmt)
        grandmaster_ts = read_timestamp(payload_fmt.grandmaster_fmt)
        ecu_ts = read_timestamp(payload_fmt.ecu_fmt)

        # Parse optional Cluster ID + Counter
        if payload_fmt.cluster_identifier:
            if offset + 3 > len(packet):
                raise ValueError(f"Packet too short for cluster_id at offset {offset}")
            cluster_id = struct.unpack("<H" if byte_order == "little" else ">H", packet[offset : offset + 2])[0]
            counter = packet[offset + 2]
            offset += 3

        # Parse optional SYNC_STATE
        # SYNC_STATE is present if at least one clock can be synchronized/syntonized
        if offset < len(packet):
            sync_state = packet[offset]

        return cls(
            is_legacy=False,
            trigger_info=trigger_info,
            payload_fmt=payload_fmt,
            counter=counter,
            xcp_slave_timestamp=xcp_slave_ts,
            grandmaster_timestamp=grandmaster_ts,
            ecu_timestamp=ecu_ts,
            cluster_id=cluster_id,
            sync_state=sync_state,
        )

    def __repr__(self) -> str:
        mode = "Legacy" if self.is_legacy else "Extended"
        parts = [f"TimeSyncEvent({mode})"]
        parts.append(f"  Trigger: {self.trigger_info.initiator.name}")
        parts.append(f"  Sampling: {self.trigger_info.time_of_sampling.name}")
        if self.xcp_slave_timestamp is not None:
            parts.append(f"  XCP Slave: {self.xcp_slave_timestamp:#x}")
        if self.grandmaster_timestamp is not None:
            parts.append(f"  Grandmaster: {self.grandmaster_timestamp:#x}")
        if self.ecu_timestamp is not None:
            parts.append(f"  ECU: {self.ecu_timestamp:#x}")
        if self.cluster_id is not None:
            parts.append(f"  Cluster ID: {self.cluster_id}, Counter: {self.counter}")
        if self.sync_state is not None:
            parts.append(f"  Sync State: {self.sync_state:#x}")
        return "\n".join(parts)


# ==============================================================================
# CHAIN-OF-RESPONSIBILITY EVENT HANDLER PATTERN
# ==============================================================================


class EventHandler(ABC):
    """
    Base class for XCP event handlers (Chain-of-Responsibility pattern).

    Handlers can be chained together, with each handler deciding whether to:
    1. Handle the event and stop the chain (return True)
    2. Pass to next handler (return False)
    3. Handle the event AND pass to next handler (call super().handle())
    """

    def __init__(self, transport: "BaseTransport"):
        self.transport = transport
        self.logger = logging.getLogger(self.__class__.__name__)
        self._next_handler: Optional[EventHandler] = None

    def set_next(self, handler: "EventHandler") -> "EventHandler":
        """Chain handlers together. Returns the handler for chaining."""
        self._next_handler = handler
        return handler

    @abstractmethod
    def can_handle(self, event_code: int, packet: bytes) -> bool:
        """Check if this handler can process the event."""
        pass

    @abstractmethod
    def handle(self, event_code: int, packet: bytes) -> bool:
        """
        Process the event.

        Returns:
            True if event was fully handled (stop chain)
            False to continue to next handler
        """
        pass

    def process(self, event_code: int, packet: bytes) -> bool:
        """Process event through the chain. Returns True if handled."""
        if self.can_handle(event_code, packet):
            handled = self.handle(event_code, packet)
            if handled:
                return True  # Event consumed

        # Pass to next handler in chain
        if self._next_handler:
            return self._next_handler.process(event_code, packet)

        return False  # No handler processed it


# ==============================================================================
# CONCRETE EVENT HANDLERS
# ==============================================================================


class TransportEventHandler(EventHandler):
    """
    Handles transport-layer events (EV_CMD_PENDING, EV_TRANSPORT).
    Always first in the chain, handles internal transport concerns.
    """

    def can_handle(self, event_code: int, packet: bytes) -> bool:
        from pyxcp.types import Event

        return event_code in (Event.EV_CMD_PENDING, Event.EV_TRANSPORT)

    def handle(self, event_code: int, packet: bytes) -> bool:
        from pyxcp.types import Event

        if event_code == Event.EV_CMD_PENDING:
            # Restart timeout detection
            self.transport.timer_restart_event.set()
            self.logger.debug("EV_CMD_PENDING: Restarted timeout detection")
            return True  # Fully handled

        elif event_code == Event.EV_TRANSPORT:
            # Transport-specific event (implementation-dependent)
            self.logger.info(f"EV_TRANSPORT received: {packet.hex()}")
            # Let derived transport classes override this if needed
            return True

        return False


class TimeSyncEventHandler(EventHandler):
    """
    Handles EV_TIME_SYNC events (XCP 1.5 advanced time correlation).

    Responsibilities:
    - Parse legacy and extended EV_TIME_SYNC packets
    - Store timing information for correlation
    - Notify DAQ system of timing updates
    """

    def __init__(self, transport: "BaseTransport"):
        super().__init__(transport)
        self.last_sync_event: Optional[TimeSyncEvent] = None

    def can_handle(self, event_code: int, packet: bytes) -> bool:
        from pyxcp.types import Event

        return event_code == Event.EV_TIME_SYNC

    def handle(self, event_code: int, packet: bytes) -> bool:
        try:
            # Determine MAX_CTO and byte order from transport
            max_cto = getattr(self.transport, "max_cto", 255)
            byte_order = getattr(self.transport, "byte_order", "little")

            # Parse the event
            sync_event = TimeSyncEvent.parse(packet, max_cto=max_cto, byte_order=byte_order)
            self.last_sync_event = sync_event

            self.logger.debug(f"EV_TIME_SYNC received:\n{sync_event}")

            # TODO: Store timing correlation data
            # This is where you'd implement:
            # - Timestamp correlation storage
            # - Clock drift calculation
            # - PTP synchronization state tracking
            # - Notify DAQ recorder of timing updates

            # For now, just log it
            if sync_event.is_legacy:
                self.logger.info(
                    f"TIME_SYNC (Legacy): XCP_Slave={sync_event.xcp_slave_timestamp:#x}, "
                    f"Trigger={sync_event.trigger_info.initiator.name}"
                )
            else:
                clocks = []
                if sync_event.xcp_slave_timestamp:
                    clocks.append(f"XCP={sync_event.xcp_slave_timestamp:#x}")
                if sync_event.grandmaster_timestamp:
                    clocks.append(f"GM={sync_event.grandmaster_timestamp:#x}")
                if sync_event.ecu_timestamp:
                    clocks.append(f"ECU={sync_event.ecu_timestamp:#x}")
                self.logger.info(
                    f"TIME_SYNC (Extended): {', '.join(clocks)}, "
                    f"Trigger={sync_event.trigger_info.initiator.name}"
                )

            return True  # Fully handled

        except Exception as e:
            self.logger.error(f"Failed to parse EV_TIME_SYNC: {e}", exc_info=True)
            return True  # Still consume the event


class SessionStateEventHandler(EventHandler):
    """
    Handles session state events (EV_SLEEP, EV_WAKE_UP, EV_SESSION_TERMINATED, EV_RESUME_MODE).
    """

    def can_handle(self, event_code: int, packet: bytes) -> bool:
        from pyxcp.types import Event

        return event_code in (Event.EV_SLEEP, Event.EV_WAKE_UP, Event.EV_SESSION_TERMINATED, Event.EV_RESUME_MODE)

    def handle(self, event_code: int, packet: bytes) -> bool:
        from pyxcp.types import Event

        if event_code == Event.EV_SLEEP:
            self.logger.info("EV_SLEEP: Slave entering sleep mode - suspending commands")
            # TODO: Set transport state to SLEEPING
            return True

        elif event_code == Event.EV_WAKE_UP:
            self.logger.info("EV_WAKE_UP: Slave resumed normal operation")
            # TODO: Resume command processing
            return True

        elif event_code == Event.EV_SESSION_TERMINATED:
            self.logger.warning("EV_SESSION_TERMINATED: Slave autonomously disconnected!")
            # TODO: Trigger disconnect cleanup
            return True

        elif event_code == Event.EV_RESUME_MODE:
            session_config_id = struct.unpack("<H", packet[2:4])[0]
            self.logger.info(f"EV_RESUME_MODE: Slave resumed with config ID={session_config_id:#x}")
            # TODO: Verify session configuration matches
            return True

        return False


class DaqStimEventHandler(EventHandler):
    """
    Handles DAQ/STIM events (EV_DAQ_OVERLOAD, EV_STIM_TIMEOUT, EV_CLEAR_DAQ, EV_STORE_DAQ).
    """

    def can_handle(self, event_code: int, packet: bytes) -> bool:
        from pyxcp.types import Event

        return event_code in (
            Event.EV_DAQ_OVERLOAD,
            Event.EV_STIM_TIMEOUT,
            Event.EV_CLEAR_DAQ,
            Event.EV_STORE_DAQ,
        )

    def handle(self, event_code: int, packet: bytes) -> bool:
        from pyxcp.types import Event

        if event_code == Event.EV_DAQ_OVERLOAD:
            self.logger.warning("EV_DAQ_OVERLOAD: Slave reporting DAQ overload!")
            return True

        elif event_code == Event.EV_STIM_TIMEOUT:
            info_type = packet[2]
            failure_type = packet[3]
            identifier = struct.unpack("<H", packet[4:6])[0]
            self.logger.error(
                f"EV_STIM_TIMEOUT: Info={info_type}, Failure={failure_type}, " f"ID={identifier}"
            )
            return True

        elif event_code == Event.EV_CLEAR_DAQ:
            self.logger.info("EV_CLEAR_DAQ: DAQ configuration cleared from NV memory")
            return True

        elif event_code == Event.EV_STORE_DAQ:
            self.logger.info("EV_STORE_DAQ: DAQ configuration stored to NV memory")
            return True

        return False


class UserEventHandler(EventHandler):
    """
    Handles user-defined events (EV_USER, EV_ECU_STATE_CHANGE, EV_STORE_CAL).
    Fallback handler for unhandled events.
    """

    def can_handle(self, event_code: int, packet: bytes) -> bool:
        # Catch-all: handles anything not handled by previous handlers
        return True

    def handle(self, event_code: int, packet: bytes) -> bool:
        from pyxcp.types import Event

        if event_code == Event.EV_USER:
            self.logger.info(f"EV_USER received: {packet.hex()}")
            # TODO: Allow user callback registration
            return True

        elif event_code == Event.EV_ECU_STATE_CHANGE:
            state_number = packet[2]
            self.logger.info(f"EV_ECU_STATE_CHANGE: State={state_number}")
            return True

        elif event_code == Event.EV_STORE_CAL:
            self.logger.info("EV_STORE_CAL: Calibration data stored to NV memory")
            return True

        else:
            self.logger.warning(f"Unhandled event code {event_code:#x}: {packet.hex()}")
            return True  # Still consume it


# ==============================================================================
# FACTORY FUNCTION
# ==============================================================================


def create_default_event_chain(transport: "BaseTransport") -> EventHandler:
    """
    Create the default event handler chain for XCP 1.5.

    Chain order:
        TransportEventHandler → TimeSyncEventHandler → SessionStateEventHandler
        → DaqStimEventHandler → UserEventHandler (fallback)

    Returns:
        Head of the handler chain
    """
    transport_handler = TransportEventHandler(transport)
    time_sync_handler = TimeSyncEventHandler(transport)
    session_handler = SessionStateEventHandler(transport)
    daq_stim_handler = DaqStimEventHandler(transport)
    user_handler = UserEventHandler(transport)

    # Build the chain
    transport_handler.set_next(time_sync_handler).set_next(session_handler).set_next(daq_stim_handler).set_next(
        user_handler
    )

    return transport_handler


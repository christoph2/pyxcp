#!/usr/bin/env python
"""
"""

import functools
import operator
from bisect import bisect_left
from typing import Any, Dict, Optional, Type

from can import CanError, CanInitializationError, Message, detect_available_configs
from can.bus import BusABC
from can.interface import _get_class_for_interface
from rich.console import Console

from pyxcp.config import CAN_INTERFACE_MAP
from pyxcp.transport.base import BaseTransport

from ..utils import seconds_to_nanoseconds


console = Console()

CAN_EXTENDED_ID = 0x80000000
MAX_11_BIT_IDENTIFIER = (1 << 11) - 1
MAX_29_BIT_IDENTIFIER = (1 << 29) - 1
MAX_DLC_CLASSIC = 8
CAN_FD_DLCS = (12, 16, 20, 24, 32, 48, 64)  # Discrete CAN-FD DLCs in case DLC > 8.


class IdentifierOutOfRangeError(Exception):
    """Signals an identifier greater then :obj:`MAX_11_BIT_IDENTIFIER` or :obj:`MAX_29_BIT_IDENTIFIER`."""

    pass


def is_extended_identifier(identifier: int) -> bool:
    """Check for extendend CAN identifier.

    Parameters
    ----------
    identifier: int

    Returns
    -------
    bool
    """
    return (identifier & CAN_EXTENDED_ID) == CAN_EXTENDED_ID


def stripIdentifier(identifier: int) -> int:
    """Get raw CAN identifier (remove :obj:`CAN_EXTENDED_ID` bit if present).

    Parameters
    ----------
    identifier: int

    Returns
    -------
    int
    """
    return identifier & (~0xE0000000)


def samplePointToTsegs(tqs: int, samplePoint: float) -> tuple:
    """Calculate TSEG1 and TSEG2 from time-quantas and sample-point.

    Parameters
    ----------
    tqs: int
        Number of time-quantas
    samplePoint: float or int
        Sample-point as a percentage value.

    Returns
    -------
    tuple (TSEG1, TSEG2)
    """
    factor = samplePoint / 100.0
    tseg1 = int(tqs * factor)
    tseg2 = tqs - tseg1
    return (tseg1, tseg2)


def pad_frame(frame: bytes, pad_frame: bool, padding_value: int) -> bytes:
    """Pad frame to next discrete DLC value (CAN-FD) or on request (CAN-Classic).

    References:
    -----------
    ISO/DIS 15765 - 4; 8.2 Data length Code (DLC)
    AUTOSAR CP Release 4.3.0, Specification of CAN Transport Layer; 7.3.8 N-PDU padding
    AUTOSAR CP Release 4.3.0, Specification of CAN Driver; [SWS_CAN_00502], [ECUC_Can_00485]
    AUTOSAR CP Release 4.3.0, Requirements on CAN; [SRS_Can_01073], [SRS_Can_01086], [SRS_Can_01160]
    """
    frame_len = len(frame)
    if frame_len <= MAX_DLC_CLASSIC:
        actual_len = MAX_DLC_CLASSIC if pad_frame else frame_len
    else:
        actual_len = CAN_FD_DLCS[bisect_left(CAN_FD_DLCS, frame_len)]
    # append fill bytes up to MAX_DLC resp. next discrete FD DLC.
    if len(frame) < actual_len:
        frame += bytes([padding_value]) * (actual_len - len(frame))
    return frame


class Identifier:
    """Convenience class for XCP formatted CAN identifiers.

    Parameters:
    -----------
    raw_id: int
        Bit 32 set (i.e. 0x80000000) signals an extended (29-bit) identifier.

    Raises
    ------
    :class:`IdentifierOutOfRangeError`
    """

    def __init__(self, raw_id: int):
        self._raw_id = raw_id
        self._id = stripIdentifier(raw_id)
        self._is_extended = is_extended_identifier(raw_id)
        if self._is_extended:
            if self._id > MAX_29_BIT_IDENTIFIER:
                raise IdentifierOutOfRangeError(f"29-bit identifier {self._id!r} is out of range")
        else:
            if self._id > MAX_11_BIT_IDENTIFIER:
                raise IdentifierOutOfRangeError(f"11-bit identifier {self._id!r} is out of range")

    @property
    def id(self) -> int:
        """
        Returns
        -------
        int
            Identifier as seen on bus.
        """
        return self._id

    @property
    def raw_id(self) -> int:
        """
        Returns
        -------
        int
            Raw XCP formatted identifier.
        """
        return self._raw_id

    @property
    def is_extended(self) -> bool:
        """
        Returns
        -------
        bool
            - True - 29-bit identifier.
            - False - 11-bit identifier.
        """
        return self._is_extended

    @property
    def type_str(self) -> str:
        """

        Returns
        -------
        str
            - "S" - 11-bit identifier.
            - "E" - 29-bit identifier.
        """
        return "E" if self.is_extended else "S"

    @staticmethod
    def make_identifier(identifier: int, extended: bool) -> "Identifier":
        """Factory method.

        Parameters
        ----------
        identifier: int
            Identifier as seen on bus.

        extended: bool
            bool
                - True - 29-bit identifier.
                - False - 11-bit identifier.
        Returns
        -------
        :class:`Identifier`

        Raises
        ------
        :class:`IdentifierOutOfRangeError`
        """
        return Identifier(identifier if not extended else (identifier | CAN_EXTENDED_ID))

    def create_filter_from_id(self) -> Dict:
        """Create a single CAN filter entry.
        s. https://python-can.readthedocs.io/en/stable/bus.html#filtering
        """
        return {
            "can_id": self.id,
            "can_mask": MAX_29_BIT_IDENTIFIER if self.is_extended else MAX_11_BIT_IDENTIFIER,
            "extended": self.is_extended,
        }

    def __eq__(self, other) -> bool:
        return (self.id == other.id) and (self.is_extended == other.is_extended)

    def __str__(self) -> str:
        return f"Identifier(id = 0x{self.id:08x}, is_extended = {self.is_extended})"

    def __repr__(self) -> str:
        return f"Identifier(0x{self.raw_id:08x})"


class Frame:
    """"""

    def __init__(self, id_: Identifier, dlc: int, data: bytes, timestamp: int) -> None:
        self.id: Identifier = id_
        self.dlc: int = dlc
        self.data: bytes = data
        self.timestamp: int = timestamp

    def __repr__(self) -> str:
        return f"Frame(id = 0x{self.id:08x}, dlc = {self.dlc}, data = {self.data}, timestamp = {self.timestamp})"

    __str__ = __repr__


class PythonCanWrapper:
    """Wrapper around python-can - github.com/hardbyte/python-can"""

    def __init__(self, parent, interface_name: str, timeout: int, **parameters) -> None:
        self.parent = parent
        self.interface_name: str = interface_name
        self.timeout: int = timeout
        self.parameters = parameters
        self.can_interface_class: Type[BusABC] = _get_class_for_interface(self.interface_name)
        self.can_interface: BusABC
        self.connected: bool = False

    def connect(self):
        if self.connected:
            return
        can_filters = []
        can_filters.append(self.parent.can_id_slave.create_filter_from_id())  # Primary CAN filter.
        if self.parent.has_user_supplied_interface:
            self.can_interface = self.parent.transport_layer_interface
        else:
            self.can_interface = self.can_interface_class(interface=self.interface_name, **self.parameters)
        if self.parent.daq_identifier:
            # Add filters for DAQ identifiers.
            for daq_id in self.parent.daq_identifier:
                can_filters.append(daq_id.create_filter_from_id())
        self.can_interface.set_filters(can_filters)
        self.parent.logger.info(f"XCPonCAN - Using Interface: '{self.can_interface!s}'")
        self.parent.logger.info(f"XCPonCAN - Filters used: {self.can_interface.filters}")
        self.parent.logger.info(f"XCPonCAN - State: {self.can_interface.state!s}")
        self.connected = True

    def close(self):
        if self.connected and not self.parent.has_user_supplied_interface:
            self.can_interface.shutdown()
        self.connected = False

    def transmit(self, payload: bytes) -> None:
        frame = Message(
            arbitration_id=self.parent.can_id_master.id,
            is_extended_id=True if self.parent.can_id_master.is_extended else False,
            is_fd=self.parent.fd,
            data=payload,
        )
        self.can_interface.send(frame)

    def read(self) -> Optional[Frame]:
        if not self.connected:
            return None
        try:
            frame = self.can_interface.recv(self.timeout)
        except CanError:
            return None
        else:
            if frame is None or not len(frame.data):
                return None  # Timeout condition.
            extended = frame.is_extended_id
            identifier = Identifier.make_identifier(frame.arbitration_id, extended)
            return Frame(
                id_=identifier,
                dlc=frame.dlc,
                data=frame.data,
                timestamp=seconds_to_nanoseconds(frame.timestamp),
            )

    def get_timestamp_resolution(self) -> int:
        return 10 * 1000


class EmptyHeader:
    """There is no header for XCP on CAN"""

    def pack(self, *args, **kwargs):
        return b""


class Can(BaseTransport):
    """"""

    MAX_DATAGRAM_SIZE = 7
    HEADER = EmptyHeader()
    HEADER_SIZE = 0

    def __init__(self, config, policy=None, transport_layer_interface: Optional[BusABC] = None):
        super().__init__(config, policy, transport_layer_interface)
        self.load_config(config)
        self.useDefaultListener = self.config.use_default_listener
        self.can_id_master = Identifier(self.config.can_id_master)
        self.can_id_slave = Identifier(self.config.can_id_slave)

        # Regarding CAN-FD s. AUTOSAR CP Release 4.3.0, Requirements on CAN; [SRS_Can_01160] Padding of bytes due to discrete CAN FD DLC]:
        #   "... If a PDU does not exactly match these configurable sizes the unused bytes shall be padded."
        #
        self.fd = self.config.fd
        self.daq_identifier = []
        if self.config.daq_identifier:
            for daq_id in self.config.daq_identifier:
                self.daq_identifier.append(Identifier(daq_id))
        self.max_dlc_required = self.config.max_dlc_required
        self.padding_value = self.config.padding_value
        self.interface_name = self.config.interface
        self.interface_configuration = detect_available_configs(interfaces=[self.interface_name])
        parameters = self.get_interface_parameters()
        self.can_interface = PythonCanWrapper(self, self.interface_name, config.timeout, **parameters)
        self.logger.info(f"XCPonCAN - Interface-Type: {self.interface_name!r} Parameters: {list(parameters.items())}")
        self.logger.info(
            f"XCPonCAN - Master-ID (Tx): 0x{self.can_id_master.id:08X}{self.can_id_master.type_str} -- "
            f"Slave-ID (Rx): 0x{self.can_id_slave.id:08X}{self.can_id_slave.type_str}"
        )

    def get_interface_parameters(self) -> Dict[str, Any]:
        result = dict(channel=self.config.channel)

        can_interface_config_class = CAN_INTERFACE_MAP[self.interface_name]

        # Optional base class parameters.
        optional_parameters = [(p, p.removeprefix("has_")) for p in can_interface_config_class.OPTIONAL_BASE_PARAMS]
        for o, n in optional_parameters:
            opt = getattr(can_interface_config_class, o)
            value = getattr(self.config, n)
            if opt:
                if value is not None:
                    result[n] = value
            elif value is not None:
                self.logger.warning(f"XCPonCAN - {self.interface_name!r} has no support for parameter {n!r}.")

        # Parameter names that need to be mapped.
        for base_name, name in can_interface_config_class.CAN_PARAM_MAP.items():
            value = getattr(self.config, base_name)
            if value is not None:
                result[name] = value

        # Interface specific parameters.
        cxx = getattr(self.config, self.interface_name)
        for name in can_interface_config_class.class_own_traits().keys():
            value = getattr(cxx, name)
            if value is not None:
                result[name] = value
        return result

    def data_received(self, payload: bytes, recv_timestamp: int):
        self.process_response(
            payload,
            len(payload),
            counter=(self.counter_received + 1) & 0xFFFF,
            recv_timestamp=recv_timestamp,
        )

    def listen(self):
        while True:
            if self.closeEvent.is_set():
                return
            frame = self.can_interface.read()
            if frame:
                self.data_received(frame.data, frame.timestamp)

    def connect(self):
        if self.useDefaultListener:
            self.start_listener()
        try:
            self.can_interface.connect()
        except CanInitializationError:
            console.print("[red]\nThere may be a problem with the configuration of your CAN-interface.\n")
            console.print(f"[grey]Current configuration of interface {self.interface_name!r}:")
            console.print(self.interface_configuration)
            raise
        self.status = 1  # connected

    def send(self, frame: bytes) -> None:
        # send the request
        self.pre_send_timestamp = self.timestamp.value
        self.can_interface.transmit(payload=pad_frame(frame, self.max_dlc_required, self.padding_value))
        self.post_send_timestamp = self.timestamp.value

    def close_connection(self):
        if hasattr(self, "can_interface"):
            self.can_interface.close()

    def close(self):
        self.finish_listener()
        self.close_connection()


def set_DLC(length: int):
    """Return DLC value according to CAN-FD.

    :param length: Length value to be mapped to a valid CAN-FD DLC.
                   ( 0 <= length <= 64)
    """

    if length < 0:
        raise ValueError("Non-negative length value required.")
    elif length <= MAX_DLC_CLASSIC:
        return length
    elif length <= 64:
        for dlc in CAN_FD_DLCS:
            if length <= dlc:
                return dlc
    else:
        raise ValueError("DLC could be at most 64.")


def calculate_filter(ids: list):
    """
    :param ids: An iterable (usually list or tuple) containing CAN identifiers.

    :return: Calculated filter and mask.
    :rtype: tuple (int, int)
    """
    any_extended_ids = any(is_extended_identifier(i) for i in ids)
    raw_ids = [stripIdentifier(i) for i in ids]
    cfilter = functools.reduce(operator.and_, raw_ids)
    cmask = functools.reduce(operator.or_, raw_ids) ^ cfilter
    cmask ^= 0x1FFFFFFF if any_extended_ids else 0x7FF
    return (cfilter, cmask)

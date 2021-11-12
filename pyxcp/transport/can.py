#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2021 by Christoph Schueler <cpu12.gems@googlemail.com>

   All Rights Reserved

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import abc
from bisect import bisect_left
from collections import OrderedDict
import functools
import operator
from time import perf_counter, time

from pyxcp.transport.base import BaseTransport
from pyxcp.config import Configuration


CAN_EXTENDED_ID         = 0x80000000
MAX_11_BIT_IDENTIFIER   = (1 << 11) - 1
MAX_29_BIT_IDENTIFIER   = (1 << 29) - 1
MAX_DLC_CLASSIC         = 8
CAN_FD_DLCS             = (12, 16, 20, 24, 32, 48, 64)  # Discrete CAN-FD DLCs in case DLC > 8.


class IdentifierOutOfRangeError(Exception):
    """Signals an identifier greater then :obj:`MAX_11_BIT_IDENTIFIER` or :obj:`MAX_29_BIT_IDENTIFIER`."""

    pass


def isExtendedIdentifier(identifier: int) -> bool:
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
    return identifier & (~CAN_EXTENDED_ID)


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


def padFrame(frame: bytes, padding_value: int, padding_len:int = 0) -> bytes:
    """Pad frame to next discrete DLC value.

    References:
    -----------
    ISO/DIS 15765 - 4; 8.2 Data length Code (DLC)
    AUTOSAR CP Release 4.3.0, Specification of CAN Transport Layer; 7.3.8 N-PDU padding
    AUTOSAR CP Release 4.3.0, Specification of CAN Driver; [SWS_CAN_00502], [ECUC_Can_00485]
    AUTOSAR CP Release 4.3.0, Requirements on CAN; [SRS_Can_01073], [SRS_Can_01086], [SRS_Can_01160]
    """
    frame_len = max(len(frame), padding_len)
    if frame_len <= MAX_DLC_CLASSIC:
        actual_len = MAX_DLC_CLASSIC
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
        self._is_extended = isExtendedIdentifier(raw_id)
        if self._is_extended:
            if self._id > MAX_29_BIT_IDENTIFIER:
                raise IdentifierOutOfRangeError("29-bit identifier '{}' is out of range".format(self._id))
        else:
            if self._id > MAX_11_BIT_IDENTIFIER:
                raise IdentifierOutOfRangeError("11-bit identifier '{}' is out of range".format(self._id))

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

    @staticmethod
    def make_identifier(identifier: int, extended: bool) -> int:
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

    def __eq__(self, other):
        return (self.id == other.id) and (self.is_extended == other.is_extended)

    def __str__(self):
        return "Identifier(id = 0x{:08x}, is_extended = {})".format(self.id, self.is_extended)

    def __repr__(self):
        return "Identifier(0x{:08x})".format(self.raw_id)


class Frame:
    """"""

    def __init__(self, id_: Identifier, dlc: int, data: bytes, timestamp: int):
        self.id = id_
        self.dlc = dlc
        self.data = data
        self.timestamp = timestamp

    def __repr__(self):
        return "Frame(id = 0x{:08x}, dlc = {}, data = {}, timestamp = {})".format(
            self.id, self.dlc, self.data, self.timestamp
        )

    __str__ = __repr__


class CanInterfaceBase(metaclass=abc.ABCMeta):
    """
    Abstract CAN interface handler that can be implemented for any actual CAN device driver
    """

    PARAMETER_MAP = {}

    @abc.abstractmethod
    def init(self, parent, receive_callback):
        """
        Must implement any required action for initing the can interface

        Parameters
        ----------
        parent: :class:`Can`
            Refers to owner.
        receive_callback: callable
            Receive callback function to register with the following argument: payload: bytes
        """

    @abc.abstractmethod
    def transmit(self, payload: bytes):
        """
        Must transmit the given payload on the master can id.

        Parameters
        ----------
        payload: bytes
            payload to transmit
        """

    @abc.abstractmethod
    def close(self):
        """ Must implement any required action for disconnecting from the can interface """

    @abc.abstractmethod
    def connect(self):
        """Open connection to can interface"""

    @abc.abstractmethod
    def read(self):
        """Read incoming data"""

    @abc.abstractmethod
    def getTimestampResolution(self):
        """Get timestamp resolution in nano seconds."""

    def loadConfig(self, config):
        """Load configuration data."""
        self.config = Configuration(self.PARAMETER_MAP or {}, config or {})


class EmptyHeader:
    """ There is no header for XCP on CAN  """

    def pack(self, *args, **kwargs):
        return b""


# can.detect_available_configs()


class Can(BaseTransport):
    """"""

    PARAMETER_MAP = {
        #                           Type            Req'd   Default
        "CAN_DRIVER":               (str,           True,   None),
        "CHANNEL":                  (str,           False,  ""),
        "MAX_DLC_REQUIRED":         (bool,          False,  False),
        "MAX_CAN_FD_DLC":           (int,           False,  64),
        "PADDING_VALUE":            (int,           False,   0),
        "CAN_USE_DEFAULT_LISTENER": (bool,          False,  True),
        # defaults to True, in this case the default listener thread is used.
        # If the canInterface implements a listener service, this parameter
        # can be set to False, and the default listener thread won't be started.
        "CAN_ID_MASTER":            (int,           True,   None),
        "CAN_ID_SLAVE":             (int,           True,   None),
        "CAN_ID_BROADCAST":         (int,           False,  None),
        "BITRATE":                  (int,           False,  250000),
        "RECEIVE_OWN_MESSAGES":     (bool,          False,  False),
    }

    PARAMETER_TO_KW_ARG_MAP = {
        "RECEIVE_OWN_MESSAGES": "receive_own_messages",
        "CHANNEL": "channel",
        "BITRATE": "bitrate",
    }

    MAX_DATAGRAM_SIZE = 7
    HEADER = EmptyHeader()
    HEADER_SIZE = 0

    def __init__(self, config=None):
        """init for CAN transport
        :param config: configuration
        """
        super().__init__(config)
        self.loadConfig(config)
        drivers = registered_drivers()
        interfaceName = self.config.get("CAN_DRIVER")
        if not interfaceName in drivers:
            raise ValueError(
                "{} is an invalid driver name -- choose from {}".format(interfaceName, [x for x in drivers.keys()])
            )
        canInterfaceClass = drivers[interfaceName]
        self.canInterface = canInterfaceClass()
        self.useDefaultListener = self.config.get("CAN_USE_DEFAULT_LISTENER")
        self.can_id_master = Identifier(self.config.get("CAN_ID_MASTER"))
        self.can_id_slave = Identifier(self.config.get("CAN_ID_SLAVE"))
        self.canInterface.loadConfig(config)
        self.canInterface.init(self, self.dataReceived)
        #
        # Regarding CAN-FD s. AUTOSAR CP Release 4.3.0, Requirements on CAN; [SRS_Can_01160] Padding of bytes due to discrete CAN FD DLC]:
        #   "... If a PDU does not exactly match these configurable sizes the unused bytes shall be padded."
        #
        self.max_dlc_required = self.config.get("MAX_DLC_REQUIRED") or self.canInterface.is_fd
        self.padding_value = self.config.get("PADDING_VALUE")
        self.padding_len = self.config.get("MAX_CAN_FD_DLC") if self.canInterface.is_fd else MAX_DLC_CLASSIC

    def dataReceived(self, payload: bytes, recv_timestamp: float = None):
        self.processResponse(payload, len(payload), counter=self.counterReceived + 1, recv_timestamp=recv_timestamp)

    def listen(self):
        while True:
            if self.closeEvent.isSet():
                return
            frame = self.canInterface.read()
            if frame:
                self.dataReceived(frame.data, frame.timestamp)

    def connect(self):
        if self.useDefaultListener:
            self.startListener()
        self.canInterface.connect()
        self.status = 1  # connected

    def send(self, frame):
        # XCP on CAN trailer: if required, FILL bytes must be appended
        if self.max_dlc_required:
            frame = padFrame(frame, self.padding_value, self.padding_len)
        # send the request
        if self.perf_counter_origin > 0:
            self.pre_send_timestamp = time()
            self.canInterface.transmit(payload = frame)
            self.post_send_timestamp = time()
        else:
            pre_send_timestamp = perf_counter()
            self.canInterface.transmit(payload = frame)
            post_send_timestamp = perf_counter()
            self.pre_send_timestamp = self.timestamp_origin + pre_send_timestamp - self.perf_counter_origin
            self.post_send_timestamp = self.timestamp_origin + post_send_timestamp - self.perf_counter_origin

    def closeConnection(self):
        if hasattr(self, "canInterface"):
            self.canInterface.close()

    def close(self):
        self.closeConnection()


def setDLC(length: int):
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


def calculateFilter(ids: list):
    """
    :param ids: An iterable (usually list or tuple) containing CAN identifiers.

    :return: Calculated filter and mask.
    :rtype: tuple (int, int)
    """
    any_extended_ids = any(isExtendedIdentifier(i) for i in ids)
    raw_ids = [stripIdentifier(i) for i in ids]
    cfilter = functools.reduce(operator.and_, raw_ids)
    cmask = functools.reduce(operator.or_, raw_ids) ^ cfilter
    cmask ^= 0x1FFFFFFF if any_extended_ids else 0x7FF
    return (cfilter, cmask)


def try_to_install_system_supplied_drivers():
    """Register available pyxcp CAN drivers."""
    import importlib
    import pkgutil
    import pyxcp.transport.candriver as cdr

    for _, modname, _ in pkgutil.walk_packages(cdr.__path__, "{}.".format(cdr.__name__)):
        try:
            importlib.import_module(modname)
        except Exception as e:
            pass


def registered_drivers():
    """
    Returns
    -------
    dict (name, class)
        Dictionary containing CAN driver names and classes of all
        available drivers (pyxcp supplied and user-defined).
    """
    sub_classes = CanInterfaceBase.__subclasses__()
    return OrderedDict(zip(([c.__name__ for c in sub_classes]), sub_classes))

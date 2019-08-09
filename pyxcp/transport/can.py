#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
"""

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2019 by Christoph Schueler <cpu12.gems@googlemail.com>

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
import functools
import operator

from pyxcp.transport.base import BaseTransport
from pyxcp.config import Configuration

CAN_EXTENDED_ID = 0x80000000


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
    """Get raw CAN identifier (remove `CAN_EXTENDED_ID` bit if present).

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


class Frame:
    """
    """
    def __init__(self, id_, dlc, data, timestamp):
        self.id = id_
        self.dlc = dlc
        self.data = data
        self.timestamp = timestamp

    def __repr__(self):
        return "Frame(id = 0x{:08x}, dlc = {}, data = {}, timestamp = {})".format(self.id, self.dlc, self.data, self.timestamp)

    __str__ = __repr__


class CanInterfaceBase(metaclass=abc.ABCMeta):
    """
    Abstract CAN interface handler that can be implemented for any actual CAN device driver
    """

    PARAMETER_MAP = {

    }

    @abc.abstractmethod
    def init(self, parent, master_id_with_ext: int, slave_id_with_ext: int, receive_callback):
        """
        Must implement any required action for initing the can interface
        :param master_id_with_ext: CAN ID on 32 bit, where MSB bit indicates extended ID format
        :param slave_id_with_ext: CAN ID on 32 bit, where MSB bit indicates extended ID format
        :param receive_callback: receive callback function to register with the following argument: payload: bytes
        """

    @abc.abstractmethod
    def transmit(self, payload: bytes):
        """
        Must transmit the given payload on the master can id.
        :param payload: payload to transmit
        :return:
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
        """Get timestamp resolution in nano seconds.
        """

    def loadConfig(self, config):
        """

        """
        self.config = Configuration(self.PARAMETER_MAP or {}, config or {})


class EmptyHeader:
    """ There is no header for XCP on CAN  """
    def pack(self, *args, **kwargs):
        return b''



# can.detect_available_configs()

class Can(BaseTransport):
    """

    """

    PARAMETER_MAP = {
        #                         Python attribute      Type    Req'd   Default
        "MAX_DLC_REQUIRED":     ("max_dlc_required",    bool,   False,  False),
        "CAN_ID_MASTER":        ("can_id_master",       int,    True,   None),
        "CAN_ID_SLAVE":         ("can_id_slave",        int,    True,   None),
        "CAN_ID_BROADCAST":     ("can_id_broadcast",    int,    False,  None),
        "BAUDRATE":             ("baudrate",            float,  False,  250000.0),
        "BTL_CYCLES":           ("btl_cycles",          int,    False,  16),
        "SAMPLE_RATE":          ("sample_rate",         int,    False,  1),
        "SAMPLE_POINT":         ("sample_point",        float,  False,  87.5),
        "SJW":                  ("sjw",                 int,    False,  2),
        "TSEG1":                ("tseg1",               int,    False,  5),
        "TSEG2":                ("tseg2",               int,    False,  2),
    }

    MAX_DATAGRAM_SIZE = 7
    HEADER = EmptyHeader()
    HEADER_SIZE = 0

    def __init__(self, canInterface: CanInterfaceBase, config=None, loglevel="WARN"):
        super().__init__(config, loglevel)
        if not issubclass(canInterface, CanInterfaceBase):
            raise TypeError('canInterface instance must inherit from CanInterface abstract base class!')
        self.canInterface = canInterface()

        """
        for key, (attr, tp, required, default) in PARAMETER_MAP.items():
            if hasattr(self.config, key):
                if not isinstance(getattr(self.config, key), tp):
                    raise TypeError("Parameter {} {} required".format(attr, tp))
                setattr(self, attr, getattr(self.config, key))
            else:
                if required:
                    raise AttributeError("{} must be specified in config!".format(key))
                else:
                    setattr(self, attr, default)
        """

        self.max_dlc_required = self.config.get("MAX_DLC_REQUIRED")
        self.can_id_master  = self.config.get("CAN_ID_MASTER")
        self.can_id_slave = self.config.get("CAN_ID_SLAVE")
        self.canInterface.init(self, self.can_id_master, self.can_id_slave, self.dataReceived)
        self.canInterface.loadConfig(config)

        self.startListener()

    def dataReceived(self, payload: bytes):
        self.processResponse(payload, len(payload), counter=0)

    def listen(self):
        while True:
            if self.closeEvent.isSet():
                return
            frame = self.canInterface.read()
            if frame:
                self.dataReceived(frame.data)


    def connect(self):
        self.canInterface.connect()
        self.status = 1  # connected

    def send(self, frame):
        # XCP on CAN trailer: if required, FILL bytes must be appended
        if self.max_dlc_required:
            # append fill bytes up to MAX DLC (=8)
            if len(frame) < 8:
                frame += b'\x00' * (8 - len(frame))
        # send the request
        self.canInterface.transmit(payload=frame)

    def closeConnection(self):
        if hasattr(self, "canInterface"):
            self.canInterface.close()


def setDLC(length: int):
    """Return DLC value according to CAN-FD.

    :param length: Length value to be mapped to a valid CAN-FD DLC.
                   ( 0 <= length <= 64)
    """
    FD_DLCS = (12, 16, 20, 24, 32, 48, 64)

    if length < 0:
        raise ValueError("Non-negative length value required.")
    elif length <= 8:
        return length
    elif length <= 64:
        for dlc in FD_DLCS:
            if length <= dlc:
                return dlc;
    else:
        raise ValueError("DLC could be at most 64.")


def calculateFilter(ids : list):
    """
    :param ids: An iterable (usually list or tuple) containing CAN identifiers.

    :return: Calculated filter and mask.
    :rtype: (int, int)
    """
    any_extended_ids = any(isExtendedIdentifier(i) for i in ids)
    raw_ids = [stripIdentifier(i) for i in ids]
    cfilter = functools.reduce(operator.and_, raw_ids)
    cmask = functools.reduce(operator.or_, raw_ids) ^ cfilter
    cmask ^= 0x1FFFFFFF if any_extended_ids else 0x7ff
    return (cfilter, cmask)


def register_drivers():
    """Register available CAN drivers.

    :return: Dictionary containing CAN driver names and classes.
    """
    import importlib
    import pkgutil
    import pyxcp.transport.candriver as cdr

    for _, modname, _ in pkgutil.walk_packages(cdr.__path__, "{}.".format(cdr.__name__)):
        try:
            importlib.import_module(modname)
        except Exception as e:
            pass

    sub_classes = CanInterfaceBase.__subclasses__()
    return dict(zip([c.__name__ for c in sub_classes], sub_classes))

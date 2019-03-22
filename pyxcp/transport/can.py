#!/usr/bin/env python
# -*- coding: utf-8 -*-

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

from pyxcp.transport.base import BaseTransport
import abc

DEFAULT_XCP_PORT = 5555


class CanInterfaceBase(metaclass=abc.ABCMeta):
    """
    Abstract CAN interface handler that can be implemented for any actual CAN device driver
    """

    @abc.abstractmethod
    def init(self, master_id_with_ext: int, slave_id_with_ext: int, receive_callback):
        """
        Must implement any required action for initing the can interface
        :param master_id_with_ext: CAN ID on 32 bit, where MSB bit indicates extended ID format
        :param slave_id_with_ext: CAN ID on 32 bit, where MSB bit indicates extended ID format
        :param receive_callback: receive callback function to register with the following argument: payload: bytes
        """
        pass

    @abc.abstractmethod
    def transmit(self, payload: bytes):
        """
        Must transmit the given payload on the master can id.
        :param payload: payload to transmit
        :return:
        """
        pass

    @abc.abstractmethod
    def close(self):
        """ Must implement any required action for disconnecting from the can interface """
        pass

    @abc.abstractmethod
    def connect(self):
        """Open connection to can interface"""
        pass


class EmptyHeader:
    """ There is no header for XCP on CAN  """
    def pack(self, *args, **kwargs):
        return b''


class Can(BaseTransport):

    MAX_DATAGRAM_SIZE = 7
    HEADER = EmptyHeader()
    HEADER_SIZE = 0

    def __init__(self, canInterface: CanInterfaceBase, config={}, loglevel="WARN"):
        super().__init__(config, loglevel)
        if not issubclass(canInterface.__class__, CanInterfaceBase):
            raise TypeError('canInterface instance must inherit from CanInterface abstract base class!')
        self.canInterface = canInterface
        self.status = 1  # connected
        if hasattr(self.config, 'MAX_DLC_REQUIRED'):
            if not isinstance(self.config.MAX_DLC_REQUIRED, bool):
                raise TypeError('bool required')
            self.max_dlc_required = self.config.MAX_DLC_REQUIRED
        else:
            self.max_dlc_required = False
        if hasattr(self.config, 'CAN_ID_MASTER'):
            if not isinstance(self.config.CAN_ID_MASTER, int):
                raise TypeError('int required')
            self.can_id_master = self.config.CAN_ID_MASTER
        else:
            raise AttributeError('CAN_ID_MASTER must be specified in config!')
        if hasattr(self.config, 'CAN_ID_SLAVE'):
            if not isinstance(self.config.CAN_ID_SLAVE, int):
                raise TypeError('int required')
            self.can_id_slave = self.config.CAN_ID_SLAVE
        else:
            raise AttributeError('CAN_ID_SLAVE must be specified in config!')
        self.canInterface.init(self.can_id_master, self.can_id_slave, self.dataReceived)
        self.startListener()

    def dataReceived(self, payload: bytes):
        self.processResponse(payload, len(payload), counter=0)

    def listen(self):
        pass

    def connect(self):
        self.CanInterface.connect()

    def send(self, frame):
        # XCP on CAN trailer: if required, FILL bytes must be appended
        if self.max_dlc_required:
            # append fill bytes up to MAX DLC (=8)
            if len(frame) < 8:
                frame += b'\x00' * (8 - len(frame))
        # send the request
        self.canInterface.transmit(payload=frame)

    def closeConnection(self):
        self.canInterface.close()

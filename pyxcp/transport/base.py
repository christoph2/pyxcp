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

import abc
from collections import deque
from datetime import datetime
import threading
from time import time, sleep

from ..logger import Logger
from ..utils import flatten, hexDump

import pyxcp.types as types
from pyxcp.config import Configuration

from ..timing import Timing


class Empty(Exception):
    pass


def get(q, timeout):
    """Get an item from a deque considering a timeout condition.
    """
    start = time()
    while not q:
        if time() - start > timeout:
            raise Empty
        sleep(0.001)

    item = q.popleft()
    return item


class BaseTransport(metaclass=abc.ABCMeta):
    """Base class for transport-layers (Can, Eth, Sxi).

    Parameters
    ----------
    config: dict-like
        Parameters like bitrate.
    loglevel: ["INFO", "WARN", "DEBUG", "ERROR", "CRITICAL"]
        Controls the verbosity of log messages.

    """

    def __init__(self, config=None, loglevel='WARN'):
        self.parent = None
        self.config = Configuration(self.PARAMETER_MAP or {}, config or {})
        self.closeEvent = threading.Event()
        self.logger = Logger("transport.Base")
        self.logger.setLevel(loglevel)
        self.counterSend = 0
        self.counterReceived = 0
        self.timing = Timing()
        self.resQueue = deque()
        self.daqQueue = deque()
        self.evQueue = deque()
        self.servQueue = deque()
        self.listener = threading.Thread(
            target=self.listen,
            args=(),
            kwargs={},
        )

        self.first_daq_timestamp = None

    def __del__(self):
        self.finishListener()
        self.closeConnection()

    def close(self):
        """Close the transport-layer connection and event-loop.
        """
        self.finishListener()
        if self.listener.is_alive():
            self.listener.join()
        self.closeConnection()

    @abc.abstractmethod
    def connect(self):
        pass

    def startListener(self):
        self.listener.start()

    def finishListener(self):
        if hasattr(self, "closeEvent"):
            self.closeEvent.set()

    def request(self, cmd, *data):
        self.logger.debug(cmd.name)
        self.parent._setService(cmd)
        cmdlen = cmd.bit_length()//8  # calculate bytes needed for cmd
        header = self.HEADER.pack(cmdlen + len(data), self.counterSend)
        self.counterSend = (self.counterSend + 1) & 0xffff

        frame = header + bytes(flatten(cmd.to_bytes(cmdlen, 'big'), data))
        self.logger.debug("-> {}".format(hexDump(frame)))
        self.timing.start()
        self.send(frame)

        try:
            xcpPDU = get(self.resQueue, timeout=2.0)
        except Empty:
            raise types.XcpTimeoutError("Response timed out.") from None

        self.timing.stop()

        pid = types.Response.parse(xcpPDU).type
        if pid == 'ERR' and cmd.name != 'SYNCH':
            err = types.XcpError.parse(xcpPDU[1:])
            raise types.XcpResponseError(err)
        else:
            pass    # Und nu??
        return xcpPDU[1:]

    def block_receive(self, length_required: int) -> bytes:
        """
        Implements packet reception for block communication model
        (e.g. for XCP on CAN)

        Parameters
        ----------
        length_required: int
            number of bytes to be expected in block response packets

        Returns
        -------
        bytes
            all payload bytes received in block response packets
        """
        block_response = b''
        while len(block_response) < length_required:
            if len(self.resQueue):
                partial_response = self.resQueue.popleft()
                block_response += partial_response[1:]
            """
            try:
                partial_response = self.resQueue.get(timeout=2.0)
                partial_response = self.resQueue.popleft()
                block_response += partial_response[1:]
            except queue.Empty:
                raise types.XcpTimeoutError("Response timed out.") from None
            """
        return block_response

    @abc.abstractmethod
    def send(self, frame):
        pass

    @abc.abstractmethod
    def closeConnection(self):
        """Does the actual connection shutdown.
        Needs to be implemented by any sub-class.
        """
        pass

    @abc.abstractmethod
    def listen(self):
        pass

    def processResponse(self, response, length, counter):
        self.counterReceived = counter
        if hasattr(self, 'use_tcp'):
            use_tcp = self.use_tcp
        else:
            use_tcp = False
        if not use_tcp:
            # for TCP this error cannot occur, instead a timeout
            # will be reaised while waiting for the correct number
            # of bytes to be received to complete the message
            if len(response) != length:
                raise types.FrameSizeError("Size mismatch.")
        pid = response[0]
        if pid >= 0xFC:
            self.logger.debug(
                "<- L{} C{} {}".format(
                    length,
                    counter,
                    hexDump(response),
                )
            )
            if pid >= 0xfe:
                # self.resQueue.put(response)
                self.resQueue.append(response)
            elif pid == 0xfd:
                # self.evQueue.put(response)
                self.evQueue.append(response)
            elif pid == 0xfc:
                # self.servQueue.put(response)
                self.servQueue.append(response)
        else:
            if self.first_daq_timestamp is None:
                self.first_daq_timestamp = datetime.now()
            # self.daqQueue.put((response, counter, length))
            self.daqQueue.append((response, counter, length))

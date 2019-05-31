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
import queue
import threading
import time

from ..logger import Logger
from ..utils import flatten, hexDump, PYTHON_VERSION

import pyxcp.types as types
from pyxcp.config import Config

from ..timing import Timing

from datetime import datetime


class BaseTransport(metaclass=abc.ABCMeta):

    def __init__(self, config=None, loglevel='WARN'):
        self.parent = None
        self.config = Config(config or {})
        self.closeEvent = threading.Event()
        self.logger = Logger("transport.Base")
        self.logger.setLevel(loglevel)
        self.counterSend = 0
        self.counterReceived = 0
        self.timing = Timing()
        self.resQueue = queue.Queue()
        self.daqQueue = queue.Queue()
        self.evQueue = queue.Queue()
        self.servQueue = queue.Queue()
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
        self.finishListener()
        if self.listener.isAlive():
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
        frame = self._prepare_request(cmd, *data)
        self.timing.start()
        self.send(frame)

        try:
            xcpPDU = self.resQueue.get(timeout=2.0)
        except queue.Empty:
            if PYTHON_VERSION >= (3, 3):
                raise types.XcpTimeoutError("Response timed out.") from None
            else:
                raise types.XcpTimeoutError("Response timed out.")
        self.resQueue.task_done()   # TODO: move up!?
        self.timing.stop()

        pid = types.Response.parse(xcpPDU).type
        if pid == 'ERR' and cmd.name != 'SYNCH':
            err = types.XcpError.parse(xcpPDU[1:])
            raise types.XcpResponseError(err)
        else:
            pass    # Und nu??
        return xcpPDU[1:]

    def block_request(self, cmd, *data):
        """
        Implements packet transmission for block communication model (e.g. DOWNLOAD block mode)
        All parameters are the same as in request(), but it does not receive response.
        """

        # check response queue before each block reauest, so that if the slave device
        # has responded with a negative response (e.g. ACCESS_DENIED or SEQUENCE_ERROR), we can
        # process it.
        try:
            xcpPDU = self.resQueue.get_nowait()
            pid = types.Response.parse(xcpPDU).type
            if pid == 'ERR' and cmd.name != 'SYNCH':
                err = types.XcpError.parse(xcpPDU[1:])
                raise types.XcpResponseError(err)
        except queue.Empty:
            pass

        frame = self._prepare_request(cmd, *data)
        self.send(frame)

    def _prepare_request(self, cmd, *data):
        """
        Prepares a request to be sent
        """
        self.logger.debug(cmd.name)
        self.parent._setService(cmd)
        cmdlen = cmd.bit_length() // 8  # calculate bytes needed for cmd
        header = self.HEADER.pack(cmdlen + len(data), self.counterSend)
        self.counterSend = (self.counterSend + 1) & 0xffff

        frame = header + bytes(flatten(cmd.to_bytes(cmdlen, 'big'), data))
        self.logger.debug("-> {}".format(hexDump(frame)))
        return frame

    def block_receive(self, length_required: int) -> bytes:
        """
        Implements packet reception for block communication model (e.g. for XCP on CAN)
        :param length_required: number of bytes to be expected in block response packets
        :return: all payload bytes received in block response packets
        """
        block_response = b''
        while len(block_response) < length_required:
            try:
                partial_response = self.resQueue.get(timeout=2.0)
                block_response += partial_response[1:]
            except queue.Empty:
                raise types.XcpTimeoutError("Response timed out.") from None
        return block_response

    @abc.abstractmethod
    def send(self, frame):
        pass

    @abc.abstractmethod
    def closeConnection(self):
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
                self.resQueue.put(response)
            elif pid == 0xfd:
                self.evQueue.put(response)
            elif pid == 0xfc:
                self.servQueue.put(response)
        else:
            if self.first_daq_timestamp is None:
                self.first_daq_timestamp = datetime.now()
            # we have to save timestamp here, so that if the slave device
            # does not provide timestamps we can have one.
            timestamp = time.perf_counter()
            self.daqQueue.put((response, counter, length, timestamp))

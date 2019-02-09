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

from ..logger import Logger
from ..utils import flatten, hexDump, PYTHON_VERSION

import pyxcp.types as types
from pyxcp.config import Config

from ..timing import Timing

from datetime import datetime


class BaseTransport(metaclass=abc.ABCMeta):

    def __init__(self, config=Config({}), loglevel='WARN'):
        self.parent = None
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
        self.listener.join()
        self.closeConnection()

    def startListener(self):
        self.listener.start()

    def finishListener(self):
        if hasattr(self, "closeEvent"):
            self.closeEvent.set()

    def request(self, cmd, *data):
        self.logger.debug(cmd.name)
        header = self.HEADER.pack(len(data) + 1, self.counterSend)
        self.counterSend += 1
        self.counterSend &= 0xffff
        frame = header + bytes(flatten(cmd, data))
        self.logger.debug("-> {}".format(hexDump(frame)))
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
        response = response
        if len(response) != length:
            raise types.FrameSizeError("Size mismatch.")
        pid = response[0]
        if pid >= 0xFC:
            self.logger.debug(
                "<- L{} C{} {}\n".format(
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
            self.daqQueue.put((response, counter, length))

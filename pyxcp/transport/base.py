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
import threading
from datetime import datetime
from time import time, sleep, get_clock_info

from ..logger import Logger
from ..utils import flatten, hexDump, time_perfcounter_correlation

import pyxcp.types as types
from pyxcp.config import Configuration

from ..timing import Timing


class Empty(Exception):
    pass


def get(q, timeout):
    """Get an item from a deque considering a timeout condition."""
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

    PARAMETER_MAP = {
        #                         Type    Req'd   Default
        "CREATE_DAQ_TIMESTAMPS": (bool, False, False),
        "LOGLEVEL": (str, False, "WARN"),
        "TIMEOUT": (float, False, 2.0),
        "ALIGNMENT": (int, False, 1),
    }

    def __init__(self, config=None):
        self.parent = None
        self.config = Configuration(BaseTransport.PARAMETER_MAP or {}, config or {})
        self.closeEvent = threading.Event()
        loglevel = self.config.get("LOGLEVEL")
        self._debug = loglevel == "DEBUG"

        self.logger = Logger("transport.Base")
        self.logger.setLevel(loglevel)
        self.counterSend = 0
        self.counterReceived = -1
        create_daq_timestamps = self.config.get("CREATE_DAQ_TIMESTAMPS")
        self.create_daq_timestamps = False if create_daq_timestamps is None else create_daq_timestamps
        timeout = self.config.get("TIMEOUT")
        self.alignment = self.config.get("ALIGNMENT")
        self.timeout = 2.0 if timeout is None else timeout
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
        self.cro_callback = None

        self.first_daq_timestamp = None
        if get_clock_info("time").resolution > 1e-5:
            ts, pc = time_perfcounter_correlation()
            self.timestamp_origin = ts
            self.datetime_origin = datetime.fromtimestamp(ts)
            self.perf_counter_origin = pc
        else:
            self.timestamp_origin = time()
            self.datetime_origin = datetime.fromtimestamp(self.timestamp_origin)

            # we will later use this to know if the current platform has a high
            # resolution time.time implementation
            self.perf_counter_origin = -1

        self.pre_send_timestamp = time()
        self.post_send_timestamp = time()
        self.recv_timestamp = time()

    def __del__(self):
        self.finishListener()
        self.closeConnection()

    def loadConfig(self, config):
        """Load configuration data."""
        self.config = Configuration(self.PARAMETER_MAP or {}, config or {})

    def close(self):
        """Close the transport-layer connection and event-loop."""
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
        frame = self._prepare_request(cmd, *data)
        self.timing.start()
        self.send(frame)

        try:
            xcpPDU = get(self.resQueue, timeout=self.timeout)
        except Empty:
            raise types.XcpTimeoutError("Response timed out (timeout={}s)".format(self.timeout)) from None

        self.timing.stop()

        pid = types.Response.parse(xcpPDU).type
        if pid == "ERR" and cmd.name != "SYNCH":
            err = types.XcpError.parse(xcpPDU[1:])
            raise types.XcpResponseError(err)
        else:
            pass  # Und nu??
        return xcpPDU[1:]

    def block_request(self, cmd, *data):
        """
        Implements packet transmission for block communication model (e.g. DOWNLOAD block mode)
        All parameters are the same as in request(), but it does not receive response.
        """

        # check response queue before each block request, so that if the slave device
        # has responded with a negative response (e.g. ACCESS_DENIED or SEQUENCE_ERROR), we can
        # process it.
        if self.resQueue:
            xcpPDU = self.resQueue.popleft()
            pid = types.Response.parse(xcpPDU).type
            if pid == "ERR" and cmd.name != "SYNCH":
                err = types.XcpError.parse(xcpPDU[1:])
                raise types.XcpResponseError(err)

        frame = self._prepare_request(cmd, *data)
        self.send(frame)

    def _prepare_request(self, cmd, *data):
        """
        Prepares a request to be sent
        """
        if self._debug:
            self.logger.debug(cmd.name)
        self.parent._setService(cmd)

        cmdlen = cmd.bit_length() // 8  # calculate bytes needed for cmd
        packet = bytes(flatten(cmd.to_bytes(cmdlen, "big"), data))

        header = self.HEADER.pack(len(packet), self.counterSend)
        self.counterSend = (self.counterSend + 1) & 0xFFFF

        frame = header + packet

        remainder = len(frame) % self.alignment
        if remainder:
            frame += b'\0' * (self.alignment - remainder)

        if self._debug:
            self.logger.debug("-> {}".format(hexDump(frame)))
        return frame

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

        Raises
        ------
        :class:`pyxcp.types.XcpTimeoutError`
        """
        TIMEOUT = 1.0  # TODO: parameter.
        block_response = b""
        start = time()
        while len(block_response) < length_required:
            if len(self.resQueue):
                partial_response = self.resQueue.popleft()
                block_response += partial_response[1:]
            else:
                if time() - start > TIMEOUT:
                    raise types.XcpTimeoutError("Response timed out [block_receive].") from None
                sleep(0.001)
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

    def processResponse(self, response, length, counter, recv_timestamp=None):
        if counter == self.counterReceived:
            self.logger.warn("Duplicate message counter {} received from the XCP slave".format(counter))
            if self._debug:
                self.logger.debug(
                    "<- L{} C{} {}".format(
                        length,
                        counter,
                        hexDump(response[:512]),
                    )
                )
            return

        self.counterReceived = counter

        pid = response[0]
        if pid >= 0xFC:
            if self._debug:
                self.logger.debug(
                    "<- L{} C{} {}".format(
                        length,
                        counter,
                        hexDump(response),
                    )
                )
            if pid >= 0xFE:
                # self.resQueue.put(response)
                self.resQueue.append(response)
                self.recv_timestamp = recv_timestamp
            elif pid == 0xFD:
                # self.evQueue.put(response)
                self.evQueue.append(response)
            elif pid == 0xFC:
                # self.servQueue.put(response)
                self.servQueue.append(response)
        else:
            if self._debug:
                self.logger.debug(
                    "<- L{} C{} ODT_Data[0:8] {}".format(
                        length,
                        counter,
                        hexDump(response[:8]),
                    )
                )
            if self.first_daq_timestamp is None:
                self.first_daq_timestamp = recv_timestamp
            if self.create_daq_timestamps:
                timestamp = recv_timestamp
            else:
                timestamp = 0.0
            element = (response, counter, length, timestamp)
            if self.cro_callback:
                self.cro_callback("DAQ", *element)
            self.daqQueue.append(element)


def createTransport(name, *args, **kws):
    """Factory function for transports.

    Returns
    -------
    :class:`BaseTransport` derived instance.
    """
    name = name.lower()
    transports = availableTransports()
    if name in transports:
        transportClass = transports[name]
    else:
        raise ValueError(
            "'{}' is an invalid transport -- please choose one of [{}].".format(name, " | ".join(transports.keys()))
        )
    return transportClass(*args, **kws)


def availableTransports():
    """List all subclasses of :class:`BaseTransport`.

    Returns
    -------
    dict
        name: class
    """
    transports = BaseTransport.__subclasses__()
    return {t.__name__.lower(): t for t in transports}

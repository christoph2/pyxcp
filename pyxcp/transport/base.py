#!/usr/bin/env python
import abc
import threading
import typing
from collections import deque

# from datetime import datetime
from time import sleep

import pyxcp.types as types

from ..cpp_ext import Timestamp, TimestampType
from ..recorder import XcpLogFileWriter
from ..timing import Timing
from ..utils import (
    SHORT_SLEEP,
    CurrentDatetime,
    flatten,
    hexDump,
    seconds_to_nanoseconds,
)


class FrameAcquisitionPolicy:
    """
    Base class for all frame acquisition policies.

    Parameters
    ---------
    filter_out: set or None
        A set of frame types to filter out.
        If None, all frame types are accepted for further processing.

        Example: (FrameType.REQUEST, FrameType.RESPONSE, FrameType.EVENT, FrameType.SERV)
                  ==> care only about DAQ frames.
    """

    def __init__(self, filter_out: typing.Optional[typing.Set[types.FrameCategory]] = None):
        self._frame_types_to_filter_out = filter_out or set()

    @property
    def filtered_out(self) -> typing.Set[types.FrameCategory]:
        return self._frame_types_to_filter_out

    def feed(self, frame_type: types.FrameCategory, counter: int, timestamp: int, payload: bytes) -> None: ...  # noqa: E704

    def finalize(self, *args) -> None:
        """
        Finalize the frame acquisition policy (if required).
        """
        ...


class NoOpPolicy(FrameAcquisitionPolicy):
    """
    No operation / do nothing policy.
    """


class LegacyFrameAcquisitionPolicy(FrameAcquisitionPolicy):
    """Dequeue based frame acquisition policy.

    Deprecated: Use only for compatibility reasons.
    """

    def __init__(self, filter_out: typing.Optional[typing.Set[types.FrameCategory]] = None):
        super().__init__(filter_out)
        self.reqQueue = deque()
        self.resQueue = deque()
        self.daqQueue = deque()
        self.evQueue = deque()
        self.servQueue = deque()
        self.metaQueue = deque()
        self.errorQueue = deque()
        self.stimQueue = deque()
        self.QUEUE_MAP = {
            types.FrameCategory.CMD: self.reqQueue,
            types.FrameCategory.RESPONSE: self.resQueue,
            types.FrameCategory.EVENT: self.evQueue,
            types.FrameCategory.SERV: self.servQueue,
            types.FrameCategory.DAQ: self.daqQueue,
            types.FrameCategory.METADATA: self.metaQueue,
            types.FrameCategory.ERROR: self.errorQueue,
            types.FrameCategory.STIM: self.stimQueue,
        }

    def feed(self, frame_type: types.FrameCategory, counter: int, timestamp: int, payload: bytes) -> None:
        # print(f"{frame_type.name:8} {counter:6}  {timestamp:7.7f} {hexDump(payload)}")
        if frame_type not in self.filtered_out:
            self.QUEUE_MAP.get(frame_type).append((counter, timestamp, payload))


class FrameRecorderPolicy(FrameAcquisitionPolicy):
    """Frame acquisition policy that records frames."""

    def __init__(
        self,
        file_name: str,
        filter_out: typing.Optional[typing.Set[types.FrameCategory]] = None,
        prealloc: int = 10,
        chunk_size: int = 1,
    ):
        super().__init__(filter_out)
        self.recorder = XcpLogFileWriter(file_name, prealloc=prealloc, chunk_size=chunk_size)

    def feed(self, frame_type: types.FrameCategory, counter: int, timestamp: int, payload: bytes) -> None:
        if frame_type not in self.filtered_out:
            self.recorder.add_frame(frame_type, counter, timestamp, payload)

    def finalize(self) -> None:
        self.recorder.finalize()


class StdoutPolicy(FrameAcquisitionPolicy):
    """Frame acquisition policy that prints frames to stdout."""

    def __init__(self, filter_out: typing.Optional[typing.Set[types.FrameCategory]] = None):
        super().__init__(filter_out)

    def feed(self, frame_type: types.FrameCategory, counter: int, timestamp: int, payload: bytes) -> None:
        if frame_type not in self.filtered_out:
            print(f"{frame_type.name:8} {counter:6}  {timestamp:8u} {hexDump(payload)}")


class EmptyFrameError(Exception):
    """Raised when an empty frame is received."""


class BaseTransport(metaclass=abc.ABCMeta):
    """Base class for transport-layers (Can, Eth, Sxi).

    Parameters
    ----------
    config: dict-like
        Parameters like bitrate.
    loglevel: ["INFO", "WARN", "DEBUG", "ERROR", "CRITICAL"]
        Controls the verbosity of log messages.

    """

    def __init__(self, config, policy: FrameAcquisitionPolicy = None):
        self.parent = None
        self.policy = policy or LegacyFrameAcquisitionPolicy()
        self.closeEvent = threading.Event()

        self.command_lock = threading.Lock()
        self.policy_lock = threading.Lock()

        self.logger = config.log
        self._debug = self.logger.level == 10

        self.counterSend: int = 0
        self.counterReceived: int = -1
        self.create_daq_timestamps = config.create_daq_timestamps
        timestamp_mode = TimestampType.ABSOLUTE_TS if config.timestamp_mode == "ABSOLUTE" else TimestampType.RELATIVE_TS
        self.timestamp = Timestamp(timestamp_mode)

        # Reference point for timestamping (may relative).
        self._start_datetime = CurrentDatetime(self.timestamp.initial_value)

        print(self._start_datetime)
        self.alignment = config.alignment
        self.timeout = seconds_to_nanoseconds(config.timeout)
        self.timer_restart_event = threading.Event()
        self.timing = Timing()
        self.resQueue = deque()
        self.listener = threading.Thread(
            target=self.listen,
            args=(),
            kwargs={},
        )

        self.first_daq_timestamp = None

        # self.timestamp_origin = self.timestamp.value
        # self.datetime_origin = datetime.fromtimestamp(self.timestamp_origin)

        self.pre_send_timestamp = self.timestamp.value
        self.post_send_timestamp = self.timestamp.value
        self.recv_timestamp = self.timestamp.value

    def __del__(self):
        self.finishListener()
        self.closeConnection()

    def load_config(self, config):
        """Load configuration data."""
        class_name = self.__class__.__name__.lower()
        self.config = getattr(config, class_name)

    def close(self):
        """Close the transport-layer connection and event-loop."""
        self.finishListener()
        if self.listener.is_alive():
            self.listener.join()
        self.closeConnection()

    @abc.abstractmethod
    def connect(self):
        pass

    def get(self):
        """Get an item from a deque considering a timeout condition."""
        start = self.timestamp.value
        while not self.resQueue:
            if self.timer_restart_event.is_set():
                start = self.timestamp.value
                self.timer_restart_event.restart_event.clear()
            if self.timestamp.value - start > self.timeout:
                raise EmptyFrameError
            sleep(SHORT_SLEEP)
        item = self.resQueue.popleft()
        # print("Q", item)
        return item

    @property
    def start_datetime(self) -> int:
        """"""
        return self._start_datetime

    def startListener(self):
        if self.listener.is_alive():
            self.finishListener()
            self.listener.join()

        self.listener = threading.Thread(target=self.listen)
        self.listener.start()

    def finishListener(self):
        if hasattr(self, "closeEvent"):
            self.closeEvent.set()

    def _request_internal(self, cmd, ignore_timeout=False, *data):
        with self.command_lock:
            frame = self._prepare_request(cmd, *data)
            self.timing.start()
            with self.policy_lock:
                self.policy.feed(types.FrameCategory.CMD, self.counterSend, self.timestamp.value, frame)
            self.send(frame)
            try:
                xcpPDU = self.get()
            except EmptyFrameError:
                if not ignore_timeout:
                    MSG = f"Response timed out (timeout={self.timeout}s)"
                    with self.policy_lock:
                        self.policy.feed(types.FrameCategory.METADATA, self.counterSend, self.timestamp.value, bytes(MSG, "ascii"))
                    raise types.XcpTimeoutError(MSG) from None
                else:
                    self.timing.stop()
                    return
            self.timing.stop()
            pid = types.Response.parse(xcpPDU).type
            if pid == "ERR" and cmd.name != "SYNCH":
                with self.policy_lock:
                    self.policy.feed(types.FrameCategory.ERROR, self.counterReceived, self.timestamp.value, xcpPDU[1:])
                err = types.XcpError.parse(xcpPDU[1:])
                raise types.XcpResponseError(err)
            return xcpPDU[1:]

    def request(self, cmd, *data):
        return self._request_internal(cmd, False, *data)

    def request_optional_response(self, cmd, *data):
        return self._request_internal(cmd, True, *data)

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
        with self.command_lock:
            if isinstance(*data, list):
                data = data[0]  # C++ interfacing.
            frame = self._prepare_request(cmd, *data)
            with self.policy_lock:
                self.policy.feed(
                    types.FrameCategory.CMD if int(cmd) >= 0xC0 else types.FrameCategory.STIM,
                    self.counterSend,
                    self.timestamp.value,
                    frame,
                )
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
            frame += b"\0" * (self.alignment - remainder)

        if self._debug:
            self.logger.debug(f"-> {hexDump(frame)}")
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
        block_response = b""
        start = self.timestamp.value
        while len(block_response) < length_required:
            if len(self.resQueue):
                partial_response = self.resQueue.popleft()
                block_response += partial_response[1:]
            else:
                if self.timestamp.value - start > self.timeout:
                    raise types.XcpTimeoutError("Response timed out [block_receive].") from None
                sleep(SHORT_SLEEP)
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

    def process_event_packet(self, packet):
        packet = packet[1:]
        ev_type = packet[0]
        self.logger.debug(f"EVENT-PACKET: {hexDump(packet)}")
        if ev_type == types.Event.EV_CMD_PENDING:
            self.timer_restart_event.set()

    def processResponse(self, response, length, counter, recv_timestamp=None):
        if counter == self.counterReceived:
            self.logger.warning(f"Duplicate message counter {counter} received from the XCP slave")
            if self._debug:
                self.logger.debug(f"<- L{length} C{counter} {hexDump(response[:512])}")
            return
        self.counterReceived = counter
        pid = response[0]
        if pid >= 0xFC:
            if self._debug:
                self.logger.debug(f"<- L{length} C{counter} {hexDump(response)}")
            if pid >= 0xFE:
                self.resQueue.append(response)
                with self.policy_lock:
                    self.policy.feed(types.FrameCategory.RESPONSE, self.counterReceived, self.timestamp.value, response)
                self.recv_timestamp = recv_timestamp
            elif pid == 0xFD:
                self.process_event_packet(response)
                with self.policy_lock:
                    self.policy.feed(types.FrameCategory.EVENT, self.counterReceived, self.timestamp.value, response)
            elif pid == 0xFC:
                with self.policy_lock:
                    self.policy.feed(types.FrameCategory.SERV, self.counterReceived, self.timestamp.value, response)
        else:
            if self._debug:
                self.logger.debug(f"<- L{length} C{counter} ODT_Data[0:8] {hexDump(response[:8])}")
            if self.first_daq_timestamp is None:
                self.first_daq_timestamp = recv_timestamp
            if self.create_daq_timestamps:
                timestamp = recv_timestamp
            else:
                timestamp = 0.0
            with self.policy_lock:
                self.policy.feed(types.FrameCategory.DAQ, self.counterReceived, timestamp, response)


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
        raise ValueError(f"{name!r} is an invalid transport -- please choose one of [{' | '.join(transports.keys())}].")
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

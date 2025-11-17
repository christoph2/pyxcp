#!/usr/bin/env python
import abc
import logging
import threading
from collections import deque
from typing import Any, Dict, Optional, Type
from pyxcp.timing import Timing
import pyxcp.types as types

from pyxcp.cpp_ext.cpp_ext import Timestamp, TimestampType
from pyxcp.transport.transport_ext import (
    FrameCategory,
    FrameAcquisitionPolicy,
    LegacyFrameAcquisitionPolicy,
    XcpFraming,
    XcpFramingConfig,
    XcpTransportLayerType,  # noqa: F401
    ChecksumType,  # noqa: F401
)
from pyxcp.utils import (
    CurrentDatetime,
    hexDump,
    seconds_to_nanoseconds,
    short_sleep,
)


class EmptyFrameError(Exception):
    """Raised when an empty frame is received."""


def parse_header_format(header_format: str) -> tuple:
    """SxI and USB framing is configurable."""
    if header_format == "HEADER_LEN_BYTE":
        return 1, 0, 0
    elif header_format == "HEADER_LEN_CTR_BYTE":
        return 1, 1, 0
    elif header_format == "HEADER_LEN_FILL_BYTE":
        return 1, 0, 1
    elif header_format == "HEADER_LEN_WORD":
        return 2, 0, 0
    elif header_format == "HEADER_LEN_CTR_WORD":
        return 2, 2, 0
    elif header_format == "HEADER_LEN_FILL_WORD":
        return 2, 0, 2
    else:
        raise ValueError(f"Invalid header format: {header_format}")


class BaseTransport(metaclass=abc.ABCMeta):
    """Base class for transport-layers (Can, Eth, Sxi).

    Parameters
    ----------
    config: dict-like
        Parameters like bitrate.
    loglevel: ["INFO", "WARN", "DEBUG", "ERROR", "CRITICAL"]
        Controls the verbosity of log messages.

    """

    def __init__(
        self,
        config,
        framing_config: XcpFramingConfig,
        policy: Optional[FrameAcquisitionPolicy] = None,
        transport_layer_interface: Optional[Any] = None,
    ):
        self.has_user_supplied_interface: bool = transport_layer_interface is not None
        self.transport_layer_interface: Optional[Any] = transport_layer_interface
        self.parent = None
        self.framing = XcpFraming(framing_config)
        self.policy: FrameAcquisitionPolicy = policy or LegacyFrameAcquisitionPolicy()
        self.closeEvent: threading.Event = threading.Event()

        self.command_lock: threading.Lock = threading.Lock()
        self.policy_lock: threading.Lock = threading.Lock()

        self.logger = logging.getLogger("PyXCP")
        self._debug: bool = self.logger.level == 10
        if transport_layer_interface:
            self.logger.info(f"Transport - User Supplied Transport-Layer Interface: '{transport_layer_interface!s}'")
        self.counter_received: int = -1
        self.create_daq_timestamps: bool = config.create_daq_timestamps
        self.timestamp = Timestamp(TimestampType.ABSOLUTE_TS)
        self._start_datetime: CurrentDatetime = CurrentDatetime(self.timestamp.initial_value)
        self.alignment: int = config.alignment
        self.timeout: int = seconds_to_nanoseconds(config.timeout)
        self.timer_restart_event: threading.Event = threading.Event()
        self.timing: Timing = Timing()
        self.resQueue: deque = deque()
        self.listener: threading.Thread = threading.Thread(
            target=self.listen,
            args=(),
            kwargs={},
            daemon=True,
        )

        self.first_daq_timestamp: Optional[int] = None
        # self.timestamp_origin = self.timestamp.value
        # self.datetime_origin = datetime.fromtimestamp(self.timestamp_origin)
        self.pre_send_timestamp: int = self.timestamp.value
        self.post_send_timestamp: int = self.timestamp.value
        self.recv_timestamp: int = self.timestamp.value
        # Ring buffer for last PDUs to aid diagnostics on failures
        try:
            from collections import deque as _dq

            self._last_pdus = _dq(maxlen=200)
        except Exception:
            self._last_pdus = []

    def __del__(self) -> None:
        self.finish_listener()
        self.close_connection()

    def load_config(self, config) -> None:
        """Load configuration data."""
        class_name: str = self.__class__.__name__.lower()
        self.config: Any = getattr(config, class_name)

    def close(self) -> None:
        """Close the transport-layer connection and event-loop."""
        self.finish_listener()
        # Avoid indefinite blocking on buggy threads
        try:
            if self.listener.is_alive():
                self.listener.join(timeout=2.0)
        except Exception:
            pass
        self.close_connection()

    @abc.abstractmethod
    def connect(self) -> None:
        pass

    def get(self):
        """Get an item from a deque considering a timeout condition."""
        start: int = self.timestamp.value
        while not self.resQueue:
            if self.timer_restart_event.is_set():
                start: int = self.timestamp.value
                self.timer_restart_event.clear()
            if self.timestamp.value - start > self.timeout:
                raise EmptyFrameError
            short_sleep()
        item = self.resQueue.popleft()
        return item

    @property
    def start_datetime(self) -> int:
        """datetime of program start.

        Returns
        -------
        int
        """
        return self._start_datetime

    def start_listener(self):
        if self.listener.is_alive():
            self.finish_listener()
            # Avoid indefinite blocking on buggy threads
            self.listener.join(timeout=2.0)

        # Ensure the close event is cleared before starting a new listener thread.
        if hasattr(self, "closeEvent"):
            self.closeEvent.clear()

        self.listener = threading.Thread(target=self.listen, daemon=True)
        self.listener.start()

    def finish_listener(self):
        if hasattr(self, "closeEvent"):
            self.closeEvent.set()

    def _request_internal(self, cmd, ignore_timeout=False, *data):
        with self.command_lock:
            frame = self._prepare_request(cmd, *data)
            self.timing.start()
            with self.policy_lock:
                self.policy.feed(FrameCategory.CMD, self.framing.counter_send, self.timestamp.value, frame)
            self.send(frame)
            try:
                xcpPDU = self.get()
            except EmptyFrameError:
                if not ignore_timeout:
                    MSG = f"Response timed out (timeout={self.timeout / 1_000_000_000}s)"
                    with self.policy_lock:
                        self.policy.feed(
                            FrameCategory.METADATA, self.framing.counter_send, self.timestamp.value, bytes(MSG, "ascii")
                        ) if self._diagnostics_enabled() else ""
                    self.logger.debug("XCP request timeout", extra={"event": "timeout", "command": cmd.name})
                    raise types.XcpTimeoutError(MSG) from None
                else:
                    self.timing.stop()
                    return
            self.timing.stop()
            pid = types.Response.parse(xcpPDU).type
            if pid == "ERR" and cmd.name != "SYNCH":
                with self.policy_lock:
                    self.policy.feed(FrameCategory.ERROR, self.counter_received, self.timestamp.value, xcpPDU[1:])
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
            if isinstance(data, list):
                data = data[0]  # C++ interfacing.
            frame = self._prepare_request(cmd, *data)
            with self.policy_lock:
                self.policy.feed(
                    FrameCategory.CMD if int(cmd) >= 0xC0 else FrameCategory.STIM,
                    self.framing.counter_send,
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
        frame = self.framing.prepare_request(cmd, *data)
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
                    waited = (self.timestamp.value - start) / 1e9 if hasattr(self.timestamp, "value") else None
                    msg = f"Response timed out [block_receive]: received {len(block_response)} of {length_required} bytes"
                    if waited is not None:
                        msg += f" after {waited:.3f}s"
                    # Attach diagnostics
                    # diag = self._build_diagnostics_dump() if self._diagnostics_enabled() else ""
                    self.logger.debug("XCP block_receive timeout", extra={"event": "timeout"})
                    raise types.XcpTimeoutError(msg) from None
                short_sleep()
        return block_response

    @abc.abstractmethod
    def send(self, frame):
        pass

    @abc.abstractmethod
    def close_connection(self):
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

    def process_response(self, response: bytes, length: int, counter: int, recv_timestamp: int) -> None:
        # Important: determine PID first so duplicate counter handling can be applied selectively.
        pid = response[0]

        if pid >= 0xFC:
            # Do not drop RESPONSE/EVENT/SERV frames even if the transport counter repeats.
            # Some slaves may reuse the counter while DAQ traffic is active, and we must not lose
            # command responses; otherwise request() can stall until timeout.
            if self._debug:
                self.logger.debug(f"<- L{length} C{counter} {hexDump(response)}")
            self.counter_received = counter
            # Record incoming non-DAQ frames for diagnostics
            self._record_pdu(
                "in",
                (FrameCategory.RESPONSE if pid >= 0xFE else FrameCategory.SERV if pid == 0xFC else FrameCategory.EVENT),
                counter,
                recv_timestamp,
                response,
                length,
            )
            if pid >= 0xFE:
                self.resQueue.append(response)
                with self.policy_lock:
                    self.policy.feed(FrameCategory.RESPONSE, self.counter_received, self.timestamp.value, response)
                self.recv_timestamp = recv_timestamp
            elif pid == 0xFD:
                self.process_event_packet(response)
                with self.policy_lock:
                    self.policy.feed(FrameCategory.EVENT, self.counter_received, self.timestamp.value, response)
            elif pid == 0xFC:
                with self.policy_lock:
                    self.policy.feed(FrameCategory.SERV, self.counter_received, self.timestamp.value, response)
        else:
            # DAQ traffic: Some transports reuse or do not advance the counter for DAQ frames.
            # Do not drop DAQ frames on duplicate counters to avoid losing measurements.
            if counter == self.counter_received:
                self.logger.debug(f"Duplicate message counter {counter} received (DAQ) - not dropping")
                # DAQ still flowing – reset request timeout window to avoid false timeouts while
                # the slave is busy but has not yet responded to a command.
                self.timer_restart_event.set()
                # Fall through and process the frame as usual.
            self.counter_received = counter
            if self._debug:
                self.logger.debug(f"<- L{length} C{counter} ODT_Data[0:8] {hexDump(response[:8])}")
            if self.first_daq_timestamp is None:
                self.first_daq_timestamp = recv_timestamp
            if self.create_daq_timestamps:
                timestamp = recv_timestamp
            else:
                timestamp = 0
            # Record DAQ frame (only keep small prefix in payload string later)
            self._record_pdu("in", FrameCategory.DAQ, counter, timestamp, response, length)
            # DAQ activity indicates the slave is alive/busy; keep extending the wait window for any
            # outstanding request, similar to EV_CMD_PENDING behavior on stacks that don't emit it.
            self.timer_restart_event.set()
            with self.policy_lock:
                self.policy.feed(FrameCategory.DAQ, self.counter_received, timestamp, response)

    def _record_pdu(
        self,
        direction: str,
        category: FrameCategory,
        counter: int,
        timestamp: int,
        payload: bytes,
        length: Optional[int] = None,
    ) -> None:
        try:
            entry = {
                "dir": direction,
                "cat": category.name,
                "ctr": int(counter),
                "ts": int(timestamp),
                "len": int(length if length is not None else len(payload)),
                "data": hexDump(payload if category != FrameCategory.DAQ else payload[:8])[:512],
            }
            self._last_pdus.append(entry)
        except Exception:
            pass  # nosec

    def _build_diagnostics_dump(self) -> str:
        import json as _json

        # transport params
        tp = {"transport": self.__class__.__name__}
        cfg = getattr(self, "config", None)
        # Extract common Eth/Can fields when available
        for key in (
            "host",
            "port",
            "protocol",
            "ipv6",
            "bind_to_address",
            "bind_to_port",
            "fd",
            "bitrate",
            "data_bitrate",
            "can_id_master",
            "can_id_slave",
        ):
            if cfg is not None and hasattr(cfg, key):
                try:
                    tp[key] = getattr(cfg, key)
                except Exception:
                    pass  # nosec
        last_n = 20
        try:
            app = getattr(self.config, "parent", None)
            app = getattr(app, "parent", None)
            if app is not None and hasattr(app, "general") and hasattr(app.general, "diagnostics_last_pdus"):
                last_n = int(app.general.diagnostics_last_pdus or last_n)
        except Exception:
            pass  # nosec
        pdus = list(self._last_pdus)[-last_n:]
        payload = {
            "transport_params": tp,
            "last_pdus": pdus,
        }
        try:
            body = _json.dumps(payload, ensure_ascii=False, default=str, indent=2)
        except Exception:
            body = str(payload)
        # Add a small header to explain what follows
        header = "--- Diagnostics (for troubleshooting) ---"
        return f"{header}\n{body}"

    def _diagnostics_enabled(self) -> bool:
        try:
            app = getattr(self.config, "parent", None)
            app = getattr(app, "parent", None)
            if app is not None and hasattr(app, "general"):
                return bool(getattr(app.general, "diagnostics_on_failure", True))
        except Exception:
            return True
        return True

    # @abc.abstractproperty
    # @property
    # def transport_layer_interface(self) -> Any:
    #    pass

    # @transport_layer_interface.setter
    # def transport_layer_interface(self, value: Any) -> None:
    #    self._transport_layer_interface = value


def create_transport(name: str, *args, **kws) -> BaseTransport:
    """Factory function for transports.

    Returns
    -------
    :class:`BaseTransport` derived instance.
    """
    name = name.lower()
    transports = available_transports()
    if name in transports:
        transport_class: Type[BaseTransport] = transports[name]
    else:
        raise ValueError(f"{name!r} is an invalid transport -- please choose one of [{' | '.join(transports.keys())}].")
    return transport_class(*args, **kws)


def available_transports() -> Dict[str, Type[BaseTransport]]:
    """List all subclasses of :class:`BaseTransport`.

    Returns
    -------
    dict
        name: class
    """
    transports = BaseTransport.__subclasses__()
    return {t.__name__.lower(): t for t in transports}

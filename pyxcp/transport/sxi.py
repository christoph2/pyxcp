import threading
from collections import deque
from dataclasses import dataclass
from typing import Any, Optional

import serial

from pyxcp.transport.transport_ext import (
    SxiFrLBCN,
    SxiFrLBC8,
    SxiFrLBC16,
    SxiFrLCBCN,
    SxiFrLCBC8,
    SxiFrLCBC16,
    SxiFrLFBCN,
    SxiFrLFBC8,
    SxiFrLFBC16,
    SxiFrLWCN,
    SxiFrLWC8,
    SxiFrLWC16,
    SxiFrLCWCN,
    SxiFrLCWC8,
    SxiFrLCWC16,
    SxiFrLFWCN,
    SxiFrLFWC8,
    SxiFrLFWC16,
)

from pyxcp.transport.base import (
    BaseTransport,
    ChecksumType,
    XcpFramingConfig,
    XcpTransportLayerType,
    parse_header_format,
)


@dataclass
class HeaderValues:
    length: int = 0
    counter: int = 0
    filler: int = 0


RECV_SIZE = 16384


def get_receiver_class(header_format: str, checksum_format: str) -> Any:
    COLUMN = {"NO_CHECKSUM": 0, "CHECKSUM_BYTE": 1, "CHECKSUM_WORD": 2}
    FORMATS = {
        "HEADER_LEN_BYTE": (SxiFrLBCN, SxiFrLBC8, SxiFrLBC16),
        "HEADER_LEN_CTR_BYTE": (SxiFrLCBCN, SxiFrLCBC8, SxiFrLCBC16),
        "HEADER_LEN_FILL_BYTE": (SxiFrLFBCN, SxiFrLFBC8, SxiFrLFBC16),
        "HEADER_LEN_WORD": (SxiFrLWCN, SxiFrLWC8, SxiFrLWC16),
        "HEADER_LEN_CTR_WORD": (SxiFrLCWCN, SxiFrLCWC8, SxiFrLCWC16),
        "HEADER_LEN_FILL_WORD": (SxiFrLFWCN, SxiFrLFWC8, SxiFrLFWC16),
    }
    return FORMATS[header_format][COLUMN[checksum_format]]


class SxI(BaseTransport):
    """"""

    def __init__(self, config=None, policy=None, transport_layer_interface: Optional[serial.Serial] = None) -> None:
        self.load_config(config)
        self.port_name = self.config.port
        self.baudrate = self.config.bitrate
        self.bytesize = self.config.bytesize
        self.parity = self.config.parity
        self.stopbits = self.config.stopbits
        self.mode = self.config.mode
        header_len, header_ctr, header_fill = parse_header_format(self.config.header_format)
        tail_cs_map = {
            "NO_CHECKSUM": ChecksumType.NO_CHECKSUM,
            "CHECKSUM_BYTE": ChecksumType.BYTE_CHECKSUM,
            "CHECKSUM_WORD": ChecksumType.WORD_CHECKSUM,
        }
        # self._listener_running = threading.Event()
        tail_cs = tail_cs_map[self.config.tail_format]
        ReceiverKlass = get_receiver_class(self.config.header_format, self.config.tail_format)
        self.receiver = ReceiverKlass(self.frame_dispatcher)
        framing_config = XcpFramingConfig(
            transport_layer_type=XcpTransportLayerType.SXI,
            header_len=header_len,
            header_ctr=header_ctr,
            header_fill=header_fill,
            tail_fill=False,
            tail_cs=tail_cs,
        )
        super().__init__(config, framing_config, policy, transport_layer_interface)
        self.tail_format = self.config.tail_format
        self.esc_sync = self.config.esc_sync
        self.esc_esc = self.config.esc_esc
        self.comm_port: serial.Serial

        if self.has_user_supplied_interface and transport_layer_interface:
            self.comm_port = transport_layer_interface
        else:
            self.logger.info(f"XCPonSxI - trying to open serial comm_port {self.port_name!r}.")
            try:
                self.comm_port = serial.Serial(
                    port=self.port_name,
                    baudrate=self.baudrate,
                    bytesize=self.bytesize,
                    parity=self.parity,
                    stopbits=self.stopbits,
                    timeout=0.1,  # self.timeout,
                    write_timeout=self.timeout,
                )
            except serial.SerialException as e:
                self.logger.critical(f"XCPonSxI - {e}")
                raise
        self._condition = threading.Condition()
        self._frames = deque()
        # self._frame_listener = threading.Thread(
        #    target=self._frame_listen,
        #    args=(),
        #    kwargs={},
        # )

    def __del__(self) -> None:
        self.close_connection()

    def connect(self) -> None:
        self.logger.info(
            f"XCPonSxI - serial comm_port {self.comm_port.portstr!r} openend "
            f"[{self.baudrate}/{self.bytesize}-{self.parity}-{self.stopbits}] "
            f"mode: {self.config.mode}"
        )
        self.logger.info(f"Framing: {self.config.header_format} {self.config.tail_format}")
        self.start_listener()

    def output(self, enable) -> None:
        if enable:
            self.comm_port.rts = False
            self.comm_port.dtr = False
        else:
            self.comm_port.rts = True
            self.comm_port.dtr = True

    def flush(self) -> None:
        self.comm_port.flush()

    def start_listener(self) -> None:
        super().start_listener()
        if hasattr(self, "_frame_listener") and self._frame_listener.is_alive():
            self._frame_listener.join(timeout=2.0)
        self._frame_listener = threading.Thread(target=self._frame_listen, daemon=True)
        self._frame_listener.start()
        # self._listener_running.wait(2.0)

    def close(self) -> None:
        """Close the transport-layer connection and event-loop."""
        self.finish_listener()
        self.closeEvent.set()
        try:
            if self.listener.is_alive():
                self.listener.join(timeout=2.0)
        except Exception:
            pass
        try:
            if hasattr(self, "_frame_listener") and self._frame_listener.is_alive():
                self._frame_listener.join(timeout=2.0)
        except Exception:
            pass
        self.close_connection()

    def listen(self) -> None:
        while True:
            if self.closeEvent.is_set():
                return
            frame_to_process = None
            with self._condition:
                while not self._frames:
                    res = self._condition.wait(1.0)
                    if not res:
                        break
                if self._frames:
                    frame_to_process = self._frames.popleft()

            if frame_to_process:
                frame, length, counter, timestamp = frame_to_process
                self.process_response(frame, length, counter, timestamp)

    def _frame_listen(self) -> None:
        # self._listener_running.set()
        while True:
            if self.closeEvent.is_set():
                return
            data = self.comm_port.read(1)
            if data:
                self.receiver.feed_bytes(data)
                data = self.comm_port.read(self.comm_port.in_waiting)
                if data:
                    self.receiver.feed_bytes(data)

    def frame_dispatcher(self, data: bytes, length: int, counter: int) -> None:
        with self._condition:
            self._frames.append((bytes(data), length, counter, self.timestamp.value))
            self._condition.notify()

    def send(self, frame: bytes) -> None:
        self.pre_send_timestamp = self.timestamp.value
        self.comm_port.write(frame)
        self.post_send_timestamp = self.timestamp.value

    def close_connection(self) -> None:
        if hasattr(self, "comm_port") and self.comm_port.is_open and not self.has_user_supplied_interface:
            self.comm_port.close()

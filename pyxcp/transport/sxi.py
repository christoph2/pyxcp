import enum
import struct
from collections import deque
from dataclasses import dataclass
from typing import Optional

import serial

import pyxcp.types as types
from pyxcp.transport.base import BaseTransport
from pyxcp.utils import hexDump


@dataclass
class HeaderValues:
    length: int = 0
    counter: int = 0
    filler: int = 0


class ESC(enum.IntEnum):
    ESC_ESC = 0x00
    ESC_SYNC = 0x01


RECV_SIZE = 16384


class SxI(BaseTransport):
    """"""

    def __init__(self, config=None, policy=None, transport_layer_interface: Optional[serial.Serial] = None) -> None:
        super().__init__(config, policy, transport_layer_interface)
        self.load_config(config)
        self.port_name = self.config.port
        self.baudrate = self.config.bitrate
        self.bytesize = self.config.bytesize
        self.parity = self.config.parity
        self.stopbits = self.config.stopbits
        self.mode = self.config.mode
        self.header_format = self.config.header_format
        self.tail_format = self.config.tail_format
        self.framing = self.config.framing
        self.sync = self.config.sync
        self.esc = self.config.esc
        self.make_header()
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
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )
            except serial.SerialException as e:
                self.logger.critical(f"XCPonSxI - {e}")
                raise
        self._packets = deque()

    def __del__(self) -> None:
        self.close_connection()

    def make_header(self) -> None:
        def unpack_len(args):
            (length,) = args
            return HeaderValues(length=length)

        def unpack_len_counter(args):
            length, counter = args
            return HeaderValues(length=length, counter=counter)

        def unpack_len_filler(args):
            length, filler = args
            return HeaderValues(length=length, filler=filler)

        HEADER_FORMATS = {
            "HEADER_LEN_BYTE": ("B", unpack_len),
            "HEADER_LEN_CTR_BYTE": ("BB", unpack_len_counter),
            "HEADER_LEN_FILL_BYTE": ("BB", unpack_len_filler),
            "HEADER_LEN_WORD": ("H", unpack_len),
            "HEADER_LEN_CTR_WORD": ("HH", unpack_len_counter),
            "HEADER_LEN_FILL_WORD": ("HH", unpack_len_filler),
        }
        fmt, unpacker = HEADER_FORMATS[self.header_format]
        self.HEADER = struct.Struct(f"<{fmt}")
        self.HEADER_SIZE = self.HEADER.size
        self.unpacker = unpacker

    def handle_framing(self, frame):

        if self.framing == "IMPROVED_FRAMING":

            # Replace SYNC by ESC+ESC_SYNC
            frame = b"".join(bytes([self.esc]) + bytes([ESC.ESC_SYNC]) if byte == self.sync else bytes([byte]) for byte in frame)

            # Replace ESC by ESC+ESC_ESC
            frame = b"".join(bytes([self.esc]) + bytes([ESC.ESC_ESC]) if byte == self.esc else bytes([byte]) for byte in frame)

        # Add sync char in front of each frame
        frame = bytes([self.sync]) + frame

        return frame

    def connect(self) -> None:
        self.logger.info(
            f"XCPonSxI - serial comm_port {self.comm_port.portstr!r} openend [{self.baudrate}/{self.bytesize}-{self.parity}-{self.stopbits}]"
        )
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

    def listen(self) -> None:
        while True:
            if self.closeEvent.is_set():
                return
            if not self.comm_port.in_waiting:
                continue

            recv_timestamp = self.timestamp.value

            if self.framing != "NO_FRAMING":
                sync = self.comm_port.read(1)  # first byte before a frame must always be the sync byte
                if sync != bytes([self.sync]):
                    raise types.FrameStructureError("Frame Wrong sync byte received.")

            header_values = self.unpacker(self.HEADER.unpack(self.comm_port.read(self.HEADER_SIZE)))
            length, counter, _ = header_values.length, header_values.counter, header_values.filler

            response = self.comm_port.read(length)
            self.timing.stop()

            if len(response) != length:
                raise types.FrameSizeError("Size mismatch.")
            self.process_response(response, length, counter, recv_timestamp)

    def send(self, frame) -> None:
        self.pre_send_timestamp = self.timestamp.value
        if self.framing != "NO_FRAMING":
            frame = self.handle_framing(frame)
        self.comm_port.write(frame)
        self.post_send_timestamp = self.timestamp.value
        if self._debug:
            self.logger.debug(f"XCPonSxI - Raw data -> {hexDump(frame)}")

    def close_connection(self) -> None:
        if hasattr(self, "comm_port") and self.comm_port.is_open and not self.has_user_supplied_interface:
            self.comm_port.close()

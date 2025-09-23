from collections import deque
from dataclasses import dataclass
from typing import Optional

import serial

import pyxcp.types as types
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
        tail_cs = tail_cs_map[self.config.tail_format]
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
                    timeout=self.timeout,
                    write_timeout=self.timeout,
                )
            except serial.SerialException as e:
                self.logger.critical(f"XCPonSxI - {e}")
                raise
        self._packets = deque()

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

    def listen(self) -> None:
        while True:
            if self.closeEvent.is_set():
                return
            if not self.comm_port.in_waiting:
                continue
            recv_timestamp = self.timestamp.value
            header_values = self.framing.unpack_header(self.comm_port.read(self.framing.header_size))
            if header_values is not None:
                length, counter = header_values
                # print(f"Received frame: {length} bytes, counter: {counter}")
                response = self.comm_port.read(length)
                self.timing.stop()
                if len(response) != length:
                    raise types.FrameSizeError("Size mismatch.")
                self.process_response(response, length, counter, recv_timestamp)

    def send(self, frame) -> None:
        self.pre_send_timestamp = self.timestamp.value
        self.comm_port.write(frame)
        self.post_send_timestamp = self.timestamp.value

    def close_connection(self) -> None:
        if hasattr(self, "comm_port") and self.comm_port.is_open and not self.has_user_supplied_interface:
            self.comm_port.close()

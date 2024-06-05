# -*- coding: utf-8 -*-

import struct
from collections import deque
from dataclasses import dataclass
from time import time

import serial

import pyxcp.types as types
from pyxcp.transport.base import BaseTransport


@dataclass
class HeaderValues:
    length: int = 0
    counter: int = 0
    filler: int = 0


RECV_SIZE = 16384


class SxI(BaseTransport):
    """"""

    def __init__(self, config=None, policy=None):
        super().__init__(config, policy)
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
        self.esc_sync = self.config.esc_sync
        self.esc_esc = self.config.esc_esc
        self.make_header()
        self.logger.debug(f"Trying to open serial comm_port {self.port_name}.")
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
            self.logger.critical(f"{e}")
            raise
        self._packets = deque()

    def __del__(self):
        self.closeConnection()

    def make_header(self):
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

    def connect(self):
        self.logger.info(f"Serial comm_port openend: {self.comm_port.portstr}@{self.baudrate} Bits/Sec.")
        self.startListener()

    def output(self, enable):
        if enable:
            self.comm_port.rts = False
            self.comm_port.dtr = False
        else:
            self.comm_port.rts = True
            self.comm_port.dtr = True

    def flush(self):
        self.comm_port.flush()

    def startListener(self):
        super().startListener()

    def listen(self):
        while True:
            if self.closeEvent.is_set():
                return
            if not self.comm_port.inWaiting():
                continue

            recv_timestamp = time()
            header_values = self.unpacker(self.HEADER.unpack(self.comm_port.read(self.HEADER_SIZE)))
            length, counter, _git  = header_values.length, header_values.counter, header_values.filler

            response = self.comm_port.read(length)
            self.timing.stop()

            if len(response) != length:
                raise types.FrameSizeError("Size mismatch.")
            self.processResponse(response, length, counter, recv_timestamp)

    def send(self, frame):
        self.pre_send_timestamp = time()
        self.comm_port.write(frame)
        self.post_send_timestamp = time()

    def closeConnection(self):
        if hasattr(self, "comm_port") and self.comm_port.isOpen():
            self.comm_port.close()

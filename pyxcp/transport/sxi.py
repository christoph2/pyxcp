# -*- coding: utf-8 -*-

import struct
from time import time

import serial

import pyxcp.types as types
from pyxcp.transport.base import BaseTransport


class SxI(BaseTransport):
    """"""

    MAX_DATAGRAM_SIZE = 512
    HEADER = struct.Struct("<HH")
    HEADER_SIZE = HEADER.size

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

    def __del__(self):
        self.closeConnection()

    def connect(self):
        self.logger.debug(f"Trying to open serial comm_port {self.port_name}.")
        try:
            self.comm_port = serial.Serial()
            self.comm_port.port = self.port_name
            self.comm_port.baudrate = self.baudrate
            self.comm_port.bytesize = self.bytesize
            self.comm_port.parity = self.parity
            self.comm_port.stopbits = self.stopbits
            self.comm_port.timeout = self.timeout
            self.comm_port.open()
        except serial.SerialException as e:
            self.logger.critical(f"{e}")
            raise
        self.logger.info(f"Serial comm_port openend as {self.comm_port.portstr}@{self.baudrate} Bits/Sec.")
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

    def listen(self):
        while True:
            if self.closeEvent.is_set():
                return
            if not self.comm_port.inWaiting():
                continue

            recv_timestamp = time()
            length, counter = self.HEADER.unpack(self.comm_port.read(self.HEADER_SIZE))

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

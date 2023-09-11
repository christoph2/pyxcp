#!/usr/bin/env python
# -*- coding: utf-8 -*-
import struct
from time import perf_counter
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
        super(SxI, self).__init__(config, policy)
        self.load_config(config)
        self.logger = config.log
        self.port_name = self.config.port
        self.baudrate = self.config.bitrate
        self.bytesize = self.config.bytesize
        self.parity = self.config.parity
        self.stopbits = self.config.stopbits

    def __del__(self):
        self.closeConnection()

    def connect(self):
        self.logger.debug("Trying to open serial comm_port {}.".format(self.port_name))
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
            self.logger.error("{}".format(e))
            raise
        self.logger.info("Serial comm_port openend as '{}' @ {} Bits/Sec.".format(self.comm_port.portstr, self.baudrate))
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
            if self.closeEvent.isSet():
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

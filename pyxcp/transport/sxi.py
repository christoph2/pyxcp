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

    PARAMETER_MAP = {
        #                        Type    Req'd   Default
        "PORT": (str, False, "COM1"),
        "BITRATE": (int, False, 38400),
        "BYTESIZE": (int, False, 8),
        "PARITY": (str, False, "N"),
        "STOPBITS": (int, False, 1),
    }

    MAX_DATAGRAM_SIZE = 512
    TIMEOUT = 0.75
    HEADER = struct.Struct("<HH")
    HEADER_SIZE = HEADER.size

    def __init__(self, config=None, policy=None):
        super(SxI, self).__init__(config, policy)
        self.loadConfig(config)
        self.portName = self.config.get("PORT")
        self.baudrate = self.config.get("BITRATE")

    def __del__(self):
        self.closeConnection()

    def connect(self):

        self.logger.debug("Trying to open serial commPort {}.".format(self.portName))
        try:
            self.commPort = serial.Serial(self.portName, self.baudrate, timeout=SxI.TIMEOUT)
        except serial.SerialException as e:
            self.logger.error("{}".format(e))
            raise
        self.logger.info("Serial commPort openend as '{}' @ {} Bits/Sec.".format(self.commPort.portstr, self.baudrate))
        self.startListener()

    def output(self, enable):
        if enable:
            self.commPort.rts = False
            self.commPort.dtr = False
        else:
            self.commPort.rts = True
            self.commPort.dtr = True

    def flush(self):
        self.commPort.flush()

    def listen(self):

        while True:
            if self.closeEvent.isSet():
                return
            if not self.commPort.inWaiting():
                continue

            recv_timestamp = time()
            length, counter = self.HEADER.unpack(self.commPort.read(self.HEADER_SIZE))

            response = self.commPort.read(length)
            self.timing.stop()

            if len(response) != length:
                raise types.FrameSizeError("Size mismatch.")

            self.processResponse(response, length, counter, recv_timestamp)

    def send(self, frame):
        self.pre_send_timestamp = time()
        self.commPort.write(frame)
        self.post_send_timestamp = time()

    def closeConnection(self):
        if hasattr(self, "commPort") and self.commPort.isOpen():
            self.commPort.close()

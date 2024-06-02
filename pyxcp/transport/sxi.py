# -*- coding: utf-8 -*-


import struct
import threading
from array import array
from collections import deque
from time import sleep, time

import serial

import pyxcp.types as types
from pyxcp.transport.base import BaseTransport


RECV_SIZE = 16384


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
        self.logger.debug(f"Trying to open serial comm_port {self.port_name}.")
        try:
            self.comm_port = serial.Serial(
                port=self.port_name,
                baudrate=self.baudrate,
                bytesize=self.bytesize,
                parity=self.parity,
                stopbits=self.stopbits,
                timeout=self.timeout,
            )
        except serial.SerialException as e:
            self.logger.critical(f"{e}")
            raise
        self._packet_listener = threading.Thread(
            target=self._packet_listen,
            args=(),
            kwargs={},
        )
        self._packets = deque()

    def __del__(self):
        self.closeConnection()

    def connect(self):
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

    def _packet_listen(self):
        print("PACKET-LISTEN")
        close_event_set = self.closeEvent.is_set

        _packets = self._packets
        read = self.comm_port.read

        buffer = array("B", bytes(RECV_SIZE))
        buffer_view = memoryview(buffer)

        while True:
            try:
                print("Trying...")
                if close_event_set():
                    print("close_event_set()")
                    return
                print("Enter reader...")
                recv_timestamp = time()
                sleep(0.1)
                ra = self.comm_port.read_all()
                print("*** READ-ALL", ra)
                read_count = read(buffer, 10)  # 100ms timeout
                print("RC", read_count)
                if read_count != RECV_SIZE:
                    _packets.append((buffer_view[:read_count].tobytes(), recv_timestamp))
                else:
                    _packets.append((buffer.tobytes(), recv_timestamp))
                    # except (USBError, USBTimeoutError):
                    # print(format_exc())
                    # sleep(SHORT_SLEEP)
                    continue
            except BaseException:  # noqa: B036
                # Note: catch-all only permitted if the intention is re-raising.
                self.status = 0  # disconnected
                break

    def startListener(self):
        super().startListener()
        print("*** START LISTENER ***")
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self._packet_listener = threading.Thread(target=self._packet_listen)
        self._packet_listener.start()

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
            print("\t***RESP", response)
            self.processResponse(response, length, counter, recv_timestamp)

    def send(self, frame):
        self.pre_send_timestamp = time()
        self.comm_port.write(frame)
        self.post_send_timestamp = time()

    def closeConnection(self):
        if hasattr(self, "comm_port") and self.comm_port.isOpen():
            self.comm_port.close()

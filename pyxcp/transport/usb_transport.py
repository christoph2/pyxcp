#!/usr/bin/env python
import struct
import threading
from array import array
from collections import deque
from time import perf_counter, sleep

import usb.backend.libusb0 as libusb0
import usb.backend.libusb1 as libusb1
import usb.backend.openusb as openusb
import usb.core
import usb.util
from usb.core import USBError, USBTimeoutError

from pyxcp.transport.base import BaseTransport
from pyxcp.utils import SHORT_SLEEP


RECV_SIZE = 16384


class Usb(BaseTransport):
    """"""

    HEADER = struct.Struct("<2H")
    HEADER_SIZE = HEADER.size

    def __init__(self, config=None, policy=None):
        super().__init__(config, policy)
        self.load_config(config)
        self.serial_number = self.config.serial_number
        self.vendor_id = self.config.vendor_id
        self.product_id = self.config.product_id
        self.configuration_number = self.config.configuration_number
        self.interface_number = self.config.interface_number
        self.library = self.config.library
        self.header_format = self.config.header_format

        ## IN-EP (RES/ERR, DAQ, and EV/SERV) Parameters.
        self.in_ep_number = self.config.in_ep_number
        self.in_ep_transfer_type = self.config.in_ep_transfer_type
        self.in_ep_max_packet_size = self.config.in_ep_max_packet_size
        self.in_ep_polling_interval = self.config.in_ep_polling_interval
        self.in_ep_message_packing = self.config.in_ep_message_packing
        self.in_ep_alignment = self.config.in_ep_alignment
        self.in_ep_recommended_host_bufsize = self.config.in_ep_recommended_host_bufsize

        ## OUT-EP (CMD and STIM) Parameters.
        self.out_ep_number = self.config.out_ep_number

        self.device = None
        self.status = 0

        self._packet_listener = threading.Thread(
            target=self._packet_listen,
            args=(),
            kwargs={},
        )
        self._packets = deque()

    def connect(self):
        if self.library:
            for backend_provider in (libusb1, libusb0, openusb):
                backend = backend_provider.get_backend(find_library=lambda x: self.library)
                if backend:
                    break
        else:
            backend = None
        if self.vendor_id and self.product_id:
            kwargs = {
                "find_all": True,
                "idVendor": self.vendor_id,
                "idProduct": self.product_id,
                "backend": backend,
            }
        else:
            kwargs = {
                "find_all": True,
                "backend": backend,
            }

        for device in usb.core.find(**kwargs):
            try:
                if device.serial_number.strip().strip("\0").lower() == self.serial_number.lower():
                    self.device = device
                    break
            except (USBError, USBTimeoutError):
                continue
        else:
            raise Exception(f"Device with serial {self.serial_number!r} not found")

        current_configuration = self.device.get_active_configuration()
        if current_configuration.bConfigurationValue != self.configuration_number:
            self.device.set_configuration(self.configuration_number)
        cfg = self.device.get_active_configuration()

        interface = cfg[(self.interface_number, 0)]

        self.out_ep = interface[self.out_ep_number]
        self.in_ep = interface[self.in_ep_number]

        self.startListener()
        self.status = 1  # connected

    def startListener(self):
        super().startListener()
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self._packet_listener = threading.Thread(target=self._packet_listen)
        self._packet_listener.start()

    def close(self):
        """Close the transport-layer connection and event-loop."""
        self.finishListener()
        if self.listener.is_alive():
            self.listener.join()
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self.closeConnection()

    def _packet_listen(self):
        close_event_set = self.closeEvent.is_set

        _packets = self._packets
        read = self.in_ep.read

        buffer = array("B", bytes(RECV_SIZE))
        buffer_view = memoryview(buffer)

        while True:
            try:
                if close_event_set():
                    return
                try:
                    recv_timestamp = self.timestamp.value
                    read_count = read(buffer, 100)  # 100ms timeout
                    if read_count != RECV_SIZE:
                        _packets.append((buffer_view[:read_count].tobytes(), recv_timestamp))
                    else:
                        _packets.append((buffer.tobytes(), recv_timestamp))
                except (USBError, USBTimeoutError):
                    # print(format_exc())
                    sleep(SHORT_SLEEP)
                    continue
            except BaseException:  # noqa: B036
                # Note: catch-all only permitted if the intention is re-raising.
                self.status = 0  # disconnected
                break

    def listen(self):
        HEADER_UNPACK_FROM = self.HEADER.unpack_from
        HEADER_SIZE = self.HEADER_SIZE

        popleft = self._packets.popleft

        processResponse = self.processResponse
        close_event_set = self.closeEvent.is_set

        _packets = self._packets
        length, counter = None, None

        data = bytearray(b"")

        last_sleep = perf_counter()

        while True:
            if close_event_set():
                return

            count = len(_packets)

            if not count:
                sleep(SHORT_SLEEP)
                last_sleep = perf_counter()
                continue

            for _ in range(count):
                bts, timestamp = popleft()

                data += bts
                current_size = len(data)
                current_position = 0

                while True:
                    if perf_counter() - last_sleep >= 0.005:
                        sleep(SHORT_SLEEP)
                        last_sleep = perf_counter()

                    if length is None:
                        if current_size >= HEADER_SIZE:
                            length, counter = HEADER_UNPACK_FROM(data, current_position)
                            current_position += HEADER_SIZE
                            current_size -= HEADER_SIZE
                        else:
                            data = data[current_position:]
                            break
                    else:
                        if current_size >= length:
                            response = data[current_position : current_position + length]
                            processResponse(response, length, counter, timestamp)

                            current_size -= length
                            current_position += length

                            length = None

                        else:
                            data = data[current_position:]
                            break

    def send(self, frame):
        self.pre_send_timestamp = self.timestamp.value
        try:
            self.out_ep.write(frame)
        except (USBError, USBTimeoutError):
            # sometimes usb.core.USBError: [Errno 5] Input/Output Error is raised
            # even though the command is send and a reply is received from the device.
            # Ignore this here since a Timeout error will be raised anyway if
            # the device does not respond
            pass
        self.post_send_timestamp = self.timestamp.value

    def closeConnection(self):
        if self.device is not None:
            usb.util.dispose_resources(self.device)

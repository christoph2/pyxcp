#!/usr/bin/env python
import struct
import threading
from array import array
from collections import deque
from typing import Optional

import usb.backend.libusb0 as libusb0
import usb.backend.libusb1 as libusb1
import usb.backend.openusb as openusb
import usb.core
import usb.util
from usb.core import USBError, USBTimeoutError

from pyxcp.transport.base import BaseTransport
from pyxcp.utils import short_sleep


RECV_SIZE = 16384
FIVE_MS = 5_000_000  # Five milliseconds in nanoseconds.


class Usb(BaseTransport):
    """"""

    HEADER = struct.Struct("<2H")
    HEADER_SIZE = HEADER.size

    def __init__(self, config=None, policy=None, transport_layer_interface: Optional[usb.core.Device] = None):
        super().__init__(config, policy, transport_layer_interface)
        self.load_config(config)
        self.serial_number: str = self.config.serial_number
        self.vendor_id: int = self.config.vendor_id
        self.product_id: int = self.config.product_id
        self.configuration_number: int = self.config.configuration_number
        self.interface_number: int = self.config.interface_number
        self.library: str = self.config.library
        self.header_format: str = self.config.header_format
        self.library = self.config.get("library")
        self.device = None

        ## IN-EP (RES/ERR, DAQ, and EV/SERV) Parameters.
        self.in_ep_number: int = self.config.in_ep_number
        self.in_ep_transfer_type = self.config.in_ep_transfer_type
        self.in_ep_max_packet_size: int = self.config.in_ep_max_packet_size
        self.in_ep_polling_interval: int = self.config.in_ep_polling_interval
        self.in_ep_message_packing = self.config.in_ep_message_packing
        self.in_ep_alignment = self.config.in_ep_alignment
        self.in_ep_recommended_host_bufsize: int = self.config.in_ep_recommended_host_bufsize

        ## OUT-EP (CMD and STIM) Parameters.
        self.out_ep_number: int = self.config.out_ep_number

        self.device: Optional[usb.core.Device] = None
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
            raise Exception(f"XCPonUSB - device with serial {self.serial_number!r} not found")

        current_configuration = self.device.get_active_configuration()
        if current_configuration.bConfigurationValue != self.configuration_number:
            self.device.set_configuration(self.configuration_number)
        cfg = self.device.get_active_configuration()

        interface = cfg[(self.interface_number, 0)]

        self.out_ep = interface[self.out_ep_number]
        self.in_ep = interface[self.in_ep_number]

        self.start_listener()
        self.status = 1  # connected

    def start_listener(self):
        super().start_listener()
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self._packet_listener = threading.Thread(target=self._packet_listen)
        self._packet_listener.start()

    def close(self):
        """Close the transport-layer connection and event-loop."""
        self.finish_listener()
        if self.listener.is_alive():
            self.listener.join()
        if self._packet_listener.is_alive():
            self._packet_listener.join()
        self.close_connection()

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
                    short_sleep()
                    continue
            except BaseException:  # noqa: B036
                # Note: catch-all only permitted if the intention is re-raising.
                self.status = 0  # disconnected
                break

    def listen(self):
        HEADER_UNPACK_FROM = self.HEADER.unpack_from
        HEADER_SIZE = self.HEADER_SIZE
        popleft = self._packets.popleft
        process_response = self.process_response
        close_event_set = self.closeEvent.is_set
        _packets = self._packets
        length: Optional[int] = None
        counter: int = 0
        data: bytearray = bytearray(b"")
        last_sleep: int = self.timestamp.value

        while True:
            if close_event_set():
                return
            count: int = len(_packets)
            if not count:
                short_sleep()
                last_sleep = self.timestamp.value
                continue
            for _ in range(count):
                bts, timestamp = popleft()
                data += bts
                current_size: int = len(data)
                current_position: int = 0
                while True:
                    if self.timestamp.value - last_sleep >= FIVE_MS:
                        short_sleep()
                        last_sleep = self.timestamp.value
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
                            process_response(response, length, counter, timestamp)
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

    def close_connection(self):
        if self.device is not None:
            usb.util.dispose_resources(self.device)

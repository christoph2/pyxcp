import struct
from collections import deque
from dataclasses import dataclass
from typing import Optional

import serial

import pyxcp.types as types
from pyxcp.transport.base import BaseTransport
from pyxcp.utils import short_sleep


@dataclass
class HeaderValues:
    length: int = 0
    counter: int = 0
    filler: int = 0


RECV_SIZE = 16384
FIVE_MS = 5_000_000  # Five milliseconds in nanoseconds


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
        self.esc_sync = self.config.esc_sync
        self.esc_esc = self.config.esc_esc
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
        """Process data received from the serial port.

        This method runs in a separate thread and continuously polls the serial port
        for new data. When data is available, it:

        1. Reads the header to get the length and counter
        2. Reads the payload based on the length
        3. Passes the payload to process_response

        The method includes periodic sleep to prevent CPU hogging and error handling
        to ensure the listener thread doesn't crash on exceptions.
        """
        # Cache frequently used methods and attributes for better performance
        close_event_set = self.closeEvent.is_set
        process_response = self.process_response
        comm_port_in_waiting = self.comm_port.in_waiting
        comm_port_read = self.comm_port.read
        header_unpacker = self.unpacker
        header_unpack = self.HEADER.unpack
        header_size = self.HEADER_SIZE

        # State variables for processing
        last_sleep = self.timestamp.value

        while True:
            # Check if we should exit the loop
            if close_event_set():
                return

            # Periodically sleep to prevent CPU hogging
            if self.timestamp.value - last_sleep >= FIVE_MS:
                short_sleep()
                last_sleep = self.timestamp.value

            # Check if there is data available to read
            if not comm_port_in_waiting():
                short_sleep()
                last_sleep = self.timestamp.value
                continue

            try:
                # Read and process the data
                recv_timestamp = self.timestamp.value

                # Read and unpack the header
                header_values = header_unpacker(header_unpack(comm_port_read(header_size)))
                length, counter, _ = header_values.length, header_values.counter, header_values.filler

                # Read the payload
                response = comm_port_read(length)
                self.timing.stop()

                # Verify the response length
                if len(response) != length:
                    self.logger.error(f"Frame size mismatch: expected {length}, got {len(response)}")
                    raise types.FrameSizeError("Size mismatch.")

                # Process the response
                process_response(response, length, counter, recv_timestamp)
            except types.FrameSizeError:
                # Re-raise FrameSizeError as it's a critical error
                raise
            except Exception as e:
                # Log any other exceptions but continue processing
                self.logger.error(f"Error in SxI listen thread: {e}")
                # Sleep briefly to avoid tight error loops
                short_sleep()
                last_sleep = self.timestamp.value

    def send(self, frame) -> None:
        self.pre_send_timestamp = self.timestamp.value
        self.comm_port.write(frame)
        self.post_send_timestamp = self.timestamp.value

    def close_connection(self) -> None:
        if hasattr(self, "comm_port") and self.comm_port.is_open and not self.has_user_supplied_interface:
            self.comm_port.close()

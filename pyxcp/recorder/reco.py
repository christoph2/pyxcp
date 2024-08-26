#!/usr/bin/env python
"""Raw XCP traffic recorder.

Data is stored in LZ4 compressed containers.

Examples
--------

See

- ``_ for recording / writing

-  ``_ for reading.
"""
import enum
import mmap
import struct
from collections import namedtuple

import lz4.block as lz4block


FILE_EXTENSION = ".xmraw"  # XCP Measurement / raw data.

MAGIC = b"ASAMINT::XCP_RAW"

FILE_HEADER_STRUCT = struct.Struct(f"<{len(MAGIC):d}sHHHLLLL")
FileHeader = namedtuple(
    "FileHeader",
    "magic hdr_size version options num_containers record_count size_compressed size_uncompressed",
)

CONTAINER_HEADER_STRUCT = struct.Struct("<LLL")
ContainerHeader = namedtuple("ContainerHeader", "record_count size_compressed size_uncompressed")

DAQ_RECORD_STRUCT = struct.Struct("<BHdL")
DAQRecord = namedtuple("DAQRecord", "category counter timestamp payload")


class XcpLogCategory(enum.IntEnum):
    """ """

    DAQ = 1


class XcpLogFileParseError(Exception):
    """Log file is damaged is some way."""

    pass


class XcpLogFileCapacityExceededError(Exception):
    pass


class XcpLogFileWriter:
    """
    Parameters
    ----------
    file_name: str
        Don't specify extension.

    prealloc: int
        Pre-allocate a sparse file (size in MB).

    chunk_size: int
        Number of kilobytes to collect before compressing.

    compression_level: int
        s. LZ4 documentation.
    """

    def __init__(
        self,
        file_name: str,
        prealloc: int = 10,
        chunk_size: int = 1024,
        compression_level: int = 9,
    ):
        self._is_closed = True
        try:
            self._of = open(f"{file_name}{FILE_EXTENSION}", "w+b")
        except Exception:
            raise
        else:
            self._of.truncate(1024 * 1024 * prealloc)  # Create sparse file (hopefully).
            self._mapping = mmap.mmap(self._of.fileno(), 0)
        self.container_header_offset = FILE_HEADER_STRUCT.size
        self.current_offset = self.container_header_offset + CONTAINER_HEADER_STRUCT.size
        self.total_size_uncompressed = self.total_size_compressed = 0
        self.container_size_uncompressed = self.container_size_compressed = 0
        self.total_record_count = 0
        self.chunk_size = chunk_size * 1024
        self.num_containers = 0
        self.intermediate_storage = []
        self.compression_level = compression_level
        self.prealloc = prealloc
        self._is_closed = False

    def add_xcp_frames(self, xcp_frames: list):
        for counter, timestamp, raw_data in xcp_frames:
            length = len(raw_data)
            item = DAQ_RECORD_STRUCT.pack(1, counter, timestamp, length) + raw_data
            self.intermediate_storage.append(item)
            self.container_size_uncompressed += len(item)
            if self.container_size_uncompressed > self.chunk_size:
                self._compress_framez()

    def _compress_framez(self):
        compressed_data = lz4block.compress(b"".join(self.intermediate_storage), compression=self.compression_level)
        record_count = len(self.intermediate_storage)
        hdr = CONTAINER_HEADER_STRUCT.pack(record_count, len(compressed_data), self.container_size_uncompressed)
        self.set(self.current_offset, compressed_data)
        self.set(self.container_header_offset, hdr)
        self.container_header_offset = self.current_offset + len(compressed_data)
        self.current_offset = self.container_header_offset + CONTAINER_HEADER_STRUCT.size
        self.intermediate_storage = []
        self.total_record_count += record_count
        self.num_containers += 1
        self.total_size_uncompressed += self.container_size_uncompressed
        self.total_size_compressed += len(compressed_data)
        self.container_size_uncompressed = 0
        self.container_size_compressed = 0

    def __del__(self):
        if not self._is_closed:
            self.close()

    def close(self):
        if not self._is_closed:
            if hasattr(self, "_mapping"):
                if self.intermediate_storage:
                    self._compress_framez()
                self._write_header(
                    version=0x0100,
                    options=0x0000,
                    num_containers=self.num_containers,
                    record_count=self.total_record_count,
                    size_compressed=self.total_size_compressed,
                    size_uncompressed=self.total_size_uncompressed,
                )
                self._mapping.flush()
                self._mapping.close()
                self._of.truncate(self.current_offset)
            self._of.close()
            self._is_closed = True

    def set(self, address: int, data: bytes):
        """Write to memory mapped file.

        Parameters
        ----------
        address: int

        data: bytes-like
        """
        length = len(data)
        try:
            self._mapping[address : address + length] = data
        except IndexError:
            raise XcpLogFileCapacityExceededError(f"Maximum file size of {self.prealloc} MBytes exceeded.") from None

    def _write_header(
        self,
        version,
        options,
        num_containers,
        record_count,
        size_compressed,
        size_uncompressed,
    ):
        hdr = FILE_HEADER_STRUCT.pack(
            MAGIC,
            FILE_HEADER_STRUCT.size,
            version,
            options,
            num_containers,
            record_count,
            size_compressed,
            size_uncompressed,
        )
        self.set(0x00000000, hdr)

    @property
    def compression_ratio(self):
        if self.total_size_compressed:
            return self.total_size_uncompressed / self.total_size_compressed


class XcpLogFileReader:
    """
    Parameters
    ----------
    file_name: str
        Don't specify extension.
    """

    def __init__(self, file_name):
        self._is_closed = True
        try:
            self._log_file = open(f"{file_name}{FILE_EXTENSION}", "r+b")
        except Exception:
            raise
        else:
            self._mapping = mmap.mmap(self._log_file.fileno(), 0)
        self._is_closed = False
        (
            magic,
            _,
            _,
            _,
            self.num_containers,
            self.total_record_count,
            self.total_size_compressed,
            self.total_size_uncompressed,
        ) = FILE_HEADER_STRUCT.unpack(self.get(0, FILE_HEADER_STRUCT.size))
        if magic != MAGIC:
            raise XcpLogFileParseError(f"Invalid file magic: {magic!r}.")

    def __del__(self):
        if not self._is_closed:
            self.close()

    @property
    def frames(self):
        """Iterate over all frames in file.

        Yields
        ------
        DAQRecord
        """
        offset = FILE_HEADER_STRUCT.size
        for _ in range(self.num_containers):
            (
                record_count,
                size_compressed,
                size_uncompressed,
            ) = CONTAINER_HEADER_STRUCT.unpack(self.get(offset, CONTAINER_HEADER_STRUCT.size))
            offset += CONTAINER_HEADER_STRUCT.size
            uncompressed_data = memoryview(lz4block.decompress(self.get(offset, size_compressed)))
            frame_offset = 0
            for _ in range(record_count):
                category, counter, timestamp, frame_length = DAQ_RECORD_STRUCT.unpack(
                    uncompressed_data[frame_offset : frame_offset + DAQ_RECORD_STRUCT.size]
                )
                frame_offset += DAQ_RECORD_STRUCT.size
                frame_data = uncompressed_data[frame_offset : frame_offset + frame_length]  # .tobytes()
                frame_offset += len(frame_data)
                frame = DAQRecord(category, counter, timestamp, frame_data)
                yield frame
            offset += size_compressed

    def get(self, address: int, length: int):
        """Read from memory mapped file.

        Parameters
        ----------
        address: int

        length: int

        Returns
        -------
        memoryview
        """
        return self._mapping[address : address + length]

    def close(self):
        if hasattr(self, "self._mapping"):
            self._mapping.close()
        self._log_file.close()
        self._is_closed = True

    @property
    def compression_ratio(self):
        if self.total_size_compressed:
            return self.total_size_uncompressed / self.total_size_compressed

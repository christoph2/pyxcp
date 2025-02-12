#!/usr/bin/env python
"""XCP Frame Recording Facility.
"""

from dataclasses import dataclass
from typing import Union

from pyxcp.types import FrameCategory


try:
    import pandas as pd
except ImportError:
    HAS_PANDAS = False
else:
    HAS_PANDAS = True

from pyxcp.recorder.rekorder import DaqOnlinePolicy  # noqa: F401
from pyxcp.recorder.rekorder import (
    DaqRecorderPolicy,      # noqa: F401
    Deserializer,           # noqa: F401
    MeasurementParameters,  # noqa: F401
    ValueHolder,            # noqa: F401
)
from pyxcp.recorder.rekorder import XcpLogFileDecoder as _XcpLogFileDecoder
from pyxcp.recorder.rekorder import _PyXcpLogFileReader, _PyXcpLogFileWriter, data_types


DATA_TYPES = data_types()


@dataclass
class XcpLogFileHeader:
    """ """

    version: int
    options: int
    num_containers: int
    record_count: int
    size_uncompressed: int
    size_compressed: int
    compression_ratio: float


COUNTER_MAX = 0xFFFF


class XcpLogFileReader:
    """ """

    def __init__(self, file_name):
        self._reader = _PyXcpLogFileReader(file_name)

    @property
    def header(self):
        return self._reader.get_header()

    def get_header(self):
        return XcpLogFileHeader(*self._reader.get_header_as_tuple())

    def get_metadata(self):
        return self._reader.get_metadata()

    def __iter__(self):
        while True:
            frames = self._reader.next_block()
            if frames is None:
                break
            for category, counter, timestamp, _, payload in frames:
                yield (FrameCategory(category), counter, timestamp, payload)

    def reset_iter(self):
        self._reader.reset()

    def as_dataframe(self):
        if HAS_PANDAS:
            df = pd.DataFrame((f for f in self), columns=["category", "counter", "timestamp", "payload"])
            df = df.set_index("timestamp")
            df.counter = df.counter.astype("uint16")
            df.category = df.category.map({v: k for k, v in FrameCategory.__members__.items()}).astype("category")
            return df
        else:
            raise NotImplementedError("method as_dataframe() requires 'pandas' package")


class XcpLogFileWriter:
    """ """

    def __init__(self, file_name: str, prealloc=500, chunk_size=1):
        self._writer = _PyXcpLogFileWriter(file_name, prealloc, chunk_size)
        self._finalized = False

    def __del__(self):
        if not self._finalized:
            self.finalize()

    def add_frame(self, category: FrameCategory, counter: int, timestamp: float, payload: Union[bytes, bytearray]):
        self._writer.add_frame(category, counter % (COUNTER_MAX + 1), timestamp, len(payload), payload)

    def finalize(self):
        self._writer.finalize()

from collections import namedtuple
from enum import IntEnum
from time import perf_counter

import rekorder as rec

XcpLogFileHeader = namedtuple(
    "XcpLogFileHeader",
    "num_containers record_count size_uncompressed size_compressed compression_ratio",
)


class FrameCategory(IntEnum):
    """ """

    META = 0
    CMD = 1
    RES = 2
    ERR = 3
    EV = 4
    SERV = 5
    DAQ = 6
    STIM = 7


class XcpLogFileReader:
    """ """

    def __init__(self, file_name):
        self._reader = rec._PyXcpLogFileReader(file_name)

    def get_header(self):
        return XcpLogFileHeader(*self._reader.get_header())

    def reset_iter(self):
        self._reader.reset()

    def __iter__(self):
        while True:
            frames = self._reader.next()
            if frames is None:
                break
            for category, counter, timestamp, length, payload in frames:
                yield (category, counter, timestamp, payload)


class XcpLogFileWriter:
    """ """

    def __init__(self, file_name):
        self._writer = rec._PyXcpLogFileWriter(file_name)

    def add_frame(self, category: int, counter: int, timestamp: float, payload: bytes):
        self._writer.add_frame(category, counter, timestamp, len(payload), payload)

    def finalize(self):
        self._writer.finalize()


writer = XcpLogFileWriter("test_logger")
for idx in range(255):
    writer.add_frame(1, idx, perf_counter(), [idx] * idx)
writer.finalize()
del writer

print("Before c-tor()")
reader = XcpLogFileReader("test_logger")
print("After c-tor()")
hdr = reader.get_header()
print(hdr)

for frame in reader:
    # print(frame)
    pass

print("Finished.")

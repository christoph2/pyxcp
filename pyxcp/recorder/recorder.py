from collections import namedtuple
from enum import IntEnum

import rekorder as rec

XcpLogFileHeader = namedtuple(
    "XcpLogFileHeader",
    "record_count size_uncompressed size_compressed compression_ratio",
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
        self._reader = rec._XcpLogFileReader(file_name)

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
        self._writer = rec._XcpLogFileWriter(file_name)


print("Before c-tor()")
reader = XcpLogFileReader("test_logger")
print("After c-tor()")
hdr = reader.get_header()
print(hdr)

for frame in reader:
    # print(frame)
    pass

print("Finished.")

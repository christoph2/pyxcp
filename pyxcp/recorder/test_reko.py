import reco
import struct
import time
from functools import partial
from random import choice
from random import randint

CNT = 1024 * 10 * 5

ri = partial(randint, 0, 255)

rs = [ri() for _ in range(CNT)]

# print(dir(time))
TS_STRUCT = struct.Struct("<Hd")

frames = []
for counter in range(CNT):
    ts = time.perf_counter()
    length = choice(rs)
    db = bytes([choice(rs)] * length)

    FS = "<H{}s".format(length)
    frame = struct.Struct(FS).pack(length, db)
    # print(length, db)
    # frame = TS_STRUCT.pack(
    #   counter, ts
    # )
    frames.append([counter, ts, frame])

# help(bytes)
DAQ_RECORD_STRUCT = struct.Struct("<BHdL")
# DAQRecord = namedtuple("DAQRecord", "category counter timestamp payload")

log = reco.XcpLogFileWriter("test_logger")

print(log)
log.add_xcp_frames(frames)

"""
def wockser(self, catagory, *args):
        response, counter, length, timestamp = args
        #print(catagory, response, counter, length, timestamp)   # .tobytes()
        raw_data = response.tobytes()
        self.intermediate_storage.append((counter, timestamp, raw_data, ))
        #li = DAQ_RECORD_STRUCT.pack(1, counter, timestamp, length)
        self.uncompressed_size += len(raw_data) + 12
        if self.uncompressed_size > 10 * 1024:
            #print("PUSH to worker!!")
            self.log_writer.add_xcp_frames(self.intermediate_storage)
            self.intermediate_storage = []
            self.uncompressed_size = 0

"""

from time import perf_counter

import pandas as pd

from pyxcp.recorder import FrameCategory
from pyxcp.recorder import XcpLogFileReader
from pyxcp.recorder import XcpLogFileWriter

writer = XcpLogFileWriter("test_logger", p=220)
# for idx in range(255):
for idx in range(512 * 1024):
    value = idx % 256
    writer.add_frame(1, idx, perf_counter(), [value] * value)
writer.finalize()
del writer
# """

print("Before c-tor()")
reader = XcpLogFileReader("test_logger")
print("After c-tor()")
hdr = reader.get_header()
print(hdr)

cnt = 0

df = pd.DataFrame((f for f in reader), columns=["category", "counter", "timestamp", "payload"])
df = df.set_index("timestamp")
df.category = df.category.map({v: k for k, v in FrameCategory.__members__.items()}).astype("category")
print(df)
print(df.info())
print(df.describe())

# for frame in reader:
#    print(frame)
#    cnt += 1

print("Finished.")

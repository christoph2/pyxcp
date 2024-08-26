from time import perf_counter

from pyxcp.recorder import FrameCategory, XcpLogFileReader, XcpLogFileWriter


# Pre-allocate a 100MB file -- Note: due to the nature of memory-mapped files, this is a HARD limit.
# Chunk size is 1MB (i.e. compression granularity).
writer = XcpLogFileWriter("test_logger", prealloc=100, chunk_size=1)

# Write some records.
start_time = perf_counter()
for idx in range(512 * 1024):
    value = idx % 256
    writer.add_frame(FrameCategory.CMD, idx, perf_counter() - start_time, bytes([value] * value))
writer.finalize()  # We're done.


reader = XcpLogFileReader("test_logger")
hdr = reader.get_header()  # Get file information.
print(hdr)

df = reader.as_dataframe()  # Return recordings as Pandas DataFrame.
print(df.info())
print(df.describe())
print(df)

reader.reset_iter()  # Non-standard method to restart iteration.

idx = 0
# Iterate over frames/records.
for _frame in reader:
    idx += 1
print("---")
print(f"Iterated over {idx} frames")

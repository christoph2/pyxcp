#!/usr/bin/env python
"""Demostrates how to use frame recording policies including recorder extension.
"""
from pprint import pprint

from pyxcp.cmdline import ArgumentParser
from pyxcp.transport.base import FrameRecorderPolicy, StdoutPolicy  # noqa: F401


ap = ArgumentParser(description="pyXCP frame recording policy example.")

LOG_FILE = "pyxcp"

policy = FrameRecorderPolicy(LOG_FILE)
use_recorder = True

# policy = StdoutPolicy()  # You may also try this one.
# use_recorder = False

with ap.run(policy=policy) as x:
    x.connect()
    if x.slaveProperties.optionalCommMode:
        x.getCommModeInfo()
    identifier = x.identifier(0x01)
    print("\nSlave Properties:")
    print("=================")
    print(f"ID: {identifier!r}")
    pprint(x.slaveProperties)
    x.disconnect()

if use_recorder:
    from pyxcp.recorder import XcpLogFileReader
    from pyxcp.utils import hexDump

    try:
        import pandas  # noqa: F401
    except ImportError:
        has_pandas = False
    else:
        has_pandas = True

    reader = XcpLogFileReader(LOG_FILE)
    hdr = reader.get_header()  # Get file information.
    print("\nRecording file header")
    print("=====================\n")
    print(hdr)
    print("\nRecorded frames")
    print("===============\n")
    print("CAT         CTR  TS             PAYLOAD")
    print("-" * 80)
    for category, counter, timestamp, payload in reader:
        print(f"{category.name:8} {counter:6}  {timestamp:7.7f} {hexDump(payload)}")
    print("-" * 80)
    reader.reset_iter()  # reader acts as an Python iterator -- can be reseted with this non-standard method.
    if has_pandas:
        print("\nRecordings as Pandas stuff")
        print("==========================\n")
        df = reader.as_dataframe()  # Return recordings as Pandas DataFrame.
        print(df.info())
        print(df.head(60))

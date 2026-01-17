#!/usr/bin/env python
# -*- coding: utf-8 -*-

import argparse
import sys
import time

from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqRecorder, DaqToCsv, load_daq_lists_from_json  # noqa: F401
from pyxcp.types import XcpTimeoutError

parser = argparse.ArgumentParser(description="XCP DAQ list recorder")
parser.add_argument(
    "DAQ_configuration_file",
    type=str,
    default=None,
)

ap = ArgumentParser(description="XCP DAQ list recorder", user_parser=parser)

args = ap.args
DAQ_LISTS = load_daq_lists_from_json(args.DAQ_configuration_file)

# daq_parser = DaqToCsv(DAQ_LISTS)  # Record to CSV file(s).
daq_parser = DaqRecorder(DAQ_LISTS, "run_daq_21092025_01", 8)  # Record to ".xmraw" file.

with ap.run(policy=daq_parser) as x:
    try:
        x.connect()
    except XcpTimeoutError:
        sys.exit(2)

    if x.slaveProperties.optionalCommMode:
        x.getCommModeInfo()

    x.cond_unlock("DAQ")  # DAQ resource is locked in many cases.

    print("setup DAQ lists.")
    daq_parser.setup()  # Execute setup procedures.
    print("start DAQ lists.")
    daq_parser.start()  # Start DAQ lists.

    time.sleep(0.25 * 60.0 * 60.0)  # Run for 15 minutes.

    print("Stop DAQ....")
    daq_parser.stop()  # Stop DAQ lists.
    print("finalize DAQ lists.\n")
    x.disconnect()

if hasattr(daq_parser, "files"):  # `files` attribute is specific to `DaqToCsv`.
    print("Data written to:")
    print("================")
    for fl in daq_parser.files.values():
        print(fl.name)

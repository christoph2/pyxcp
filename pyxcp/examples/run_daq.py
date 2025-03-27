#!/usr/bin/env python

import sys
import time

from pyxcp.cmdline import ArgumentParser
from pyxcp.daq_stim import DaqList, DaqRecorder, DaqToCsv  # noqa: F401
from pyxcp.types import XcpTimeoutError


ap = ArgumentParser(description="DAQ test")

XCP_LITE = False

#
# NOTE: UPDATE TO CORRECT ADDRESSES BEFORE RUNNING!!!
#
if XCP_LITE:
    # Vectorgrp XCPlite.
    DAQ_LISTS = [
        DaqList(
            name="part_1",
            event_num=0,
            stim=False,
            enable_timestamps=False,
            measurements=[
                ("byteCounter", 0x00023648, 0, "U8"),
                ("wordCounter", 0x0002364C, 0, "U16"),
                ("dwordCounter", 0x00023650, 0, "U32"),
                ("sbyteCounter", 0x00023649, 0, "I8"),
            ],
            priority=0,
            prescaler=1,
        ),
        DaqList(
            name="part_2",
            event_num=7,
            stim=False,
            enable_timestamps=False,
            measurements=[
                ("swordCounter", 0x00023654, 0, "I16"),
                ("sdwordCounter", 0x00023658, 0, "I32"),
                ("channel1", 0x00023630, 0, "F64"),
                ("channel2", 0x00023638, 0, "F64"),
                ("channel3", 0x00023640, 0, "F64"),
            ],
            priority=0,
            prescaler=1,
        ),
    ]
else:
    # XCPsim from CANape.
    DAQ_LISTS = [
        DaqList(
            name="pwm_stuff",
            event_num=2,
            stim=False,
            enable_timestamps=True,
            measurements=[
                ("channel1", 0x1BD004, 0, "F32"),
                ("period", 0x001C0028, 0, "F32"),
                ("channel2", 0x1BD008, 0, "F32"),
                ("PWMFiltered", 0x1BDDE2, 0, "U8"),
                ("PWM", 0x1BDDDF, 0, "U8"),
                ("Triangle", 0x1BDDDE, 0, "I8"),
            ],
            priority=0,
            prescaler=1,
        ),
        DaqList(
            name="bytes",
            event_num=1,
            stim=False,
            enable_timestamps=True,
            measurements=[
                ("TestByte_000", 0x1BE11C, 0, "U8"),
                ("TestByte_015", 0x1BE158, 0, "U8"),
                ("TestByte_016", 0x1BE15C, 0, "U8"),
                ("TestByte_023", 0x1BE178, 0, "U8"),
                ("TestByte_024", 0x1BE17C, 0, "U8"),
                ("TestByte_034", 0x1BE1A4, 0, "U8"),
                ("TestByte_059", 0x1BE208, 0, "U8"),
                ("TestByte_061", 0x1BE210, 0, "U8"),
                ("TestByte_063", 0x1BE218, 0, "U8"),
                ("TestByte_064", 0x1BE21C, 0, "U8"),
                ("TestByte_097", 0x1BE2A0, 0, "U8"),
                ("TestByte_107", 0x1BE2C8, 0, "U8"),
                ("TestByte_131", 0x1BE328, 0, "U8"),
                ("TestByte_156", 0x1BE38C, 0, "U8"),
                ("TestByte_159", 0x1BE398, 0, "U8"),
                ("TestByte_182", 0x1BE3F4, 0, "U8"),
                ("TestByte_183", 0x1BE3F8, 0, "U8"),
                ("TestByte_189", 0x1BE410, 0, "U8"),
                ("TestByte_195", 0x1BE428, 0, "U8"),
                ("TestByte_216", 0x1BE47C, 0, "U8"),
                ("TestByte_218", 0x1BE484, 0, "U8"),
                ("TestByte_221", 0x1BE490, 0, "U8"),
                ("TestByte_251", 0x1BE508, 0, "U8"),
                ("TestByte_263", 0x1BE538, 0, "U8"),
                ("TestByte_276", 0x1BE56C, 0, "U8"),
                ("TestByte_277", 0x1BE570, 0, "U8"),
                ("TestByte_297", 0x1BE5C0, 0, "U8"),
                ("TestByte_302", 0x1BE5D4, 0, "U8"),
                ("TestByte_324", 0x1BE62C, 0, "U8"),
                ("TestByte_344", 0x1BE67C, 0, "U8"),
                ("TestByte_346", 0x1BE684, 0, "U8"),
            ],
            priority=0,
            prescaler=1,
        ),
        DaqList(
            name="words",
            event_num=3,
            stim=False,
            enable_timestamps=True,
            measurements=[
                ("TestWord_001", 0x1BE120, 0, "U16"),
                ("TestWord_003", 0x1BE128, 0, "U16"),
                ("TestWord_004", 0x1BE12C, 0, "U16"),
                ("TestWord_005", 0x1BE134, 0, "U16"),
                ("TestWord_006", 0x1BE134, 0, "U16"),
                ("TestWord_007", 0x1BE138, 0, "U16"),
                ("TestWord_008", 0x1BE13C, 0, "U16"),
                ("TestWord_009", 0x1BE140, 0, "U16"),
                ("TestWord_011", 0x1BE148, 0, "U16"),
            ],
            priority=0,
            prescaler=1,
        ),
    ]

daq_parser = DaqToCsv(DAQ_LISTS)  # Record to CSV file(s).
# daq_parser = DaqRecorder(DAQ_LISTS, "run_daq", 2)  # Record to ".xmraw" file.

with ap.run(policy=daq_parser) as x:
    try:
        x.connect()
    except XcpTimeoutError:
        print("TO")
        sys.exit(2)

    if x.slaveProperties.optionalCommMode:
        x.getCommModeInfo()

    x.cond_unlock("DAQ")  # DAQ resource is locked in many cases.

    print("setup DAQ lists.")
    daq_parser.setup()  # Execute setup procedures.
    print("start DAQ lists.")
    daq_parser.start()  # Start DAQ lists.

    time.sleep(5.0 * 60.0)  # Run for 15 minutes.

    print("Stop DAQ....")
    daq_parser.stop()  # Stop DAQ lists.
    print("finalize DAQ lists.\n")
    x.disconnect()

if hasattr(daq_parser, "files"):  # `files` attribute is specific to `DaqToCsv`.
    print("Data written to:")
    print("================")
    for fl in daq_parser.files.values():
        print(fl.name)

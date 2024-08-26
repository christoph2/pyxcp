#!/usr/bin/env python
"""Very basic hello-world example.
"""
from pprint import pprint

from pyxcp.cmdline import ArgumentParser
from pyxcp.utils import decode_bytes


daq_info = False


def callout(master, args):
    global daq_info
    if args.daq_info:
        daq_info = True


ap = ArgumentParser(description="pyXCP hello world.", callout=callout)
ap.parser.add_argument(
    "-d",
    "--daq-info",
    dest="daq_info",
    help="Display DAQ-info",
    default=False,
    action="store_true",
)

with ap.run() as x:
    x.connect()
    if x.slaveProperties.optionalCommMode:
        x.getCommModeInfo()
    identifier = x.identifier(0x01)
    print("\nSlave Properties:")
    print("=================")
    print(f"ID: {identifier!r}")
    pprint(x.slaveProperties)
    x.cond_unlock()
    cps = x.getCurrentProtectionStatus()
    print("\nProtection Status")
    print("=================")
    for k, v in cps.items():
        print(f"    {k:6s}: {v}")
    daq = x.getDaqInfo()
    pprint(daq)
    if daq_info:
        dqp = x.getDaqProcessorInfo()
        print("\nDAQ Processor Info:")
        print("===================")
        print(dqp)
        print("\nDAQ Events:")
        print("===========")
        for idx in range(dqp.maxEventChannel):
            evt = x.getDaqEventInfo(idx)
            length = evt.eventChannelNameLength
            name = decode_bytes(x.pull(length))
            dq = "DAQ" if evt.daqEventProperties.daq else ""
            st = "STIM" if evt.daqEventProperties.stim else ""
            dq_st = dq + " " + st
            print(f"    [{idx:04}] {name:r}")
            print(f"        dir:            {dq_st}")
            print(f"        packed:         {evt.daqEventProperties.packed}")
            PFX_CONS = "CONSISTENCY_"
            print(f"        consistency:    {evt.daqEventProperties.consistency.strip(PFX_CONS)}")
            print(f"        max. DAQ lists: {evt.maxDaqList}")
            PFX_TU = "EVENT_CHANNEL_TIME_UNIT_"
            print(f"        unit:           {evt.eventChannelTimeUnit.strip(PFX_TU)}")
            print(f"        cycle:          {evt.eventChannelTimeCycle or 'SPORADIC'}")
            print(f"        priority        {evt.eventChannelPriority}")

        dqr = x.getDaqResolutionInfo()
        print("\nDAQ Resolution Info:")
        print("====================")
        print(dqr)
        for idx in range(dqp.maxDaq):
            print(f"\nDAQ List Info #{idx}")
            print("=================")
            print(f"{x.getDaqListInfo(idx)}")
    x.disconnect()

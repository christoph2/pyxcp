#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Very basic hello-world example.
"""
from pprint import pprint
from pyxcp.cmdline import ArgumentParser

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
    gid = x.getId(0x1)
    result = x.fetch(gid.length)
    print("\nSlave properties:")
    print("=================")
    print("ID: '{}'".format(result.decode("utf8")))
    pprint(x.slaveProperties)

    if daq_info:
        dqp = x.getDaqProcessorInfo()
        print("\nDAQProcessor info:")
        print("==================")
        print(dqp)
        dqr = x.getDaqResolutionInfo()
        print("\nDAQResolution info:")
        print("===================")
        print(dqr)
        for idx in range(dqp.maxDaq):
            print("\nDAQList info #{}".format(idx))
            print("================")
            print("{}".format(x.getDaqListInfo(idx)))
    x.disconnect()

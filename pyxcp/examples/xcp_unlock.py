#!/usr/bin/env python
"""Very basic hello-world example.
"""
from pyxcp.cmdline import ArgumentParser


"""
"""


def callout(master, args):
    if args.sk_dll:
        master.seedNKeyDLL = args.sk_dll


ap = ArgumentParser(callout)
ap.parser.add_argument(
    "-s",
    "--sk-dll",
    dest="sk_dll",
    help="Seed-and-Key .DLL name",
    type=str,
    default=None,
)

with ap.run() as x:
    x.connect()

    print("")
    rps = x.getCurrentProtectionStatus()
    print("Protection before unlocking:", rps, end="\n\n")

    x.cond_unlock()

    rps = x.getCurrentProtectionStatus()
    print("Protection after unlocking:", rps)

    x.disconnect()

#!/usr/bin/env python
"""Very basic hello-world example."""

import argparse

from pyxcp.cmdline import ArgumentParser


parser = argparse.ArgumentParser(description="XCP unlock example")
parser.add_argument(
    "-s",
    "--sk-dll",
    dest="sk_dll",
    help="Seed-and-Key .DLL name",
    type=str,
    default=None,
)

ap = ArgumentParser(parser)

with ap.run() as x:
    if ap.args.sk_dll:
        x.seedNKeyDLL = ap.args.sk_dll

    x.connect()

    print("")
    rps = x.getCurrentProtectionStatus()
    print("Protection before unlocking:", rps, end="\n\n")

    x.cond_unlock()

    rps = x.getCurrentProtectionStatus()
    print("Protection after unlocking:", rps)

    x.disconnect()

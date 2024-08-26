#!/usr/bin/env python
"""Scan for available IDs.
"""

from pyxcp.cmdline import ArgumentParser


def main():
    ap = ArgumentParser(description="Scan for available IDs.")
    with ap.run() as x:
        x.connect()
        result = x.id_scanner()
        for key, value in result.items():
            print(f"{key}: {value}", end="\n\n")
        x.disconnect()


if __name__ == "__main__":
    main()

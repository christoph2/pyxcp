#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Scan for available IDs.
"""
from pprint import pprint

from pyxcp.cmdline import ArgumentParser


def main():
    ap = ArgumentParser(description="Scan for available IDs.")
    with ap.run() as x:
        x.connect()
        result = x.id_scanner()
        print("\n")
        print("Implemented IDs".center(80))
        print("=" * 80)
        pprint(result)
        x.disconnect()


if __name__ == "__main__":
    main()

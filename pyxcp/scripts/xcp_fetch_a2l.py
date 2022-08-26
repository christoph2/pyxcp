#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Fetch A2L file from XCP slave (if supported).
"""

from pathlib import Path
import sys

from pyxcp.cmdline import ArgumentParser
from pyxcp.types import XcpGetIdType


def main():
    ap = ArgumentParser(description="Fetch A2L file from XCP slave.")

    with ap.run() as x:
        x.connect()

        # TODO: error-handling.
        file_name = x.identifier(XcpGetIdType.FILENAME)
        content = x.identifier(XcpGetIdType.FILE_TO_UPLOAD)
        x.disconnect()
        if not file_name.lower().endswith(".a2l"):
            file_name += ".a2l"
        phile = Path(file_name)
        if phile.exists():
            print(f"{file_name} already exists.")
            sys.exit(1)
        with phile.open("wt", encoding = "utf-8") as of:
            of.write(content)
        print(f"Created {file_name}")

if __name__ == "__main__":
    main()

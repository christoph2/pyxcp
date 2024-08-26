#!/usr/bin/env python
"""Fetch A2L file from XCP slave (if supported).
"""
import sys
from pathlib import Path

from rich.prompt import Confirm

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
        if not content:
            sys.exit(f"Empty response from ID '{XcpGetIdType.FILE_TO_UPLOAD!r}'.")
        if not file_name:
            file_name = "output.a2l"
        if not file_name.lower().endswith(".a2l"):
            file_name += ".a2l"
        dest = Path(file_name)
        if dest.exists():
            if not Confirm.ask(f"Destination file [green]{dest.name!r}[/green] already exists. Do you want to overwrite it?"):
                print("Aborting...")
                exit(1)
        with dest.open("wt", encoding="utf-8") as of:
            of.write(content)
        print(f"A2L data written to {file_name!r}.")


if __name__ == "__main__":
    main()

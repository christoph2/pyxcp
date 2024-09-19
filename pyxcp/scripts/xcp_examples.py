#!/usr/bin/env python

"""
Copy pyXCP examples to a given directory.
"""

import argparse
import sys
from pathlib import Path

from pyxcp import console


pyver = sys.version_info
if pyver.major == 3 and pyver.minor <= 9:
    import pkg_resources

    def copy_files_from_package(package_name: str, source_directory: str, args: argparse.Namespace) -> None:
        destination_directory = args.output_directory
        force = args.force
        for fn in pkg_resources.resource_listdir(package_name, source_directory):
            source_file = Path(pkg_resources.resource_filename(package_name, f"{source_directory}/{fn}"))
            if source_file.suffix == ".py":
                dest_file = Path(destination_directory) / fn
                if dest_file.exists() and not force:
                    console.print(f"[white]Destination file [blue]{fn!r} [white]already exists. Skipping.")
                    continue
                console.print(f"[blue]{source_file} [white]==> [green]{dest_file}")
                data = source_file.read_text(encoding="utf-8")
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(data, encoding="utf-8")

else:
    import importlib.resources

    def copy_files_from_package(package_name: str, source_directory: str, args: argparse.Namespace) -> None:
        destination_directory = args.output_directory
        force = args.force
        for fn in importlib.resources.files(f"{package_name}.{source_directory}").iterdir():
            if fn.suffix == ".py":
                data = fn.read_text(encoding="utf-8")
                dest_file = Path(destination_directory) / fn.name
                if dest_file.exists() and not force:
                    console.print(f"[white]Destination file [blue]{fn.name!r} [white]already exists. Skipping.")
                    continue
                console.print(f"[blue]{fn} [white]==> [green]{dest_file}")
                dest_file.parent.mkdir(parents=True, exist_ok=True)
                dest_file.write_text(data, encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)

    parser.add_argument("output_directory", metavar="output_directory", type=Path, help="output directory")

    parser.add_argument("-f", "--force", action="store_true", help="overwrite existing files.")

    args = parser.parse_args()
    print("Copying pyXCP examples...\n")
    copy_files_from_package("pyxcp", "examples", args)


if __name__ == "__main__":
    main()

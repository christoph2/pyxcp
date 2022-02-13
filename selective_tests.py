#!/usr/bin/env python
# -*- coding: utf-8 -*-
import sys
from pathlib import Path


"""
dir_map
file_map
ignore_file
ignore_dir
"""


def main(args):
    print("SELECTIVE_TESTS called with:", args)
    dirs = set()
    args = args[1:]
    with open("st.txt", "wt") as of:
        for arg in args:
            parent = str(Path(arg).parent)
            dirs.add(parent)
            of.write(str(arg))
            of.write("\t")
            of.write(parent)
            of.write("\n")


if __name__ == "__main__":
    main(sys.argv)

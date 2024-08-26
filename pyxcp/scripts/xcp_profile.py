#!/usr/bin/env python
"""Create / convert pyxcp profiles (configurations).
"""

import sys

from pyxcp.cmdline import ArgumentParser


def main():
    if len(sys.argv) == 1:
        sys.argv.append("profile")
    elif len(sys.argv) >= 2 and sys.argv[1] != "profile":
        sys.argv.insert(1, "profile")

    ap = ArgumentParser(description="Create / convert pyxcp profiles (configurations).")

    try:
        with ap.run() as x:  # noqa: F841
            pass
    except FileNotFoundError as e:
        print(f"Error: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()

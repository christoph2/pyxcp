#!/usr/bin/env python
"""Create / convert pyxcp profiles (configurations).
"""

import sys

from pyxcp.cmdline import ArgumentParser


sys.argv.append("profile")
ap = ArgumentParser(description="Create / convert pyxcp profiles (configurations).")

with ap.run() as x:
    pass

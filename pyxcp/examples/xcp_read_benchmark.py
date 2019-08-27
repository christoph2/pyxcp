#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""Very basic hello-world example.
"""

__copyright__ = """
    pySART - Simplified AUTOSAR-Toolkit for Python.

   (C) 2009-2019 by Christoph Schueler <cpu12.gems@googlemail.com>

   All Rights Reserved

  This program is free software; you can redistribute it and/or modify
  it under the terms of the GNU General Public License as published by
  the Free Software Foundation; either version 2 of the License, or
  (at your option) any later version.

  This program is distributed in the hope that it will be useful,
  but WITHOUT ANY WARRANTY; without even the implied warranty of
  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
  GNU General Public License for more details.

  You should have received a copy of the GNU General Public License along
  with this program; if not, write to the Free Software Foundation, Inc.,
  51 Franklin Street, Fifth Floor, Boston, MA 02110-1301 USA.
"""

import time

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

sns.set()

from pyxcp.cmdline import ArgumentParser

ADDR = 0x4000
LENGTH = 0x1000
ITERATIONS = 100

ap = ArgumentParser(description = "pyXCP hello world.")
with ap.run() as x:
    xs = []
    ys = []
    x.connect()
    for ctoSize in range(8, 64 + 4, 4):
        print("CTO-Size: {}".format(ctoSize))
        xs.append(ctoSize)
        start = time.perf_counter()
        for idx in range(ITERATIONS):
            x.setMta(ADDR)
            data = x.fetch(LENGTH, ctoSize)
        et = time.perf_counter() - start
        ys.append(et)
        print("CTO size: {:-3} -- elapsed time {:-3.04}".format(ctoSize, et))
    x.disconnect()
    plt.plot(xs, ys)
    plt.show()

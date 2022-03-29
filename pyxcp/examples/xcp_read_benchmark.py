#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Very basic hello-world example.
"""
import time
from pyxcp.cmdline import ArgumentParser

import matplotlib.pyplot as plt
import numpy as np
import seaborn as sns

sns.set()


ADDR = 0x4000
LENGTH = 0x1000
ITERATIONS = 100

ap = ArgumentParser(description="pyXCP hello world.")
with ap.run() as x:
    xs = []
    ys = []
    x.connect()
    for ctoSize in range(8, 64 + 4, 4):
        print("CTO-Size: {}".format(ctoSize))
        xs.append(ctoSize)
        start = time.perf_counter()
        for _ in range(ITERATIONS):
            x.setMta(ADDR)
            data = x.fetch(LENGTH, ctoSize)
        et = time.perf_counter() - start
        ys.append(et)
        print("CTO size: {:-3} -- elapsed time {:-3.04}".format(ctoSize, et))
    x.disconnect()
    plt.plot(xs, ys)
    plt.show()

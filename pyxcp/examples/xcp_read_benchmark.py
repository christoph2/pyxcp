#!/usr/bin/env python
"""Very basic hello-world example.
"""
import time

import matplotlib.pyplot as plt
import seaborn as sns

from pyxcp.cmdline import ArgumentParser
from pyxcp.transport import FrameRecorderPolicy


sns.set()


ADDR = 0x4000
LENGTH = 0x1000
ITERATIONS = 100

recorder_policy = FrameRecorderPolicy()  # Create frame recorder.
ap = ArgumentParser(description="pyXCP hello world.", policy=recorder_policy)
with ap.run() as x:
    xs = []
    ys = []
    x.connect()
    for ctoSize in range(8, 64 + 4, 4):
        print(f"CTO-Size: {ctoSize}")
        xs.append(ctoSize)
        start = time.perf_counter()
        for _ in range(ITERATIONS):
            x.setMta(ADDR)
            data = x.fetch(LENGTH, ctoSize)
        et = time.perf_counter() - start
        ys.append(et)
        print(f"CTO size: {ctoSize:-3} -- elapsed time {et:-3.04}")
    x.disconnect()
    plt.plot(xs, ys)
    plt.show()

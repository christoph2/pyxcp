#!/usr/bin/env python
import time


class Timing:
    T_US = 1000 * 1000
    T_MS = 1000
    T_S = 1

    UNIT_MAP = {
        T_US: "uS",
        T_MS: "mS",
        T_S: "S",
    }
    FMT = "min:  {0:2.3f} {4}\nmax:  {1:2.3f} {4}\n" "avg:  {2:2.3f} {4}\nlast: {3:2.3f} {4}"

    def __init__(self, unit=T_MS, record=False):
        self.min = None
        self.max = None
        self.avg = None
        self._previous = None
        self.unit = unit
        self._record = record
        self._values = []

    def start(self):
        self._start = time.perf_counter()

    def stop(self):
        self._stop = time.perf_counter()
        elapsed = self._stop - self._start
        if self._record:
            self._values.append(elapsed)
        if self._previous:
            self.min = min(self._previous, elapsed)
            self.max = max(self._previous, elapsed)
            self.avg = (self._previous + elapsed) / 2
        else:
            self.min = self.max = self.avg = elapsed
        self._previous = elapsed

    def __str__(self):
        unitName = Timing.UNIT_MAP.get(self.unit, "??")
        self.min = 0 if self.min is None else self.min
        self.max = 0 if self.max is None else self.max
        self.avg = 0 if self.avg is None else self.avg
        self._previous = 0 if self._previous is None else self._previous
        return Timing.FMT.format(
            self.min * self.unit,
            self.max * self.unit,
            self.avg * self.unit,
            self._previous * self.unit,
            unitName,
        )

    __repr__ = __str__

    @property
    def values(self):
        return self._values

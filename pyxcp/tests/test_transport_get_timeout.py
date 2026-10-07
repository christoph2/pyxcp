import logging
import threading
import time
from collections import deque
from types import SimpleNamespace

import pytest

from pyxcp.transport.base import BaseTransport, EmptyFrameError


def make_stub(timeout_s: float):
    return SimpleNamespace(
        timeout=int(timeout_s * 1_000_000_000),
        timestamp=SimpleNamespace(value=0),
        timer_restart_event=threading.Event(),
        resQueue=deque(),
        resQueue_condition=threading.Condition(),
        logger=logging.getLogger("test"),
        DAQ_TIMEOUT_EXTENSION_FACTOR=BaseTransport.DAQ_TIMEOUT_EXTENSION_FACTOR,
    )


class Clock:
    def __init__(self, stub):
        self.stub = stub

    @property
    def value(self):
        return time.monotonic_ns()


def test_get_returns_response():
    stub = make_stub(0.2)
    stub.timestamp = Clock(stub)
    stub.resQueue.append(b"\xff")
    assert BaseTransport.get(stub) == b"\xff"


def test_get_plain_timeout():
    stub = make_stub(0.2)
    stub.timestamp = Clock(stub)
    with pytest.raises(EmptyFrameError):
        BaseTransport.get(stub)


def test_get_bounded_under_continuous_daq():
    stub = make_stub(0.2)
    stub.timestamp = Clock(stub)
    stop = threading.Event()

    def flood():
        while not stop.is_set():
            stub.timer_restart_event.set()
            time.sleep(0.01)

    t = threading.Thread(target=flood, daemon=True)
    t.start()
    begin = time.monotonic()
    try:
        with pytest.raises(EmptyFrameError):
            BaseTransport.get(stub)
    finally:
        stop.set()
        t.join()
    assert time.monotonic() - begin < 0.2 * BaseTransport.DAQ_TIMEOUT_EXTENSION_FACTOR + 0.5

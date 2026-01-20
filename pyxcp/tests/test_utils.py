import enum
from sys import version_info

from pyxcp.utils import (
    PYTHON_VERSION,
    CurrentDatetime,
    decode_bytes,
    delay,
    enum_from_str,
    flatten,
    functools_reduce_iconcat,
    getPythonVersion,
    hexDump,
    seconds_to_nanoseconds,
    short_sleep,
    slicer,
)


def test_hexdump(capsys):
    assert hexDump(range(16)) == "[00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f]"
    assert hexDump(bytes([0xDE, 0xAD, 0xBE, 0xEF])) == "[de ad be ef]"
    assert hexDump(bytearray([0x01, 0x02])) == "[01 02]"
    assert hexDump([0x10, 0x20]) == "[10 20]"
    assert hexDump((0x30, 0x40)) == "[30 40]"


def test_slicer1():
    res = slicer([1, 2, 3, 4, 5, 6, 7, 8], 4)
    assert res == [[1, 2, 3, 4], [5, 6, 7, 8]]


def test_slicer2():
    res = slicer(["10", "20", "30", "40", "50", "60", "70", "80"], 4, tuple)
    assert res == [("10", "20", "30", "40"), ("50", "60", "70", "80")]


def test_slicer_edge_cases():
    assert slicer([], 5) == []
    assert slicer([1, 2], 5) == [[1, 2]]


def test_flatten1():
    res = flatten([[1, 2, 3, 4], [5, 6, 7, 8]])
    assert res == [1, 2, 3, 4, 5, 6, 7, 8]
    assert flatten([]) == []
    assert flatten([[1]]) == [1]


def test_functools_reduce_iconcat():
    assert functools_reduce_iconcat([[1, 2], [3, 4]]) == [1, 2, 3, 4]


def test_version():
    assert getPythonVersion() == version_info
    assert PYTHON_VERSION == version_info
    assert getPythonVersion() == PYTHON_VERSION


def test_seconds_to_nanoseconds():
    assert seconds_to_nanoseconds(1) == 1_000_000_000
    assert seconds_to_nanoseconds(0.5) == 500_000_000


def test_decode_bytes():
    assert decode_bytes(b"hello") == "hello"
    assert decode_bytes("äöü".encode("utf-8")) == "äöü"
    # Test with invalid encoding that might be detected as something else or fail
    assert decode_bytes(b"\xff\xfeh\x00e\x00l\x00l\x00o\x00") == "hello"  # UTF-16 LE


def test_short_sleep():
    # Just verify it doesn't crash
    short_sleep()


def test_delay():
    import time

    start = time.perf_counter()
    delay(0.01)
    end = time.perf_counter()
    assert end - start >= 0.01


class MyEnum(enum.IntEnum):
    A = 1
    B = 2


def test_enum_from_str():
    assert enum_from_str(MyEnum, "A") == MyEnum.A
    assert enum_from_str(MyEnum, "B") == MyEnum.B
    assert enum_from_str(MyEnum, "C") is None


def test_current_datetime():
    # 1737387960000000000 ns is 2025-01-20 15:46:00 UTC
    ts_ns = 1737387960000000000
    cd = CurrentDatetime(ts_ns)
    assert cd.timestamp_ns == ts_ns
    assert isinstance(cd.timezone, str)
    assert isinstance(cd.utc_offset, int)
    assert isinstance(cd.dst_offset, int)
    s = str(cd)
    assert "CurrentDatetime" in s
    assert str(ts_ns) in s

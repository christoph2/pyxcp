from sys import version_info

from pyxcp.utils import PYTHON_VERSION, flatten, getPythonVersion, hexDump, slicer


def test_hexdump(capsys):
    print(hexDump(range(16)), end="")
    captured = capsys.readouterr()
    assert captured.out == "[00 01 02 03 04 05 06 07 08 09 0a 0b 0c 0d 0e 0f]"


def test_slicer1():
    res = slicer([1, 2, 3, 4, 5, 6, 7, 8], 4)
    assert res == [[1, 2, 3, 4], [5, 6, 7, 8]]


def test_slicer2():
    res = slicer(["10", "20", "30", "40", "50", "60", "70", "80"], 4, tuple)
    assert res == [("10", "20", "30", "40"), ("50", "60", "70", "80")]


def test_flatten1():
    res = flatten([[1, 2, 3, 4], [5, 6, 7, 8]])
    assert res == [1, 2, 3, 4, 5, 6, 7, 8]


def test_version():
    assert getPythonVersion() == version_info
    assert PYTHON_VERSION == version_info
    assert getPythonVersion() == PYTHON_VERSION

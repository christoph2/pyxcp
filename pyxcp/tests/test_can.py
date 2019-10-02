import pytest

from pyxcp.transport.can import (
    setDLC, calculateFilter, CAN_EXTENDED_ID,
    isExtendedIdentifier, stripIdentifier,
    Identifier, MAX_11_BIT_IDENTIFIER, MAX_29_BIT_IDENTIFIER,
    IdentifierOutOfRangeError)


def testSet0():
    assert setDLC(0) == 0


def testSet4():
    assert setDLC(4) == 4


def testSet8():
    assert setDLC(8) == 8


def testSet9():
    assert setDLC(9) == 12


def testSet12():
    assert setDLC(12) == 12


def testSet13():
    assert setDLC(13) == 16


def testSet16():
    assert setDLC(16) == 16


def testSet17():
    assert setDLC(17) == 20


def testSet20():
    assert setDLC(20) == 20


def testSet23():
    assert setDLC(23) == 24


def testSet24():
    assert setDLC(24) == 24


def testSet25():
    assert setDLC(25) == 32


def testSet32():
    assert setDLC(32) == 32


def testSet33():
    assert setDLC(33) == 48


def testSet48():
    assert setDLC(48) == 48


def testSet49():
    assert setDLC(49) == 64


def testSet64():
    assert setDLC(64) == 64


def testSet128():
    with pytest.raises(ValueError):
        setDLC(128)


def testNegative():
    with pytest.raises(ValueError):
        setDLC(-1)


def testfilter1():
    assert calculateFilter([0x101, 0x102, 0x103]) == (0x100, 0x7fc)


def testfilter2():
    assert calculateFilter([0x101, 0x102 | CAN_EXTENDED_ID, 0x103]) == (0x100, 0x1ffffffc)


def testfilter3():
    assert calculateFilter([0x1567 | CAN_EXTENDED_ID]) == (0x1567, 0x1fffffff)


def testfilter4():
    assert calculateFilter([
        0x1560 | CAN_EXTENDED_ID, 0x1561, 0x1562, 0x1563,
        0x1564, 0x1565, 0x1566, 0x1567, 0x1568, 0x1569, 0x156a, 0x156b,
        0x156c, 0x156d, 0x1563, 0x156f]) == (0x1560, 0x1ffffff0)


def testfilter5():
    assert calculateFilter([
        0x1560 | CAN_EXTENDED_ID, 0x1561, 0x1562, 0x1563,
        0x1564, 0x1565, 0x1566, 0x1567]) == (0x1560, 0x1ffffff8)


def testIsExtendedIdentifier1():
    assert isExtendedIdentifier(0x280) is False


def testIsExtendedIdentifier2():
    assert isExtendedIdentifier(0x280 | CAN_EXTENDED_ID) is True


def testStripIdentifier1():
    assert stripIdentifier(0x280) == 0x280


def testStripIdentifier2():
    assert stripIdentifier(0x280 | CAN_EXTENDED_ID) == 0x280


# def testSamplePointToTsegs1():
#     samplePointToTsegs


def test_identifier_works1():
    i = Identifier(CAN_EXTENDED_ID | 4711)
    assert i.id == 4711
    assert i.is_extended is True
    assert i.raw_id == CAN_EXTENDED_ID | 4711


def test_identifier_works2():
    i = Identifier(111)
    assert i.id == 111
    assert i.is_extended is False
    assert i.raw_id == 111


def test_identifier_max_works1():
    i = Identifier(CAN_EXTENDED_ID | MAX_29_BIT_IDENTIFIER)
    assert i.id == MAX_29_BIT_IDENTIFIER
    assert i.is_extended is True
    assert i.raw_id == CAN_EXTENDED_ID | MAX_29_BIT_IDENTIFIER


def test_identifier_max_works2():
    i = Identifier(MAX_11_BIT_IDENTIFIER)
    assert i.id == MAX_11_BIT_IDENTIFIER
    assert i.is_extended is False
    assert i.raw_id == MAX_11_BIT_IDENTIFIER


def test_identifier_outof_range_raises1():
    with pytest.raises(IdentifierOutOfRangeError):
        Identifier(CAN_EXTENDED_ID | (MAX_29_BIT_IDENTIFIER + 10))


def test_identifier_outof_range_raises2():
    with pytest.raises(IdentifierOutOfRangeError):
        Identifier(MAX_11_BIT_IDENTIFIER + 10)


def test_identifier_str_works1(capsys):
    i = Identifier(101)
    print(str(i), end="")
    captured = capsys.readouterr()
    assert captured.out == "Identifier(id = 0x00000065, is_extended = False)"


def test_identifier_repr_works1(capsys):
    i = Identifier(101)
    print(repr(i), end="")
    captured = capsys.readouterr()
    assert captured.out == "Identifier(0x00000065)"


def test_identifier_str_works2(capsys):
    i = Identifier(101 | CAN_EXTENDED_ID)
    print(str(i), end="")
    captured = capsys.readouterr()
    assert captured.out == "Identifier(id = 0x00000065, is_extended = True)"


def test_identifier_repr_works2(capsys):
    i = Identifier(101 | CAN_EXTENDED_ID)
    print(repr(i), end="")
    captured = capsys.readouterr()
    assert captured.out == "Identifier(0x80000065)"


def test_identifier_repr_does_the_trick1(capsys):
    i = Identifier(101)
    assert eval(repr(i)) == Identifier(101)


def test_identifier_repr_does_the_trick2(capsys):
    i = Identifier(101 | CAN_EXTENDED_ID)
    assert eval(repr(i)) == Identifier(101 | CAN_EXTENDED_ID)

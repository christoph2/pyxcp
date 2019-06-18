import pytest

from pyxcp.transport.can import setDLC

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



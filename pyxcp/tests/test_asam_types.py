import pytest

from pyxcp.asam import types


def testEncodeUint32_0():
    assert types.A_Uint32("<").encode(3415750566) == b"\xa67\x98\xcb"


def testDecodeUint32_0():
    assert types.A_Uint32("<").decode((0xA6, 0x37, 0x98, 0xCB)) == 3415750566


def testLittleEndian():
    assert isinstance(types.AsamBaseType(types.INTEL), types.AsamBaseType)


def testBigEndian():
    assert isinstance(types.AsamBaseType(types.MOTOROLA), types.AsamBaseType)


def testInvalidByteOrderRaisesTypeError():
    with pytest.raises(ValueError):
        types.AsamBaseType("#")

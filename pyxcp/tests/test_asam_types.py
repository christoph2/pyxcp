
import pytest

from pyxcp.asam import types


class TestEncode:

    def testEncodeUint32_0(self):
        assert types.A_Uint32("<").encode(3415750566) ==  b'\xa67\x98\xcb'


class TestDecode:

    def testDecodeUint32_0(self):
        assert types.A_Uint32("<").decode((0xa6, 0x37, 0x98, 0xcb)) ==  3415750566


class TestAsamBaseType:

    def testLittleEndian(self):
        assert isinstance(types.AsamBaseType(types.INTEL), types.AsamBaseType)

    def testBigEndian(self):
        assert isinstance(types.AsamBaseType(types.MOTOROLA), types.AsamBaseType)

    def testInvalidByteOrderRaisesTypeError(self):

        with pytest.raises(ValueError):
            types.AsamBaseType('#')


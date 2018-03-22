
import unittest

from pyxcp.asam import types

class TestEncode(unittest.TestCase):

    def testEncodeUint32_0(self):
        self.assertEqual(types.A_Uint32("<").encode(3415750566), b'\xa67\x98\xcb')


class TestDecode(unittest.TestCase):

    def testDecodeUint32_0(self):
        self.assertEqual(types.A_Uint32("<").decode((0xa6, 0x37, 0x98, 0xcb)), 3415750566)


class TestAsamBaseType(unittest.TestCase):

    def testLittleEndian(self):
        self.assertTrue(isinstance(types.AsamBaseType(types.INTEL), types.AsamBaseType))

    def testBigEndian(self):
        self.assertTrue(isinstance(types.AsamBaseType(types.MOTOROLA), types.AsamBaseType))

    def testInvalidByteOrderRaisesTypeError(self):
        self.assertRaises(TypeError, types.AsamBaseType, '#')

if __name__ == '__main__':
  unittest.main()

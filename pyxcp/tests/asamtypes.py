
import unittest

from pyxcp.asam import types

class Encode(unittest.TestCase):

  def testEncodeUint32_0(self):
    self.assertEqual(types.A_Uint32("<").encode(3415750566), b'\xa67\x98\xcb')


class Decode(unittest.TestCase):

  def testDecodeUint32_0(self):
    self.assertEqual(types.A_Uint32("<").decode((0xa6, 0x37, 0x98, 0xcb)), 3415750566)
    

if __name__ == '__main__':
  unittest.main()

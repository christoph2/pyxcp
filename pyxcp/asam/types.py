
import struct

INTEL = "<"
MOTOROLA = ">"

"""
    A_VOID: pseudo type for non-existing elements
    A_BIT: one bit
    A_UNIT8: unsigned integer 8-bit
    A_UINT16: unsigned integer 16-bit
    A_UINT32: unsigned integer 32-bit
    A_INT8: signed integer 8-bit, two's complement
    A_INT16: signed integer 16-bit, two's complement
    A_INT32: signed integer 32-bit, two's complement
    A_INT64: signed integer 64-bit, two's complement
    A_FLOAT32: IEEE 754 single precision
    A_FLOAT64: IEEE 754 double precision
    A_ASCIISTRING: string, ISO-8859-1 encoded
    A_UTF8STRING: string, UTF-8 encoded
    A_UNICODE2STRING: string, UCS-2 encoded
    A_BYTEFIELD: Field of bytes
"""

class AsamBaseType(object):

  def __init__(self, byteorder):
    assert byteorder in ("<", ">")
    self.byteorder = byteorder
        
  def encode(self, value):
    return struct.pack("{}{}".format(self.byteorder, self.FMT), value)
    
  def decode(self, value):
    return struct.unpack("{}{}".format(self.byteorder, self.FMT), bytes(value))[0]
    
    
class A_Uint8(AsamBaseType):
  FMT = "B"


class A_Uint16(AsamBaseType):
  FMT = "H"


class A_Uint32(AsamBaseType):
  FMT = "I"


class A_Uint64(AsamBaseType):    
  FMT = "Q"
  
class A_Int8(AsamBaseType):
  FMT = "b"


class A_Int16(AsamBaseType):
  FMT = "h"


class A_Int32(AsamBaseType):
  FMT = "i"


class A_Int64(AsamBaseType):    
  FMT = "q"
  
  

print(A_Uint16(INTEL).decode(b"\x04\x00"))
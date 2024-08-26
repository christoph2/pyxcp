#!/usr/bin/env python
import struct


INTEL = "<"
MOTOROLA = ">"

"""
    A_VOID: pseudo type for non-existing elements
    A_BIT: one bit
    A_ASCIISTRING: string, ISO-8859-1 encoded
    A_UTF8STRING: string, UTF-8 encoded
    A_UNICODE2STRING: string, UCS-2 encoded
    A_BYTEFIELD: Field of bytes
"""


class AsamBaseType:
    """Base class for ASAM codecs.

    Note
    ----
    Always use derived classes.
    """

    def __init__(self, byteorder):
        """

        Parameters
        ----------
        byteorder: char {'<', '>'}
          - '<' Little-endian
          - '>' Big-endian
        """
        if byteorder not in ("<", ">"):
            raise ValueError("Invalid byteorder.")
        self.byteorder = byteorder

    def encode(self, value):
        """Encode a value.

        Encode means convert a value, eg. an integer, to a byte-string.

        Parameters
        ----------
        value: data-type
          data-type is determined by derived class.

        Returns
        -------
        bytes
          Encoded value.
        """
        return struct.pack(f"{self.byteorder}{self.FMT}", value)

    def decode(self, value):
        """Decode a value.

        Decode means convert a byte-string to a meaningful data-type, eg. an
        integer.

        Parameters
        ----------
        value:  bytes

        Returns
        -------
        data-type
          data-type is determined by derived class.
        """
        return struct.unpack(f"{self.byteorder}{self.FMT}", bytes(value))[0]


class A_Uint8(AsamBaseType):
    """ASAM A_UINT8 codec."""

    FMT = "B"


class A_Uint16(AsamBaseType):
    """ASAM A_UINT16 codec."""

    FMT = "H"


class A_Uint32(AsamBaseType):
    """ASAM A_UINT32 codec."""

    FMT = "I"


class A_Uint64(AsamBaseType):
    """ASAM A_UINT64 codec."""

    FMT = "Q"


class A_Int8(AsamBaseType):
    """ASAM A_INT8 codec."""

    FMT = "b"


class A_Int16(AsamBaseType):
    """ASAM A_INT16 codec."""

    FMT = "h"


class A_Int32(AsamBaseType):
    """ASAM A_INT32 codec."""

    FMT = "i"


class A_Int64(AsamBaseType):
    """ASAM A_INT64 codec."""

    FMT = "q"


class A_Float32(AsamBaseType):
    """ASAM A_FLOAT32 codec."""

    FMT = "f"


class A_Float64(AsamBaseType):
    """ASAM A_FLOAT64 codec."""

    FMT = "d"

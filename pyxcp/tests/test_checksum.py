import pytest

from pyxcp import checksum


"""
XCP_ADD_11          0x10        0x10
XCP_ADD_12          0x0F10      0x0F10
XCP_ADD_14          0x00000F10  0x00000F10
XCP_ADD_22          0x1800      0x0710
XCP_ADD_24          0x00071800  0x00080710
XCP_ADD_44          0x140C03F8  0xFC040B10

XCP_CRC_16          0xC76A      0xC76A
XCP_CRC_16_CITT     0x9D50      0x9D50
XCP_CRC_32          0x89CD97CE  0x89CD97CE
"""

TEST = bytes(
    (
        0x01,
        0x02,
        0x03,
        0x04,
        0x05,
        0x06,
        0x07,
        0x08,
        0x09,
        0x0A,
        0x0B,
        0x0C,
        0x0D,
        0x0E,
        0x0F,
        0x10,
        0xF1,
        0xF2,
        0xF3,
        0xF4,
        0xF5,
        0xF6,
        0xF7,
        0xF8,
        0xF9,
        0xFA,
        0xFB,
        0xFC,
        0xFD,
        0xFE,
        0xFF,
        0x00,
    )
)


def testAdd11():
    assert checksum.check(TEST, "XCP_ADD_11") == 0x10


def testAdd12():
    assert checksum.check(TEST, "XCP_ADD_12") == 0x0F10


def testAdd14():
    assert checksum.check(TEST, "XCP_ADD_14") == 0x00000F10


def testAdd22():
    assert checksum.check(TEST, "XCP_ADD_22") == 0x1800


def testAdd24():
    assert checksum.check(TEST, "XCP_ADD_24") == 0x00071800


def testAdd44():
    assert checksum.check(TEST, "XCP_ADD_44") == 0x140C03F8


def testCrc16():
    assert checksum.check(TEST, "XCP_CRC_16") == 0xC76A


def testCrc16Ccitt():
    assert checksum.check(TEST, "XCP_CRC_16_CITT") == 0x9D50


def testCrc32():
    assert checksum.check(TEST, "XCP_CRC_32") == 0x89CD97CE


def testUserDefined():
    with pytest.raises(NotImplementedError):
        checksum.check(TEST, "XCP_USER_DEFINED")

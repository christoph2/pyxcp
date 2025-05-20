#!/usr/bin/env python

import pytest

from pyxcp.cpp_ext.cpp_ext import Bin, DaqList, McObject  # # noqa:  F401
from pyxcp.daq_stim.optimize import make_continuous_blocks
from pyxcp.daq_stim.optimize.binpacking import first_fit_decreasing


DAQ_LISTS_1 = [
    DaqList(
        "test",
        0,
        False,
        False,
        [
            ("voltage1", 0x0080051A - 4, 0, "F32"),  # 80053a
            ("voltage2", 0x0080051E - 4, 0, "F32"),
            ("voltage3", 0x00800522 - 4, 0, "F32"),
            ("voltage4", 0x00800526 - 4, 0, "F32"),
            ("sine_wave", 0x00800512, 0, "F32"),
        ],
    ),
]

DAQ_LISTS_2 = [
    DaqList(
        "test",
        0,
        False,
        False,
        [
            ("voltage1", 0x0080051A, 0, "F32"),  # 80053a
            ("voltage2", 0x0080051E, 0, "F32"),
            ("voltage3", 0x00800522, 0, "F32"),
            ("voltage4", 0x00800526, 0, "F32"),
            ("sq0", 0x00800516, 0, "U8"),
            ("sq1", 0x00800517, 0, "U8"),
            ("sine_wave", 0x00800512, 0, "F32"),
        ],
    ),
]

max_payload_size = 64
max_payload_size_first = 64

EXPECTED_BLOCK_VAR_1_64 = [
    McObject(
        name="",
        address=8389906,
        ext=0,
        data_type="",
        length=20,
        components=[
            McObject(name="sine_wave", address=8389906, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="voltage1", address=8389910, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="voltage2", address=8389914, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="voltage3", address=8389918, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="voltage4", address=8389922, ext=0, data_type="F32", length=4, components=[]),
        ],
    )
]

EXPECTED_BLOCK_VAR_1_8 = [
    McObject(
        name="",
        address=8389906,
        ext=0,
        data_type="",
        length=4,
        components=[McObject(name="sine_wave", address=8389906, ext=0, data_type="F32", length=4, components=[])],
    ),
    McObject(
        name="",
        address=8389910,
        ext=0,
        data_type="",
        length=4,
        components=[McObject(name="voltage1", address=8389910, ext=0, data_type="F32", length=4, components=[])],
    ),
    McObject(
        name="",
        address=8389914,
        ext=0,
        data_type="",
        length=4,
        components=[McObject(name="voltage2", address=8389914, ext=0, data_type="F32", length=4, components=[])],
    ),
    McObject(
        name="",
        address=8389918,
        ext=0,
        data_type="",
        length=4,
        components=[McObject(name="voltage3", address=8389918, ext=0, data_type="F32", length=4, components=[])],
    ),
    McObject(
        name="",
        address=8389922,
        ext=0,
        data_type="",
        length=4,
        components=[McObject(name="voltage4", address=8389922, ext=0, data_type="F32", length=4, components=[])],
    ),
]

EXPECTED_BLOCK_VAR_2_64 = [
    McObject(
        name="",
        address=8389906,
        ext=0,
        data_type="",
        length=6,
        components=[
            McObject(name="sine_wave", address=8389906, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="sq0", address=8389910, ext=0, data_type="U8", length=1, components=[]),
            McObject(name="sq1", address=8389911, ext=0, data_type="U8", length=1, components=[]),
        ],
    ),
    McObject(
        name="",
        address=8389914,
        ext=0,
        data_type="",
        length=16,
        components=[
            McObject(name="voltage1", address=8389914, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="voltage2", address=8389918, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="voltage3", address=8389922, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="voltage4", address=8389926, ext=0, data_type="F32", length=4, components=[]),
        ],
    ),
]

EXPECTED_BLOCK_VAR_2_8 = [
    McObject(
        name="",
        address=8389906,
        ext=0,
        data_type="",
        length=6,
        components=[
            McObject(name="sine_wave", address=8389906, ext=0, data_type="F32", length=4, components=[]),
            McObject(name="sq0", address=8389910, ext=0, data_type="U8", length=1, components=[]),
            McObject(name="sq1", address=8389911, ext=0, data_type="U8", length=1, components=[]),
        ],
    ),
    McObject(
        name="",
        address=8389914,
        ext=0,
        data_type="",
        length=4,
        components=[
            McObject(name="voltage1", address=8389914, ext=0, data_type="F32", length=4, components=[]),
        ],
    ),
    McObject(
        name="",
        address=8389918,
        ext=0,
        data_type="",
        length=4,
        components=[
            McObject(name="voltage2", address=8389918, ext=0, data_type="F32", length=4, components=[]),
        ],
    ),
    McObject(
        name="",
        address=8389922,
        ext=0,
        data_type="",
        length=4,
        components=[
            McObject(name="voltage3", address=8389922, ext=0, data_type="F32", length=4, components=[]),
        ],
    ),
    McObject(
        name="",
        address=8389926,
        ext=0,
        data_type="",
        length=4,
        components=[
            McObject(name="voltage4", address=8389926, ext=0, data_type="F32", length=4, components=[]),
        ],
    ),
]

BIN_PACKING_VAR1_8 = (
    (
        7,
        3,
        [
            McObject(
                name="",
                address=8389906,
                ext=0,
                data_type="",
                length=4,
                components=[
                    McObject(name="sine_wave", address=8389906, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
    (
        7,
        3,
        [
            McObject(
                name="",
                address=8389910,
                ext=0,
                data_type="",
                length=4,
                components=[
                    McObject(name="voltage1", address=8389910, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
    (
        7,
        3,
        [
            McObject(
                name="",
                address=8389914,
                ext=0,
                data_type="",
                length=4,
                components=[
                    McObject(name="voltage2", address=8389914, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
    (
        7,
        3,
        [
            McObject(
                name="",
                address=8389918,
                ext=0,
                data_type="",
                length=4,
                components=[
                    McObject(name="voltage3", address=8389918, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
)

BIN_PACKING_VAR2_8 = (
    (
        7,
        1,
        [
            McObject(
                name="",
                address=8389906,
                ext=0,
                data_type="",
                length=6,
                components=[
                    McObject(name="sine_wave", address=8389906, ext=0, data_type="F32", length=4, components=[]),
                    McObject(name="sq0", address=8389910, ext=0, data_type="U8", length=1, components=[]),
                    McObject(name="sq1", address=8389911, ext=0, data_type="U8", length=1, components=[]),
                ],
            )
        ],
    ),
    (
        7,
        3,
        [
            McObject(
                name="",
                address=8389914,
                ext=0,
                data_type="",
                length=4,
                components=[
                    McObject(name="voltage1", address=8389914, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
    (
        7,
        3,
        [
            McObject(
                name="",
                address=8389918,
                ext=0,
                data_type="",
                length=4,
                components=[
                    McObject(name="voltage2", address=8389918, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
    (
        7,
        3,
        [
            McObject(
                name="",
                address=8389922,
                ext=0,
                data_type="",
                length=4,
                components=[
                    McObject(name="voltage3", address=8389922, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
    (
        7,
        3,
        [
            McObject(
                name="",
                address=8389926,
                ext=0,
                data_type="",
                length=4,
                components=[
                    McObject(name="voltage4", address=8389926, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
)

BIN_PACKING_VAR1_64 = (
    (
        63,
        43,
        [
            McObject(
                name="",
                address=8389906,
                ext=0,
                data_type="",
                length=20,
                components=[
                    McObject(name="sine_wave", address=8389906, ext=0, data_type="F32", length=4, components=[]),
                    McObject(name="voltage1", address=8389910, ext=0, data_type="F32", length=4, components=[]),
                    McObject(name="voltage2", address=8389914, ext=0, data_type="F32", length=4, components=[]),
                    McObject(name="voltage3", address=8389918, ext=0, data_type="F32", length=4, components=[]),
                    McObject(name="voltage4", address=8389922, ext=0, data_type="F32", length=4, components=[]),
                ],
            )
        ],
    ),
)

BIN_PACKING_VAR2_64 = (
    63,
    41,
    [
        McObject(
            name="",
            address=8389914,
            ext=0,
            data_type="",
            length=16,
            components=[
                McObject(name="voltage1", address=8389914, ext=0, data_type="F32", length=4, components=[]),
                McObject(name="voltage2", address=8389918, ext=0, data_type="F32", length=4, components=[]),
                McObject(name="voltage3", address=8389922, ext=0, data_type="F32", length=4, components=[]),
                McObject(name="voltage4", address=8389926, ext=0, data_type="F32", length=4, components=[]),
            ],
        ),
        McObject(
            name="",
            address=8389906,
            ext=0,
            data_type="",
            length=6,
            components=[
                McObject(name="sine_wave", address=8389906, ext=0, data_type="F32", length=4, components=[]),
                McObject(name="sq0", address=8389910, ext=0, data_type="U8", length=1, components=[]),
                McObject(name="sq1", address=8389911, ext=0, data_type="U8", length=1, components=[]),
            ],
        ),
    ],
)


@pytest.mark.parametrize(
    "daq_lists, expected_blocks, payload_size",
    [
        (DAQ_LISTS_1, EXPECTED_BLOCK_VAR_1_64, 64),
        (DAQ_LISTS_1, EXPECTED_BLOCK_VAR_1_8, 8),
        (DAQ_LISTS_2, EXPECTED_BLOCK_VAR_2_64, 64),
        (DAQ_LISTS_2, EXPECTED_BLOCK_VAR_2_8, 8),
    ],
)
def test_make_continuous_blocks(daq_lists, expected_blocks, payload_size):
    daq_list = daq_lists[0]
    blocks = make_continuous_blocks(daq_list.measurements, payload_size - 1, payload_size - 1)
    for block, expected_block in zip(blocks, expected_blocks):
        assert block == expected_block


@pytest.mark.parametrize(
    "blocks, expected_blocks, payload_size",
    [
        (EXPECTED_BLOCK_VAR_1_8, BIN_PACKING_VAR1_8, 8),
        (EXPECTED_BLOCK_VAR_2_8, BIN_PACKING_VAR2_8, 8),
        (EXPECTED_BLOCK_VAR_1_64, BIN_PACKING_VAR1_64, 64),
        (EXPECTED_BLOCK_VAR_2_64, BIN_PACKING_VAR2_64, 64),
    ],
)
def test_first_fit_decreasing(blocks, expected_blocks, payload_size):
    res = first_fit_decreasing(blocks, payload_size - 1, payload_size - 1)  # noqa:  F841
    # for entry in res:
    #    print(entry.size, entry.residual_capacity, entry.entries)

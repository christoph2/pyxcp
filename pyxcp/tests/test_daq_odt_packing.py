#!/usr/bin/env python
"""Tests for ODT packing in DaqProcessor.setup().

Verifies that `maxOdtEntrySizeDaq` only caps the size of a single ODT entry, while
the per-ODT container capacity is `MAX_DTO - overhead`. Measurements should pack up
to the full container capacity, and the resulting ODT count should grow only when
the data genuinely exceeds one ODT.
"""

import logging

from pyxcp.cpp_ext.cpp_ext import DaqList

from pyxcp.daq_stim import DaqProcessor


class AttrDict(dict):
    def __getattr__(self, name):
        return self[name]


# tiny per-entry cap, large DTO.
DAQ_INFO = {
    "valid": {"processor": True, "resolution": True, "events": True},
    "processor": {
        "keyByte": {
            "addressExtension": "AE_DIFFERENT_WITHIN_ODT",
            "identificationField": "IDF_ABS_ODT_NUMBER",
            "optimisationType": "OM_DEFAULT",
        },
        "maxDaq": 2,
        "minDaq": 0,
        "properties": {
            "configType": "DYNAMIC",
            "pidOffSupported": False,
            "prescalerSupported": True,
            "resumeSupported": True,
            "timestampSupported": False,
        },
    },
    "resolution": {
        "granularityOdtEntrySizeDaq": 1,
        "maxOdtEntrySizeDaq": 4,
        "timestampMode": {"fixed": False, "size": "NO_TIME_STAMP", "unit": "DAQ_TIMESTAMP_UNIT_1MS"},
        "timestampTicks": 0,
    },
}

MAX_ODT = 16  # per A2L DAQ_LIST


class MockMaster:
    def __init__(self):
        self.slaveProperties = AttrDict({"maxDto": 255, "supportsDaq": True, "byteOrder": "INTEL", "interleavedMode": False})
        self.alloc_odt_calls = []

    def getDaqInfo(self, include_event_lists=False):
        return DAQ_INFO

    def freeDaq(self):
        pass

    def allocDaq(self, daq_count):
        pass

    def allocOdt(self, daq_num, odt_count):
        self.alloc_odt_calls.append((daq_num, odt_count))

    def allocOdtEntry(self, daq_num, odt_num, entry_count):
        pass

    def setDaqPtr(self, *a, **k):
        pass

    def writeDaq(self, *a, **k):
        pass

    def setDaqListMode(self, *a, **k):
        pass

    def startStopDaqList(self, *a, **k):
        return AttrDict({"firstPid": 0})


def _run_setup(measurements):
    daq_lists = [DaqList("event_1", 0, False, True, measurements)]
    daq = DaqProcessor(daq_lists, logger=logging.getLogger("test.daq"))
    daq.pid_off = False
    daq.xcp_master = MockMaster()
    daq.set_parameters = lambda *a, **k: None
    daq.setup()
    return daq.xcp_master.alloc_odt_calls


def test_small_max_odt_entry_size_does_not_inflate_odt_count():
    """100 non-contiguous 1-byte measurements must pack into a single ODT.

    The entries cannot be merged (addresses are spaced apart), so this exercises
    pure bin-packing. With a 255-byte DTO the container holds far more than 100
    one-byte entries, so a single ODT is expected.
    """
    measurements = [(f"m{i}", 0x1000 + i * 4, 0, "U8") for i in range(100)]
    alloc_odt_calls = _run_setup(measurements)

    assert len(alloc_odt_calls) == 1
    _daq_num, odt_count = alloc_odt_calls[0]
    assert odt_count == 1


def test_measurements_exceeding_one_odt_span_multiple_odts():
    """Measurements that exceed one ODT's capacity must spill into more ODTs.

    The per-ODT container holds MAX_DTO - overhead = 254 bytes, and each entry is
    capped at max_entry_size = min(maxOdtEntrySizeDaq=4, 254) = 4 bytes, so 63
    four-byte entries fit per ODT. Using one more than that (64) must produce a
    second ODT, confirming the ODT count grows only when the data genuinely
    outgrows a single ODT.
    """
    overhead = 1  # IDF_ABS_ODT_NUMBER, no timestamp, no PID_OFF
    container = 255 - overhead
    entry_size = 4
    entries_per_odt = container // entry_size  # 63

    n = entries_per_odt + 1

    measurements = [(f"m{i}", 0x2000 + i * 8, 0, "U32") for i in range(n)]
    alloc_odt_calls = _run_setup(measurements)

    assert len(alloc_odt_calls) == 1
    _daq_num, odt_count = alloc_odt_calls[0]
    expected = -(-n // entries_per_odt)  # ceil(64 / 63) == 2
    assert expected == 2
    assert odt_count == expected

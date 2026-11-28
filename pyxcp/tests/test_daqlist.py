"""Tests for the SaxElectronics fork DAQ handler (pyxcp/custom_patches/daqlist.py)."""

from pyxcp.custom_patches.daqlist import DaqDataHandler


def test_frames_are_sorted_per_daq_list():
    h = DaqDataHandler()
    h._process_daq_data_simple(bytes([0, 1, 0xAA, 0xBB]))
    h._process_daq_data_simple(bytes([0, 2, 0xCC]))
    assert h.pop_odtdata_for_daqlist_stored_by_entry(1) == (0, b"\xaa\xbb")
    assert h.pop_odtdata_for_daqlist_stored_by_entry(2) == (0, b"\xcc")
    assert h.pop_odtdata_for_daqlist_stored_by_entry(1) is None
    assert h.pop_odtdata_for_daqlist_stored_by_entry(99) is None


def test_complete_sample_emitted_on_odt_wraparound():
    h = DaqDataHandler()
    # Sample 1: ODT 0, 1, 2 for DAQ list 0
    for odt in (0, 1, 2):
        h._process_daq_data_simple(bytes([odt, 0, odt]))
    assert h.pop_received_daq_data_stored_by_sample_point(0) is None  # not complete until wraparound
    # Next sample starts -> previous one is complete
    h._process_daq_data_simple(bytes([0, 0, 0x10]))
    assert h.pop_received_daq_data_stored_by_sample_point(0) == [(0, b"\x00"), (1, b"\x01"), (2, b"\x02")]
    assert h.pop_received_daq_data_stored_by_sample_point(0) is None


def test_daq_lists_are_independent():
    h = DaqDataHandler()
    h._process_daq_data_simple(bytes([0, 0, 1]))
    h._process_daq_data_simple(bytes([1, 0, 2]))
    h._process_daq_data_simple(bytes([0, 1, 3]))  # different DAQ list, must not close list 0's sample
    assert h.pop_received_daq_data_stored_by_sample_point(0) is None
    h._process_daq_data_simple(bytes([0, 0, 4]))
    assert h.pop_received_daq_data_stored_by_sample_point(0) == [(0, b"\x01"), (1, b"\x02")]

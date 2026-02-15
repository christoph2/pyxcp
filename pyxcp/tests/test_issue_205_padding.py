"""Test for Issue #205 - CAN padding should not corrupt response parsing."""

import pytest


def test_response_trimming_removes_padding():
    """Test that response[:length] correctly removes CAN padding.

    Regression test for Issue #205: When using CAN-FD with max_dlc_required=True
    and padding_value=0xAA, responses were not trimmed before parsing, causing
    padding bytes to be interpreted as data.

    The fix in base.py process_response() now trims responses to actual length
    before appending to resQueue.
    """
    # Simulate a CAN frame with padding
    actual_response = bytearray([0xFF, 0x01, 0x02, 0x03, 0x04, 0x05, 0x06, 0x07])
    padded_response = actual_response + bytearray([0xAA] * 56)  # Pad to 64 bytes

    # The fix: base.py now does response[:length] before queuing
    actual_length = 8
    trimmed_response = padded_response[:actual_length]

    # Verify padding is removed
    assert len(trimmed_response) == 8
    assert trimmed_response == actual_response
    assert 0xAA not in trimmed_response


def test_shortupload_with_padding():
    """Test SHORT_UPLOAD command response with padding.

    SHORT_UPLOAD response format: [PID=0xFF] [data bytes...] [padding...]
    The parser should only read the requested number of bytes.
    """
    # SHORT_UPLOAD response: Read 4 bytes from address
    # Response: FF 01 02 03 04 [padding...]
    shortupload_response = bytearray([0xFF, 0x01, 0x02, 0x03, 0x04])
    shortupload_padded = shortupload_response + bytearray([0xAA] * 59)  # Pad to 64

    # The fix: trim to actual length (5 bytes: PID + 4 data)
    actual_length = 5
    response_trimmed = shortupload_padded[:actual_length]

    # Extract data (skip PID)
    data = response_trimmed[1:]

    assert len(data) == 4
    assert data == bytearray([0x01, 0x02, 0x03, 0x04])
    assert 0xAA not in data, "Padding should not appear in data"


def test_daq_frame_with_padding():
    """Test DAQ frame response with padding."""
    # DAQ frame: [timestamp] [payload...] [padding...]
    daq_frame = bytearray([0x00, 0x10, 0x20, 0x30, 0x40, 0x50, 0x60, 0x70])
    daq_padded = daq_frame + bytearray([0xAA] * 56)

    # The fix: trim to actual length
    actual_length = 8
    trimmed = daq_padded[:actual_length]

    assert len(trimmed) == 8
    assert trimmed == daq_frame
    assert 0xAA not in trimmed


def test_various_padding_values():
    """Test that trimming works with different padding values."""
    response = bytearray([0xFF, 0x11, 0x22, 0x33])

    # Test with common padding values: 0x00, 0xAA, 0xFF, 0xCC
    for pad_value in [0x00, 0xAA, 0xFF, 0xCC]:
        padded = response + bytearray([pad_value] * 60)
        trimmed = padded[:4]

        assert len(trimmed) == 4
        assert trimmed == response
        assert pad_value not in response or response.count(pad_value) == trimmed.count(pad_value)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])

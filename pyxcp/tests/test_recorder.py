import pytest

from pyxcp.recorder.rekorder import _PyXcpLogFileWriter


def test_writer_rejects_payload_larger_than_format_length(tmp_path):
    writer = _PyXcpLogFileWriter(str(tmp_path / "oversized"), 1, 1, "")

    with pytest.raises(ValueError, match="16-bit length field"):
        writer.add_frame(1, 0, 0, 65536, b"x" * 65536)

    writer.finalize()

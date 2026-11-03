import io

import pytest

from tts_bench.backend.protocol import ProtocolError, encode_frame, read_frame, write_frame


def test_round_trip_with_and_without_payload():
    buf = io.BytesIO()
    write_frame(buf, {"type": "chunk", "texto": "áé"}, b"\x01\x02")
    write_frame(buf, {"type": "done"})
    buf.seek(0)
    assert read_frame(buf) == ({"type": "chunk", "texto": "áé"}, b"\x01\x02")
    assert read_frame(buf) == ({"type": "done"}, b"")


def test_eof_returns_none():
    assert read_frame(io.BytesIO(b"")) is None


def test_truncated_raises():
    raw = encode_frame({"type": "chunk"}, b"abcdef")
    for cut in (3, 10, len(raw) - 2):
        with pytest.raises(ProtocolError):
            read_frame(io.BytesIO(raw[:cut]))

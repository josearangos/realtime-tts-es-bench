import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.errors import StreamingNotSupportedError

TOL_NS = 20_000_000


@pytest.mark.parametrize("gran", ["chunk", "sentence"])
def test_stream_timing(gran, voice):
    a = FakeAdapter(gran, first_chunk_delay_s=0.1, chunk_interval_s=0.05, n_chunks=3)
    a.load()
    try:
        t0 = __import__("time").perf_counter_ns()
        chunks = list(a.stream("hola", voice))
        assert len(chunks) == 3
        stamps = [c.produced_at_ns for c in chunks]
        assert stamps == sorted(stamps) and len(set(stamps)) == 3
        assert abs((stamps[0] - t0) - 100_000_000) < TOL_NS
        assert abs((stamps[1] - stamps[0]) - 50_000_000) < TOL_NS
        res = a.synthesize("hola", voice)
        assert res.first_audio_ns == res.chunks[0].produced_at_ns
        assert abs((res.first_audio_ns - res.request_started_ns) - 100_000_000) < TOL_NS
    finally:
        a.close()


def test_none_granularity(voice):
    a = FakeAdapter("none")
    a.load()
    try:
        assert a.synthesize("hola", voice).first_audio_ns is None
        with pytest.raises(StreamingNotSupportedError):
            a.stream("hola", voice)
    finally:
        a.close()

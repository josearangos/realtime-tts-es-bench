import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.errors import SynthesisError


def test_midstream_failure_carries_partial_chunks(voice):
    a = FakeAdapter("chunk", fail_after_chunks=2)
    a.load()
    try:
        got = []
        with pytest.raises(SynthesisError) as ei:
            for c in a.stream("hola", voice):
                got.append(c)
        assert len(got) == 2 and len(ei.value.partial_chunks) == 2
        with pytest.raises(SynthesisError):
            a.synthesize("hola", voice)
    finally:
        a.close()

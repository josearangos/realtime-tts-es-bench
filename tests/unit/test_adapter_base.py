import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.errors import EngineAlreadyLoadedError, InputLimitError, SynthesisError


def test_input_limit_checked_before_engine(voice):
    a = FakeAdapter(max_chars=5)
    a.load()
    with pytest.raises(InputLimitError):
        a.synthesize("123456", voice)
    a.close()


def test_text_unchanged_and_within_limit_ok(voice):
    a = FakeAdapter(max_chars=5)
    a.load()
    assert len(a.synthesize("12345", voice).audio) > 0
    a.close()


def test_engine_exception_wrapped(voice):
    a = FakeAdapter(fail_after_chunks=1)
    a.load()
    with pytest.raises(SynthesisError) as ei:
        a.synthesize("hola", voice)
    assert len(ei.value.partial_chunks) == 1
    a.close()


def test_synthesize_before_load(voice):
    with pytest.raises(SynthesisError):
        FakeAdapter().synthesize("hola", voice)


def test_guard_released_on_close():
    a, b = FakeAdapter(), FakeAdapter(name="other")
    a.load()
    with pytest.raises(EngineAlreadyLoadedError):
        b.load()
    a.close()
    b.load()
    b.close()

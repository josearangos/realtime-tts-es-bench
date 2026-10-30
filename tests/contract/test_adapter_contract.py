import pytest

from tts_bench.adapters.fake import FakeAdapter

ADAPTERS = {
    "fake-chunk": lambda: FakeAdapter("chunk"),
    "fake-sentence": lambda: FakeAdapter("sentence"),
    "fake-none": lambda: FakeAdapter("none"),
}


@pytest.mark.parametrize("key", ADAPTERS)
def test_adapter_contract(key, voice):
    adapter = ADAPTERS[key]()
    try:
        load_s = adapter.load()
        assert load_s >= 0
        res = adapter.synthesize("Hola, ¿cómo estás?", voice)
        assert res.audio.size > 0
        assert res.sample_rate == adapter.sample_rate  # never resampled
        d = res.descriptor
        for f in ("name", "engine_version", "model_id", "license_code", "spanish_variant", "voice_kind"):
            assert getattr(d, f)
        assert d.streaming.granularity in ("chunk", "sentence", "none")
    finally:
        adapter.close()

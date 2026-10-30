import pytest

import tts_bench  # noqa: F401
from tts_bench.core.registry import get_adapter, register, registered_names


def test_unknown_lists_registered():
    with pytest.raises(KeyError) as ei:
        get_adapter("nope")
    assert "fake" in str(ei.value)


def test_new_adapter_usable_via_registry(voice):
    register("throwaway", "tts_bench.adapters.fake:FakeAdapter")
    assert "throwaway" in registered_names()
    a = get_adapter("throwaway", granularity="none", name="throwaway")
    a.load()
    try:
        assert a.synthesize("hola", voice).audio.size > 0
    finally:
        a.close()

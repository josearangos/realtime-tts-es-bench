import tts_bench  # noqa: F401
from tts_bench.core.registry import get_adapter

EXPECTED = {"phonon": "chunk", "piper": "sentence"}


def test_declared_constants():
    for name, gran in EXPECTED.items():
        assert get_adapter(name).descriptor.streaming.granularity == gran
    assert get_adapter("pocket_tts").descriptor.streaming.granularity in ("chunk", "none")

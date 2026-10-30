import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.errors import EngineAlreadyLoadedError


def test_second_engine_refused_then_allowed_after_close():
    a, b = FakeAdapter(name="a"), FakeAdapter(name="b")
    a.load()
    try:
        with pytest.raises(EngineAlreadyLoadedError):
            b.load()
    finally:
        a.close()
    b.load()
    b.close()

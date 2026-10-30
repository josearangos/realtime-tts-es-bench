import pytest

from tts_bench.core import adapter as adapter_mod
from tts_bench.core.voices import VoiceReference


class InMemoryVoiceLibrary:
    def resolve(self, name, kind=None, *, engine=None, use=None, content=None):
        return VoiceReference(name, kind, f"memory://{name}")


@pytest.fixture
def voice():
    return InMemoryVoiceLibrary().resolve("test", "fixed_voice")


@pytest.fixture(autouse=True)
def reset_guard():
    adapter_mod._LOADED = None
    yield
    adapter_mod._LOADED = None

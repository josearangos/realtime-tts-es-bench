import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.voices import VoiceReference
from tts_bench.corpus import Corpus, load_corpus


@pytest.fixture
def make_adapter():
    created = []

    def _make(**fake_kwargs):
        a = FakeAdapter(**fake_kwargs)
        created.append(a)
        return a

    yield _make
    for a in created:
        a.close()


@pytest.fixture
def voice():
    return VoiceReference("default", "fixed_voice", "memory://default")


@pytest.fixture
def mini_corpus():
    def _mini(n: int) -> Corpus:
        full = load_corpus()
        return Corpus(full.version, full.content_hash, full.sentences[:n])

    return _mini

import pytest

from tts_bench.core.adapter import BaseAdapter
from tts_bench.core.errors import EmptyAudioError, SynthesisError
from tts_bench.adapters.fake import FakeAdapter


class SilentAdapter(FakeAdapter):
    def _iter_engine(self, text, voice):
        return iter(())


def test_no_audio_raises_empty_audio_error(voice):
    a = SilentAdapter()
    a.load()
    try:
        with pytest.raises(EmptyAudioError):
            a.synthesize("hola", voice)
        with pytest.raises(SynthesisError, match="produced no audio"):
            a.synthesize("hola", voice)
    finally:
        a.close()

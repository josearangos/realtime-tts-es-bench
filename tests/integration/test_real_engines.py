"""Run in each engine's own venv; skipped when the engine or its voices are unavailable."""
import importlib.util

import pytest

from tts_bench.core.errors import EngineNotInstalledError, VoiceNotFoundError, WeightsMissingError
from tts_bench.core.registry import get_adapter
from tts_bench.voices import LocalVoiceLibrary

pytestmark = pytest.mark.engine

CASES = [
    ("phonon", "ptts", "valentina"),
    ("pocket_tts", "pocket_tts", "valentina"),
    ("pocket_tts", "pocket_tts", "emiliano"),
    ("piper", "piper", "es_MX-claude-high"),
]
TEXT = "Hola, esta es una prueba de síntesis de voz en español."


@pytest.mark.parametrize("engine,module,voice_name", CASES)
def test_real_engine_contract(engine, module, voice_name):
    if importlib.util.find_spec(module) is None:
        pytest.skip(f"{module} not installed in this environment")
    adapter = get_adapter(engine)
    try:
        adapter.load()
    except (EngineNotInstalledError, WeightsMissingError) as exc:
        pytest.skip(str(exc))
    try:
        try:
            ref = LocalVoiceLibrary().resolve(
                voice_name, adapter.descriptor.voice_kind, engine=adapter.descriptor.name
            )
        except VoiceNotFoundError as exc:
            pytest.skip(str(exc))
        try:
            res = adapter.synthesize(TEXT, ref)
        except Exception as exc:
            if "Weights" in type(exc).__name__ or "gated" in str(exc):
                pytest.skip(str(exc))
            raise
        assert res.audio.size > 0 and res.sample_rate > 0
        assert res.descriptor.engine_version and res.descriptor.spanish_variant
        assert (res.first_audio_ns is None) == (res.descriptor.streaming.granularity == "none")
    finally:
        adapter.close()

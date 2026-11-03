"""Short warm benchmark for the engine installed in the current venv; skipped otherwise."""
import importlib.util

import pytest

from tts_bench.core.errors import EngineNotInstalledError, VoiceNotFoundError, WeightsMissingError
from tts_bench.core.registry import get_adapter
from tts_bench.corpus import Corpus, load_corpus
from tts_bench.metrics.results import read_results, write_results
from tts_bench.metrics.runner import run_benchmark
from tts_bench.voices import LocalVoiceLibrary

pytestmark = pytest.mark.engine

CASES = [
    ("phonon", "ptts", "valentina-phonon"),
    ("pocket_tts", "pocket_tts", "valentina-pocket"),
    ("piper", "piper", "es_MX-claude-high"),
]


@pytest.mark.parametrize("engine,module,voice_name", CASES)
def test_short_warm_benchmark(engine, module, voice_name, tmp_path):
    import tts_bench.adapters  # noqa: F401

    if importlib.util.find_spec(module) is None:
        pytest.skip(f"{module} not installed in this environment")
    adapter = get_adapter(engine)
    try:
        voice = LocalVoiceLibrary().resolve(voice_name, adapter.descriptor.voice_kind, engine=engine)
    except VoiceNotFoundError as exc:
        pytest.skip(str(exc))
    full = load_corpus()
    corpus = Corpus(full.version, full.content_hash, full.sentences[:5])
    try:
        results = run_benchmark(adapter, corpus, voice, mode="warm", repetitions=2, warmup=1,
                                config={"limit": 5}, argv=["run", engine, "--mode", "warm"])
    except (EngineNotInstalledError, WeightsMissingError) as exc:
        pytest.skip(str(exc))
    path = write_results(results, tmp_path)
    again = read_results(path)
    assert again.summary["n_total"] == 10
    assert again.resources["peak_ram_mib_final"] > 0

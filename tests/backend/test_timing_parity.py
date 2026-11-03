import re
from pathlib import Path

import pytest

from tests.backend.conftest import request_body, ws_collect
from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.voices import VoiceReference
from tts_bench.metrics import runner
from tts_bench.metrics.timing import timing_from_marks

DOCS = Path(__file__).resolve().parents[2] / "docs"


class _S:
    id = "s"
    text = "Hola, buenos días."


def test_backend_matches_offline_harness(backend_factory):
    b = backend_factory(first_chunk_s=0.1, chunk_interval_s=0.04, audio_s=0.8, chunks=4)
    _, _, _, last, _ = ws_collect(b.client, request_body())
    a = FakeAdapter(first_chunk_delay_s=0.1, chunk_interval_s=0.04, audio_seconds=0.8, n_chunks=4)
    a.load()
    try:
        m = runner.measure_request(a, _S, VoiceReference("v", "fixed_voice", "memory://v"), 1, "steady")
    finally:
        a.close()
    assert last["ttfa_ms"] == pytest.approx(m.ttfa_ms, rel=0.15)
    assert last["generation_ms"] == pytest.approx(m.generation_ms, rel=0.15)
    assert last["rtf"] == pytest.approx(m.rtf, rel=0.15)


def test_identical_marks_give_identical_values():
    marks = [(0, 120_000_000, 10), (1, 160_000_000, 10)]
    one = timing_from_marks(0, marks, 160_000_000, 0.5, True)
    two = timing_from_marks(0, list(marks), 160_000_000, 0.5, True)
    assert one == two


def test_docs_definitions_match():
    backend = (DOCS / "backend.md").read_text(encoding="utf-8")
    metrics = (DOCS / "metrics.md").read_text(encoding="utf-8")
    for phrase in ("just before the synthesis call (`request_started_ns`)",
                   "last audio delivered (`finished_ns`)",
                   "first non-empty audio chunk delivered",
                   "each chunk's delivery; gap = since previous chunk"):
        assert phrase in metrics and phrase in backend
    for name in ("TTFA", "RTF", "Generation time", "Chunk latency"):
        assert re.search(rf"\| {name}", metrics) and re.search(rf"\| {name}", backend)

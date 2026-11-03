import numpy as np
import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.core.voices import VoiceReference
from tts_bench.metrics import runner
from tts_bench.metrics.timing import timing_from_marks

MS = 1_000_000


def test_hand_set_marks():
    marks = [(0, 200 * MS, 100), (1, 250 * MS, 100), (2, 300 * MS, 100)]
    t = timing_from_marks(0, marks, 350 * MS, 2.0, True)
    assert t.generation_ms == pytest.approx(350)
    assert t.ttfa_ms == pytest.approx(200)
    assert t.rtf == pytest.approx(0.35 / 2.0)
    assert [c.gap_ms for c in t.chunks] == pytest.approx([200, 50, 50])
    assert [c.at_ms for c in t.chunks] == pytest.approx([200, 250, 300])


def test_empty_first_chunk_skipped_for_ttfa():
    marks = [(0, 10 * MS, 0), (1, 40 * MS, 50)]
    assert timing_from_marks(0, marks, 50 * MS, 1.0, True).ttfa_ms == pytest.approx(40)


def test_no_streaming_gives_no_ttfa():
    t = timing_from_marks(0, [(0, 90 * MS, 10)], 90 * MS, 1.0, False)
    assert t.ttfa_ms is None


def test_zero_audio_gives_no_rtf():
    assert timing_from_marks(0, [], 10 * MS, 0.0, True).rtf is None


class _Sentence:
    id = "s1"
    text = "Hola, buenos días."


def test_runner_and_helper_agree():
    a = FakeAdapter(first_chunk_delay_s=0.03, chunk_interval_s=0.01, audio_seconds=0.5, n_chunks=3)
    a.load()
    try:
        voice = VoiceReference("v", "fixed_voice", "memory://v")
        result = a.synthesize(_Sentence.text, voice)
        marks = [(c.index, c.produced_at_ns, int(c.samples.size)) for c in result.chunks]
        t = timing_from_marks(result.request_started_ns, marks, result.finished_ns, 0.5, True)
        m = runner.measure_request(a, _Sentence, voice, 1, "steady")
        assert m.status == "ok"
        assert m.rtf == pytest.approx(m.generation_ms / 1000 / m.audio_seconds)
        assert t.ttfa_ms == pytest.approx(30, rel=0.5)
        assert m.ttfa_ms == pytest.approx(30, rel=0.5)
        assert [c.index for c in m.chunks] == [c.index for c in t.chunks]
    finally:
        a.close()

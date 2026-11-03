import pytest

from tts_bench.core.errors import EngineNotInstalledError
from tts_bench.metrics.runner import run_benchmark

FAST = dict(first_chunk_delay_s=0.0, chunk_interval_s=0.0)


def test_cold_reports_load_and_first_request(make_adapter, voice, mini_corpus):
    a = make_adapter(load_delay_s=0.3, first_chunk_delay_s=0.02, chunk_interval_s=0.0)
    r = run_benchmark(a, mini_corpus(4), voice, mode="cold", repetitions=2)
    s = r.summary
    assert s["load_time_ms"] == pytest.approx(300, rel=0.05)
    first = [m for m in r.measurements if m.phase == "first_request"]
    assert len(first) == 1 and first[0].repetition == 1
    assert first[0].sentence_id == mini_corpus(4).sentences[0].id
    # 4 sentences x 2 reps = 8 requests; one is the first request
    assert s["n_total"] == 7 and s["rtf"]["n"] == 7 and s["ttfa_ms"]["n"] == 7
    assert s["first_request"]["sentence_id"] == first[0].sentence_id
    assert s["first_request"]["penalty_ms"] == pytest.approx(first[0].generation_ms - s["generation_ms"]["p50"])


def test_warm_discards_warmup(make_adapter, voice, mini_corpus):
    a = make_adapter(load_delay_s=0.1, **FAST)
    r = run_benchmark(a, mini_corpus(3), voice, mode="warm", repetitions=2, warmup=3)
    assert len(r.measurements) == 6
    assert all(m.phase == "steady" for m in r.measurements)
    assert r.summary["n_total"] == 6
    assert r.summary["warmup"] == {"requests": 3, "discarded": True, "failed": 0}
    assert r.summary["load_time_ms"] == pytest.approx(100, rel=0.2)
    assert "first_request" not in r.summary.data


def test_failed_load_writes_nothing(make_adapter, voice, mini_corpus, monkeypatch):
    a = make_adapter()

    def boom():
        raise EngineNotInstalledError("fake", "pip install nothing")

    monkeypatch.setattr(a, "_load", boom)
    with pytest.raises(EngineNotInstalledError):
        run_benchmark(a, mini_corpus(2), voice, mode="warm")


def test_cli_failed_load_exit_2_no_file(tmp_path, monkeypatch):
    from tts_bench.adapters.fake import FakeAdapter
    from tts_bench.metrics.__main__ import main

    def boom(self):
        raise EngineNotInstalledError("fake", "pip install nothing")

    monkeypatch.setattr(FakeAdapter, "_load", boom)
    assert main(["run", "fake", "--mode", "warm", "--limit", "2", "--out", str(tmp_path)]) == 2
    assert list(tmp_path.iterdir()) == []


def test_warm_median_rtf_reproducible(make_adapter, voice, mini_corpus):
    medians = []
    for _ in range(2):
        a = make_adapter(first_chunk_delay_s=0.02, chunk_interval_s=0.005, audio_seconds=0.4)
        r = run_benchmark(a, mini_corpus(5), voice, mode="warm", repetitions=3, warmup=2)
        medians.append(r.summary["rtf"]["p50"])
    assert abs(medians[0] - medians[1]) / medians[0] <= 0.10

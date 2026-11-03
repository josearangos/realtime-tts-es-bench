import pytest

from tts_bench.metrics.model import Measurement
from tts_bench.metrics.stats import NOT_AVAILABLE, percentile, summarize


def m(i, rep=1, *, status="ok", phase="steady", rtf=0.5, gen=100.0, ttfa=20.0, audio=1.0):
    ok = status == "ok"
    return Measurement(
        f"S-{i}", rep, phase, status,
        audio_seconds=audio if ok else None, generation_ms=gen if ok else None,
        rtf=rtf if ok else None, ttfa_ms=ttfa if ok else None,
    )


def test_percentile_linear_interpolation():
    assert percentile([1, 2, 3, 4, 5], 50) == pytest.approx(3.0)
    assert percentile([1, 2, 3, 4, 5], 95) == pytest.approx(4.8)


def test_summarize_ignores_failed_invalid_and_first_request():
    rows = [m(1, rtf=0.2), m(2, rtf=0.4), m(3, status="failed"), m(4, status="invalid"),
            m(5, phase="first_request", rtf=9.0, gen=900.0)]
    s = summarize(rows)
    assert s["n_ok"] == 2 and s["n_failed"] == 1 and s["n_invalid"] == 1 and s["n_total"] == 4
    assert s["rtf"]["n"] == 2
    assert s["rtf"]["mean"] == pytest.approx(0.3)
    assert s["first_request"]["rtf"] == 9.0
    assert s["first_request"]["penalty_ms"] == pytest.approx(800.0)


def test_low_sample_flag():
    assert summarize([m(i) for i in range(19)])["rtf"]["p95_low_sample"] is True
    assert summarize([m(i) for i in range(20)])["rtf"]["p95_low_sample"] is False


def test_reliable_threshold():
    ok = [m(i) for i in range(18)]
    assert summarize(ok + [m(90, status="failed"), m(91, status="invalid")])["reliable"] is True  # exactly 10%
    assert summarize(ok + [m(90, status="failed"), m(91, status="invalid"), m(92, status="failed")])["reliable"] is False


def test_ttfa_not_available():
    s = summarize([m(1, ttfa=None), m(2, ttfa=None)])
    assert s["ttfa_ms"] == NOT_AVAILABLE
    assert "ttfa_note" in s.data


def test_throughput_median_and_per_repetition():
    rows = [m(1, 1, audio=2.0), m(2, 1, audio=2.0), m(3, 2, audio=2.0), m(4, 3, audio=2.0)]
    s = summarize(rows, windows_s={1: 2.0, 2: 1.0, 3: 4.0})
    t = s["throughput_audio_s_per_s"]
    assert t["per_repetition"] == [2.0, 2.0, 0.5]
    assert t["median"] == 2.0


def test_load_and_warmup_passthrough():
    s = summarize([m(1)], load_time_ms=300.0, warmup={"requests": 3, "discarded": True})
    assert s["load_time_ms"] == 300.0 and s["warmup"]["discarded"] is True

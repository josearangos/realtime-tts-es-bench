import pytest

from tts_bench.core.errors import ConsentRequiredError
from tts_bench.voices import ConsentRecord


@pytest.mark.parametrize("kw", [
    dict(permitted_uses=[]),
    dict(permitted_uses=["publish_results"]),
    dict(alias="has space"),
    dict(alias="Upper"),
    dict(date="2025-13-40"),
    dict(allowed_content=[]),
])
def test_invalid_records(kw):
    base = dict(alias="ana", date="2025", permitted_uses=["internal_benchmarking"], allowed_content=["inbound"])
    with pytest.raises(ValueError):
        ConsentRecord(**{**base, **kw})


def test_dates_and_permits():
    for d in ("2025", "2025-06-01"):
        r = ConsentRecord("ana", d, ["internal_benchmarking"], ["inbound"])
    assert r.permits("internal_benchmarking", "inbound") is None
    assert r.permits("published_results") == "published_results"
    assert r.permits(content="collections") == "collections"


def test_add_recording_without_consent(library, wav_factory):
    with pytest.raises(ConsentRequiredError, match="consent add"):
        library.add_recording(wav_factory(), "nobody", "es-CO")
    assert not (library.root / "recordings").exists()


def test_add_recording_stores_analysis(consented, wav_factory):
    info = consented.add_recording(wav_factory("m.wav", 6), "ana", "es-CO")
    assert info.recording_id.startswith("rec-") and len(info.recording_id) == 16
    assert "too_short" in info.warnings and "music_not_ruled_out" in info.warnings
    assert (consented.root / "recordings" / f"{info.recording_id}.wav").is_file()

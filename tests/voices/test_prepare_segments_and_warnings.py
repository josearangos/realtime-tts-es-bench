import pytest

from tts_bench.core.errors import ConsentRequiredError
from tts_bench.voices import audio_check, prepare
from tts_bench.voices.prepare import prepare_for_engine


def test_pocket_default_segment(consented, recording):
    prepare_for_engine(consented, recording.recording_id, "pocket_tts", "p1")
    e = consented.show("p1")
    assert e["segment"] == {"start_s": 0.0, "length_s": min(20.0, recording.duration_s)}
    assert e["kind"] == "reference_audio" and e["creation"] == "automated"
    assert audio_check.analyze(consented.resolve("p1").path_or_id)["duration_s"] == pytest.approx(e["segment"]["length_s"], abs=0.01)


def test_override(consented, recording):
    prepare_for_engine(consented, recording.recording_id, "pocket_tts", "p2", 2, 5)
    assert consented.show("p2")["segment"] == {"start_s": 2.0, "length_s": 5.0}


def test_phonon_registers_nothing(consented, recording):
    msg = prepare_for_engine(consented, recording.recording_id, "phonon", "v")
    assert "studio.gradium.ai" in msg and recording.recording_id in msg
    assert consented.public_index() == []


def test_same_recording_across_engines(consented, recording, wav_factory, tmp_path):
    prepare_for_engine(consented, recording.recording_id, "pocket_tts", "val-pocket")
    f = tmp_path / "ph.safetensors"; f.write_bytes(b"s")
    consented.register("val-phonon", "phonon", "stored_voice_file", f, recording_id=recording.recording_id,
                       segment={"start_s": 0, "length_s": 10}, creation="external: x", accent_label="es-CO")
    assert consented.show("val-phonon")["recording_id"] == consented.show("val-pocket")["recording_id"]
    assert consented.same_source(["val-phonon", "val-pocket"])
    other = consented.add_recording(wav_factory("o.wav", 13), "ana", "es-CO")
    prepare_for_engine(consented, other.recording_id, "pocket_tts", "emi")
    assert not consented.same_source(["val-phonon", "emi"])


def test_accent_mismatch_only_when_known(consented, recording, monkeypatch):
    prepare_for_engine(consented, recording.recording_id, "pocket_tts", "a")
    assert not any(w.startswith("accent_mismatch") for w in consented.show("a")["warnings"])
    monkeypatch.setitem(prepare.ENGINE_PRIMARY_VARIANT, "pocket_tts", "es-ES")
    prepare_for_engine(consented, recording.recording_id, "pocket_tts", "b")
    assert "accent_mismatch:pocket_tts" in consented.show("b")["warnings"]


def test_without_consent_refused(consented, recording):
    (consented.root / "consent" / "ana.json").unlink()
    with pytest.raises(ConsentRequiredError):
        prepare_for_engine(consented, recording.recording_id, "pocket_tts", "x")

import pytest

from tests.voices.conftest import register_fake
from tts_bench.core.errors import ConsentRequiredError, VoiceEngineMismatchError, VoiceIntegrityError


def test_engine_and_kind_mismatch(consented, recording):
    register_fake(consented, recording, engine="fake")
    with pytest.raises(VoiceEngineMismatchError, match="fake.*other|other.*fake"):
        consented.resolve("v1", engine="other")
    with pytest.raises(VoiceEngineMismatchError):
        consented.resolve("v1", "reference_audio", engine="fake")
    assert consented.resolve("v1", "stored_voice_file", engine="fake")


def test_missing_and_modified(consented, recording):
    register_fake(consented, recording)
    path = consented.resolve("v1").path_or_id
    with open(path, "ab") as f:
        f.write(b"x")
    with pytest.raises(VoiceIntegrityError) as ei:
        consented.resolve("v1")
    assert ei.value.reason == "modified" and "expected" in str(ei.value)
    import os; os.remove(path)
    with pytest.raises(VoiceIntegrityError) as ei:
        consented.resolve("v1")
    assert ei.value.reason == "missing"


def test_consent_file_deleted(consented, recording):
    register_fake(consented, recording)
    (consented.root / "consent" / "ana.json").unlink()
    with pytest.raises(ConsentRequiredError):
        consented.resolve("v1")


def test_verify_reports_all(consented, recording):
    for n in ("a", "b", "c"):
        register_fake(consented, recording, n)
    for n in ("a", "c"):
        (consented.root / "voices" / n / f"{n}.bin").write_bytes(b"tampered")
    assert [n for n, _ in consented.verify()] == ["a", "c"]

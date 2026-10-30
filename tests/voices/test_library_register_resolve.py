import json

import pytest

from tts_bench.core.errors import ConsentRequiredError, VoiceAlreadyRegisteredError, VoiceNotFoundError
from tests.voices.conftest import register_fake
from tts_bench.voices import LocalVoiceLibrary


def test_register_and_resolve(consented, recording):
    register_fake(consented, recording)
    e = consented.show("v1")
    for k in ("name", "engine", "kind", "cloned", "file", "owned", "sha256", "recording_id", "consent_id",
              "segment", "creation", "accent_label", "warnings", "created"):
        assert k in e
    assert e["cloned"] and e["owned"]
    ref = consented.resolve("v1")
    assert ref.path_or_id.startswith("/") and ref.kind == "stored_voice_file"


def test_cloned_requires_links(consented, recording, tmp_path):
    f = tmp_path / "x.bin"; f.write_bytes(b"x")
    for kw in (dict(recording_id=None, segment={"start_s": 0, "length_s": 1}),
               dict(recording_id=recording.recording_id, segment=None)):
        with pytest.raises(ConsentRequiredError):
            consented.register("z", "fake", "stored_voice_file", f, creation="c", accent_label="a", **kw)


def test_fixed_voice_needs_nothing(library):
    library.register_fixed("es_MX-claude-high", "piper", "es_MX-claude-high", "es-MX", "downloaded")
    e = library.show("es_MX-claude-high")
    assert not e["cloned"] and e["consent_id"] is None and e["segment"] is None
    assert library.resolve("es_MX-claude-high", "fixed_voice", engine="piper").path_or_id == "es_MX-claude-high"


def test_piper_name_must_match_voice_id(library):
    with pytest.raises(ValueError, match="voice id"):
        library.register_fixed("mine", "piper", "es_MX-claude-high", "es-MX", "d")


def test_unknown_and_duplicate(consented, recording):
    register_fake(consented, recording)
    with pytest.raises(VoiceNotFoundError, match="v1"):
        consented.resolve("nope")
    with pytest.raises(VoiceAlreadyRegisteredError):
        register_fake(consented, recording)


def test_public_index_has_no_paths(consented, recording):
    register_fake(consented, recording)
    row = consented.public_index()[0]
    assert set(row) == {"name", "engine", "kind", "cloned", "accent_label", "sha256", "recording_id"}
    assert str(consented.root) not in json.dumps(row)


def test_same_source(consented, recording, wav_factory):
    register_fake(consented, recording, "a", "phonon")
    register_fake(consented, recording, "b", "pocket_tts")
    other = consented.add_recording(wav_factory("o.wav", 13), "ana", "es-CO")
    register_fake(consented, other, "c", "pocket_tts")
    assert consented.same_source(["a", "b"]) and consented.same_source(["a"])
    assert not consented.same_source(["a", "c"])


def test_same_source_false_with_fixed(consented, recording):
    register_fake(consented, recording, "a")
    consented.register_fixed("es_AR-daniela-high", "piper", "es_AR-daniela-high", "es-AR", "d")
    assert not consented.same_source(["a", "es_AR-daniela-high"])


def test_unreadable_index_is_empty(tmp_path):
    (tmp_path / "library.json").write_text("{not json")
    with pytest.raises(VoiceNotFoundError):
        LocalVoiceLibrary(tmp_path).resolve("x")

import json

import pytest

from tests.voices.conftest import register_fake
from tts_bench.core.errors import VoiceAlreadyRegisteredError, VoiceNotFoundError


def test_remove_keeps_unowned(consented, tmp_path):
    model = tmp_path / "m.onnx"; model.write_bytes(b"m")
    consented.register_fixed("m", "piper", str(model), "es-MX", "d")
    gen = consented.root / "generated" / "m"; gen.mkdir(parents=True); (gen / "a.wav").write_bytes(b"1")
    consented.remove("m")
    assert model.exists() and not gen.exists()
    with pytest.raises(VoiceNotFoundError):
        consented.resolve("m")


def test_withdraw(consented, recording, tmp_path):
    for n in ("a", "b"):
        register_fake(consented, recording, n)
        g = consented.root / "generated" / n; g.mkdir(parents=True); (g / "o.wav").write_bytes(b"1")
    res = tmp_path / "results"; res.mkdir()
    hit = {"voice": {"name": "a", "recording_id": recording.recording_id}, "ttfa_ms": 12.5}
    other = {"voice": {"name": "zzz"}, "ttfa_ms": 1}
    (res / "hit.json").write_text(json.dumps(hit)); (res / "other.json").write_text(json.dumps(other))
    report = consented.withdraw("ana", res)
    assert sorted(report.voices_removed) == ["a", "b"] and len(report.results_marked) == 1
    assert report.tombstones_written == 2 and report.files_deleted >= 5
    root = consented.root
    assert not list((root / "voices").rglob("*.bin")) and not list((root / "generated").rglob("*.wav"))
    assert not (root / "consent" / "ana.json").exists() and not list((root / "recordings").glob("*.wav"))
    assert json.loads((res / "hit.json").read_text()) == {**hit, "voice_withdrawn": True}
    assert json.loads((res / "other.json").read_text()) == other
    with pytest.raises(VoiceNotFoundError):
        consented.resolve("a")
    with pytest.raises(VoiceAlreadyRegisteredError):
        register_fake(consented, recording, "a")
    tomb = json.loads((root / "library.json").read_text())["withdrawn"]
    assert {t["name"] for t in tomb} == {"a", "b"}


def test_withdraw_without_results_dir(consented, recording, tmp_path):
    register_fake(consented, recording)
    assert consented.withdraw("ana", tmp_path / "missing").results_marked == []


def test_remove_marks_results_and_blocks_reuse(consented, recording, tmp_path):
    register_fake(consented, recording, "a")
    register_fake(consented, recording, "b")
    g = consented.root / "generated" / "a"; g.mkdir(parents=True); (g / "o.wav").write_bytes(b"1")
    res = tmp_path / "results"; res.mkdir()
    hit = {"voice": {"name": "a"}, "ttfa_ms": 9.0}
    keep = {"voice": {"name": "b"}, "ttfa_ms": 8.0}
    (res / "hit.json").write_text(json.dumps(hit)); (res / "keep.json").write_text(json.dumps(keep))
    report = consented.remove("a", res)
    assert report.results_marked == [str(res / "hit.json")] and report.tombstones_written == 1
    assert json.loads((res / "hit.json").read_text()) == {**hit, "voice_withdrawn": True}
    assert json.loads((res / "keep.json").read_text()) == keep
    assert not g.exists() and consented.resolve("b")
    with pytest.raises(VoiceNotFoundError):
        consented.resolve("a")
    with pytest.raises(VoiceAlreadyRegisteredError):
        register_fake(consented, recording, "a")
    assert [t["name"] for t in json.loads((consented.root / "library.json").read_text())["withdrawn"]] == ["a"]

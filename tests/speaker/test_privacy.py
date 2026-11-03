import json
import re
from pathlib import Path

from tts_bench.speaker.files import write_results
from tts_bench.speaker.scoring import score_embeddings

from .conftest import fixed_embeddings

ROOT = Path(__file__).resolve().parents[2]


def test_results_hold_no_vectors_paths_or_voice_material(tmp_path, mini_corpus):
    corpus = mini_corpus(3)
    emb = fixed_embeddings({s.id: (0.123456, 0.654321, 0.111111) for s in corpus.sentences})
    r = score_embeddings(emb, corpus, command="python -m tts_bench.speaker score embeddings.json",
                         environment={"python": "3.11"})
    p = write_results(r, tmp_path / "r.json")
    raw = p.read_text(encoding="utf-8")
    assert "0.654321" not in raw and "vector" not in raw
    assert ".wav" not in raw and "reference.wav" not in raw
    assert str(tmp_path) not in raw and not re.search(r'"/[A-Za-z]', raw) and "/Users/" not in raw
    data = json.loads(raw)
    assert "hostname" not in raw and "user" not in {k.lower() for k in data["environment"]}
    forbidden = {"vector", "reference", "path", "file"}
    assert not (forbidden & set(data))


def test_gitignore_covers_voice_derived_data():
    patterns = (ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "output/speaker/" in patterns and "*.wav" in patterns


def test_no_voice_material_is_tracked_under_results_speaker():
    banned = {".wav", ".safetensors", ".npy", ".pt"}
    found = [p for p in (ROOT / "results" / "speaker").rglob("*") if p.suffix in banned]
    assert found == []

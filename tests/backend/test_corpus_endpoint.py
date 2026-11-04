"""GET /v1/corpus (feature 008): text only, main subset, never cloning.jsonl."""

import json

from tts_bench.corpus import loader


def test_corpus_shape_and_fields(client):
    r = client.get("/v1/corpus")
    assert r.status_code == 200
    body = r.json()
    assert body["corpus_version"] == loader.read_version(loader.default_corpus_dir()).version
    assert body["count"] == len(body["sentences"]) > 0
    for s in body["sentences"]:
        assert set(s) == {"id", "text", "campaign", "scenario", "tags"}


def test_text_is_spoken_form_and_main_only(client):
    sentences = loader.read_sentences(loader.default_corpus_dir() / "sentences.jsonl")
    main = {s.id: s for s in sentences if s.subset.value == "main"}
    got = {s["id"]: s for s in client.get("/v1/corpus").json()["sentences"]}
    assert set(got) == set(main)
    for sid, s in main.items():
        assert got[sid]["text"] == s.speak_text


def test_cloning_content_never_appears(client):
    cloning = [json.loads(line) for line in
               (loader.default_corpus_dir() / "cloning.jsonl").read_text(encoding="utf-8").splitlines() if line.strip()]
    text = client.get("/v1/corpus").text
    ids = {s["id"] for s in json.loads(text)["sentences"]}
    for rec in cloning:
        assert rec["id"] not in ids
        assert rec["text"] not in text


def test_missing_corpus_returns_503_without_path(backend, tmp_path):
    backend.config.repo_root = tmp_path / "nowhere"
    r = backend.client.get("/v1/corpus")
    assert r.status_code == 503
    assert r.json()["error"] == "corpus_unavailable"
    assert str(tmp_path) not in r.text
    assert backend.client.get("/v1/health").status_code == 200


def test_malformed_corpus_returns_503(backend, tmp_path):
    (tmp_path / "corpus").mkdir()
    (tmp_path / "corpus" / "sentences.jsonl").write_text("{not json\n")
    (tmp_path / "corpus" / "VERSION.json").write_text("{}")
    backend.config.repo_root = tmp_path
    r = backend.client.get("/v1/corpus")
    assert r.status_code == 503 and str(tmp_path) not in r.text

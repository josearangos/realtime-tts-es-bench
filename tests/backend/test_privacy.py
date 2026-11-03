import hashlib
import json

import pytest

from tests.backend.conftest import request_body, ws_collect


def _forbidden(b, tmp_path):
    values = {str(tmp_path), str(b.library.root), ".safetensors", "recording_id", "consent_id", "rec-"}
    for v in b.library.public_index():
        if v["sha256"]:
            values.add(v["sha256"])
        if v["recording_id"]:
            values.add(v["recording_id"])
    return values


def test_voice_objects_have_exactly_four_keys(client):
    for e in client.get("/v1/engines").json()["engines"]:
        for v in e["voices"]:
            assert set(v) == {"name", "kind", "cloned", "accent_label"}


def test_nothing_leaks_anywhere(backend_factory, tmp_path):
    b = backend_factory(fail_after=2)
    bodies = [b.client.get("/v1/engines").text, b.client.get("/v1/health").text]
    r_ok = b.client.post("/v1/synthesize", json=request_body(voice="tono-fijo"))
    bodies += [json.dumps(dict(r_ok.headers))]
    bodies += [b.client.post("/v1/synthesize", json=request_body(voice="nada")).text,
               b.client.post("/v1/synthesize", json=request_body(engine="nada")).text,
               b.client.post("/v1/synthesize", json=request_body()).text]
    start, chunks, audio, last, _ = ws_collect(b.client, request_body())
    bodies += [json.dumps([start, chunks, last])]
    bodies += [b.log_path.read_text(encoding="utf-8")]
    for text in bodies:
        for bad in _forbidden(b, tmp_path):
            assert bad not in text, bad
        assert '"ana"' not in text and ".wav" not in text


def test_no_file_routes(client):
    for path in ("/static/x", "/files/x", "/voices/x", "/cloned_voices/library.json",
                 "/v1/../cloned_voices/library.json", "/v1/voices", "/cloned_voices/"):
        assert client.get(path).status_code in (404, 405), path


def test_all_library_voices_of_an_engine_are_listed(client, backend):
    names = {v["name"] for v in client.get("/v1/engines/fake").json()["voices"]}
    expected = {v["name"] for v in backend.library.public_index() if v["engine"] == "fake"}
    assert names == expected and len(names) == 2  # cloned + fixed, no consent filtering

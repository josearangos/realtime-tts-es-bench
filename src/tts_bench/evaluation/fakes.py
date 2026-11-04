"""Test doubles: a synthetic dataset (sine WAVs) and an in-process fake Label Studio HTTP server.

The fake does NOT deduplicate imports, so a double import is detectable by tests.
"""

from __future__ import annotations

import json
import re
import threading
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, urlparse

import numpy as np

from .loudness import write_wav

FAKE_TOKEN = "fake-token"
# (engine, voice, accent, cloned)
FAKE_CONDITIONS = [
    ("fakea", "voz1", "es-CO", False),
    ("fakeb", "voz2", "es-MX", False),
    ("fakec", "clon1", "es-CO", True),
]


def _tone(freq: float, seconds: float = 0.6, rate: int = 16000, amp: float = 0.3) -> np.ndarray:
    t = np.arange(int(seconds * rate)) / rate
    return amp * np.sin(2 * np.pi * freq * t)


def make_fake_dataset(root: str | Path, n_main: int = 12, n_cloning: int = 6) -> dict:
    """Create corpus/, a voice library and output/{intelligibility,speaker}/ under `root`.

    Non-cloned conditions get main sentences; the cloned one gets the cloning subset (like the real layouts)
    plus main sentences too, so every subset has at least two conditions only for the main subset.
    """
    root = Path(root)
    corpus = root / "corpus"
    corpus.mkdir(parents=True, exist_ok=True)

    def rec(prefix, i, subset):
        return {"id": f"{prefix}-{i:03d}", "text": f"Frase de prueba número {i} de {prefix}.", "campaign": "collections",
                "scenario": "card_balance", "tags": ["question"], "address": "usted", "probes": "name",
                "reviewed": True, "subset": subset}

    main = [rec("COB" if i % 2 else "VEN", i, "main") for i in range(1, n_main + 1)]
    cloning = [rec("CLO", i, "cloning") for i in range(1, n_cloning + 1)]
    (corpus / "sentences.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in main) + "\n", encoding="utf-8")
    (corpus / "cloning.jsonl").write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in cloning) + "\n", encoding="utf-8")
    from tts_bench.corpus.loader import compute_hash
    (corpus / "VERSION.json").write_text(json.dumps({
        "version": "9.9.9", "date": "2026-01-01", "counts": {"main": n_main, "cloning": n_cloning},
        "content_sha256": compute_hash(corpus)}), encoding="utf-8")

    voices_dir = root / "voices_lib"
    _fake_voice_library(voices_dir, root / "fake-reference.wav")

    out = root / "output"
    for k, (engine, voice, accent, cloned) in enumerate(FAKE_CONDITIONS):
        d = out / ("speaker" if cloned else "intelligibility") / f"{engine}-{voice}"
        d.mkdir(parents=True, exist_ok=True)
        ids = [r["id"] for r in main] + ([r["id"] for r in cloning] if cloned else [])
        items = []
        for sid in ids:
            write_wav(d / f"{sid}.wav", _tone(200 + 40 * k + len(items) * 3), 16000)
            items.append({"file": f"{sid}.wav", "sentence_id": sid, "status": "ok", "sample_rate": 16000,
                          "duration_s": 0.6, "error": None})
        manifest = {"schema_version": 1, "corpus": {"subset": "main"},
                    "engine": {"name": engine, "voice": {"name": voice, "accent_label": accent,
                                                         "kind": "reference_audio" if cloned else "fixed_voice"}},
                    "items": items}
        (d / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return {"root": root, "corpus": corpus, "output": out, "voices_dir": voices_dir,
            "main_ids": [r["id"] for r in main], "cloning_ids": [r["id"] for r in cloning]}


def _fake_voice_library(voices_dir: Path, ref_wav: Path, uses=("human_evaluation",)) -> None:
    """A real LocalVoiceLibrary (so consent is enforced exactly as in production) with one cloned voice."""
    from tts_bench.voices.consent import ConsentRecord
    from tts_bench.voices.library import LocalVoiceLibrary

    write_wav(ref_wav, _tone(330, 3.0) + 0.05 * np.sin(2 * np.pi * 90 * np.arange(48000) / 16000), 16000)
    lib = LocalVoiceLibrary(voices_dir)
    lib.add_consent(ConsentRecord("fakeowner", "2025", list(uses), ["collections", "cloning_prompts"]))
    rec = lib.add_recording(ref_wav, "fakeowner", "es-CO", no_music_confirmed=True)
    lib.register("clon1", "fakec", "reference_audio", ref_wav, recording_id=rec.recording_id,
                 segment={"start_s": 0.0, "length_s": 3.0}, creation="automated", accent_label="es-CO")


class _State:
    def __init__(self):
        self.lock = threading.Lock()
        self.projects: list[dict] = []
        self.tasks: dict[int, list[dict]] = {}
        self.storages: dict[int, list[dict]] = {}
        self.users: list[dict] = []
        self.annotations: dict[int, list[dict]] = {}  # task id -> annotations
        self.next_id = 1
        self.import_calls = 0

    def nid(self) -> int:
        self.next_id += 1
        return self.next_id


class FakeLabelStudio:
    """Context manager exposing `.url`, `.token` and inspection/scripting helpers."""

    def __init__(self, token: str = FAKE_TOKEN):
        self.token = token
        self.state = _State()
        self._server: ThreadingHTTPServer | None = None
        self.healthy = True

    @property
    def url(self) -> str:
        return f"http://127.0.0.1:{self._server.server_address[1]}"

    def __enter__(self):
        outer = self

        class Handler(BaseHTTPRequestHandler):
            def log_message(self, *a):
                pass

            def _send(self, code, payload=None):
                body = json.dumps(payload).encode() if payload is not None else b""
                self.send_response(code)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(body)))
                self.end_headers()
                self.wfile.write(body)

            def _body(self):
                n = int(self.headers.get("Content-Length") or 0)
                return json.loads(self.rfile.read(n)) if n else None

            def _route(self, method):
                u = urlparse(self.path)
                q = {k: v[0] for k, v in parse_qs(u.query).items()}
                p = u.path
                if p == "/health":
                    return self._send(200, {"status": "UP"}) if outer.healthy else self._send(503, {})
                if self.headers.get("Authorization") != f"Token {outer.token}":
                    return self._send(401, {"detail": "bad token"})
                st = outer.state
                body = self._body() if method in ("POST", "PUT", "PATCH") else None
                with st.lock:
                    if p == "/api/projects" and method == "GET":
                        return self._send(200, {"count": len(st.projects), "results": st.projects})
                    if p == "/api/projects" and method == "POST":
                        proj = dict(body, id=st.nid())
                        st.projects.append(proj)
                        st.tasks[proj["id"]] = []
                        return self._send(201, proj)
                    if p == "/api/tasks" and method == "GET":
                        pid, page, size = int(q["project"]), int(q.get("page", 1)), int(q.get("page_size", 100))
                        chunk = st.tasks[pid][(page - 1) * size: page * size]
                        return self._send(200, {"tasks": chunk, "total": len(st.tasks[pid])})
                    m = re.fullmatch(r"/api/projects/(\d+)/import", p)
                    if m and method == "POST":
                        pid = int(m.group(1))
                        st.import_calls += 1
                        for t in body:
                            st.tasks[pid].append({"id": st.nid(), "data": t["data"]})
                        return self._send(201, {"task_count": len(body)})
                    m = re.fullmatch(r"/api/projects/(\d+)/export", p)
                    if m and method == "GET":
                        pid = int(m.group(1))
                        out = [dict(t, annotations=st.annotations.get(t["id"], [])) for t in st.tasks[pid]]
                        return self._send(200, out)
                    m = re.fullmatch(r"/api/tasks/(\d+)", p)
                    if m and method == "DELETE":
                        tid = int(m.group(1))
                        for pid in st.tasks:
                            st.tasks[pid] = [t for t in st.tasks[pid] if t["id"] != tid]
                        st.annotations.pop(tid, None)
                        return self._send(204)
                    if p == "/api/storages/localfiles/" and method == "GET":
                        return self._send(200, st.storages.get(int(q.get("project", 0)), []))
                    if p == "/api/storages/localfiles/" and method == "POST":
                        s = dict(body, id=st.nid())
                        st.storages.setdefault(body["project"], []).append(s)
                        return self._send(201, s)
                    if p == "/api/users/" and method == "GET":
                        return self._send(200, st.users)
                    if p == "/api/users/" and method == "POST":
                        if not body.get("username"):
                            return self._send(400, {"validation_errors": {"username": ["This field is required."]}})
                        if any(u["email"] == body["email"] for u in st.users):
                            return self._send(400, {"email": ["exists"]})
                        u = {"id": st.nid(), "email": body["email"]}
                        st.users.append(u)
                        return self._send(201, u)
                self._send(404, {"detail": "not found"})

            def do_GET(self):
                self._route("GET")

            def do_POST(self):
                self._route("POST")

            def do_DELETE(self):
                self._route("DELETE")

        self._server = ThreadingHTTPServer(("127.0.0.1", 0), Handler)
        self._thread = threading.Thread(target=self._server.serve_forever, daemon=True)
        self._thread.start()
        return self

    def __exit__(self, *exc):
        self._server.shutdown()
        self._server.server_close()

    # helpers for tests ---------------------------------------------------
    def project(self, title_prefix: str) -> dict:
        return next(p for p in self.state.projects if p["title"].startswith(title_prefix))

    def tasks(self, title_prefix: str) -> list[dict]:
        return self.state.tasks[self.project(title_prefix)["id"]]

    def add_user(self, email: str) -> int:
        with self.state.lock:
            u = {"id": self.state.nid(), "email": email}
            self.state.users.append(u)
            return u["id"]

    def annotate(self, task_id: int, user_id: int, result: list, lead_time: float = 5.0,
                 created_at: str = "2026-11-04T10:00:00Z") -> None:
        with self.state.lock:
            self.state.annotations.setdefault(task_id, []).append({
                "id": self.state.nid(), "completed_by": user_id, "result": result,
                "lead_time": lead_time, "created_at": created_at})

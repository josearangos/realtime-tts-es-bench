"""JSON Lines request log (data-model RequestLogEntry). Never holds audio or paths."""

from __future__ import annotations

import hashlib
import json
import threading
import time
from pathlib import Path

from .scrub import scrub_paths


class RequestLog:
    def __init__(self, path: str | Path, log_text: bool = False, max_bytes: int = 5 * 1024 * 1024, keep: int = 3):
        self.path = Path(path)
        self.log_text = log_text
        self.max_bytes = max_bytes
        self.keep = keep
        self._lock = threading.Lock()

    def _rotate(self) -> None:
        for i in range(self.keep - 1, 0, -1):
            src = self.path.with_name(f"{self.path.name}.{i}")
            if src.exists():
                src.replace(self.path.with_name(f"{self.path.name}.{i + 1}"))
        if self.path.exists():
            self.path.replace(self.path.with_name(f"{self.path.name}.1"))
        old = self.path.with_name(f"{self.path.name}.{self.keep + 1}")
        old.unlink(missing_ok=True)

    def log_request(self, *, request_id, engine, voice, text, status, engine_version=None, model_id=None,
                    error=None, summary=None, concurrent_engines=0) -> None:
        text = text or ""
        entry = {
            "ts": time.strftime("%Y-%m-%dT%H:%M:%S", time.gmtime()) + "Z",
            "request_id": request_id,
            "engine": engine,
            "engine_version": engine_version,
            "model_id": model_id,
            "voice": voice,
            "text_chars": len(text),
            "text_sha256": hashlib.sha256(text.encode("utf-8")).hexdigest(),
            "status": status,
            "concurrent_engines": concurrent_engines,
        }
        if error:
            entry["error"] = scrub_paths(str(error))
        if summary:
            entry["summary"] = summary
        if self.log_text:
            entry["text"] = text
        line = json.dumps(entry, ensure_ascii=False) + "\n"
        with self._lock:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            if self.path.exists() and self.path.stat().st_size + len(line.encode("utf-8")) > self.max_bytes:
                self._rotate()
            with self.path.open("a", encoding="utf-8") as f:
                f.write(line)

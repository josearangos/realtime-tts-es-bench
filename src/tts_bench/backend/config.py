"""Backend configuration: environment plus an optional git-ignored backend.toml."""

from __future__ import annotations

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]

DEFAULT_VENVS = {
    "fake": ".venv-core",
    "phonon": ".venv-phonon",
    "pocket_tts": ".venv-pocket",
    "piper": ".venv-piper",
}


@dataclass
class BackendConfig:
    host: str = "127.0.0.1"
    port: int = 8000
    max_chars: int = 500
    queue_waiting: int = 2
    cancel_grace_s: float = 30.0
    request_timeout_s: float = 60.0
    voices_dir: str | None = None  # None: the voice library's own default location
    log_text: bool = False
    log_path: str = "output/backend/requests.jsonl"
    log_max_bytes: int = 5 * 1024 * 1024
    log_keep: int = 3
    repo_root: Path = field(default_factory=lambda: REPO_ROOT)
    venvs: dict[str, str] = field(default_factory=dict)
    python_overrides: dict[str, str] = field(default_factory=dict)  # engine -> interpreter (tests)
    worker_env: dict[str, str] = field(default_factory=dict)  # extra worker environment (tests)

    @classmethod
    def load(cls, path: str | Path | None = None) -> "BackendConfig":
        cfg = cls()
        toml_path = Path(path) if path else cfg.repo_root / "backend.toml"
        if toml_path.is_file():
            data = tomllib.loads(toml_path.read_text(encoding="utf-8"))
            for key in ("host", "port", "max_chars", "queue_waiting", "cancel_grace_s",
                        "request_timeout_s", "voices_dir", "log_text"):
                if key in data:
                    setattr(cfg, key, data[key])
            cfg.venvs = dict(data.get("venvs", {}))
        env = os.environ.get("TTS_BACKEND_MAX_CHARS")
        if env:
            cfg.max_chars = int(env)
        return cfg

    @property
    def log_dir(self) -> Path:
        p = Path(self.log_path)
        return (p if p.is_absolute() else self.repo_root / p).parent

    def venv_python(self, engine: str) -> Path:
        if engine in self.python_overrides:
            return Path(self.python_overrides[engine])
        venv = self.venvs.get(engine) or DEFAULT_VENVS.get(engine) or f".venv-{engine}"
        base = Path(venv)
        if not base.is_absolute():
            base = self.repo_root / base
        return base / "bin" / "python"

    def effective_limit(self, descriptor) -> int:
        limits = [self.max_chars]
        engine_limit = descriptor.input_limits.max_chars
        if engine_limit is not None:
            limits.append(engine_limit)
        return min(limits)

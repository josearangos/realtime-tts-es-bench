"""Engine and voice catalog: descriptors, availability with reasons, public voices only."""

from __future__ import annotations

import json
import subprocess
from pathlib import Path

from ..core.errors import (
    ConsentNotPermittedError,
    TTSBenchError,
    VoiceEngineMismatchError,
    VoiceIntegrityError,
    VoiceNotFoundError,
)
from ..core.registry import registered_names
from ..core.voices import VoiceReference
from .config import BackendConfig
from .errors import BackendError
from .scrub import scrub_paths

PUBLIC_VOICE_KEYS = ("name", "kind", "cloned", "accent_label")  # allow-list (FR-010)
NO_VOICES_NOTE = "no voices registered in the library"


def registered_engines() -> list[str]:
    from .. import adapters  # noqa: F401  (registers the engines)

    return registered_names()


def voices_for(engine: str, library) -> list[dict]:
    """Public voice objects for an engine, built from an explicit allow-list."""
    out = []
    for v in library.public_index():
        if v["engine"] == engine:
            out.append({k: v[k] for k in PUBLIC_VOICE_KEYS})
    return out


def resolve_voice(engine: str, voice: str, library) -> VoiceReference:
    names = [v["name"] for v in voices_for(engine, library)]
    if voice not in names:
        raise BackendError("unknown_voice", f"Unknown voice '{voice}' for engine '{engine}'.", available=names)
    try:
        return library.resolve(voice, engine=engine, use="internal_benchmarking")
    except ConsentNotPermittedError as exc:
        raise BackendError("voice_not_permitted", scrub_paths(str(exc))) from exc
    except (VoiceNotFoundError, VoiceEngineMismatchError) as exc:
        raise BackendError("unknown_voice", f"Unknown voice '{voice}' for engine '{engine}'.", available=names) from exc
    except VoiceIntegrityError as exc:
        raise BackendError("unknown_voice", f"Voice '{voice}' is not usable ({exc.reason}).", available=names) from exc
    except TTSBenchError as exc:
        raise BackendError("unknown_voice", scrub_paths(str(exc)), available=names) from exc


def probe(engine: str, config: BackendConfig, timeout: float = 20.0) -> dict:
    """Run the worker with --describe under the engine's venv. Returns
    {"availability": {...}, "descriptor": dict | None}."""
    python = config.venv_python(engine)
    if not Path(python).is_file():
        return {
            "descriptor": None,
            "availability": {
                "status": "unavailable", "reason": "venv_missing",
                "hint": f"Create the virtual environment for '{engine}' or point to it in backend.toml.",
            },
        }
    import os

    env = dict(os.environ)
    src = str(config.repo_root / "src")
    env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
    env.update({k: str(v) for k, v in config.worker_env.items()})
    try:
        proc = subprocess.run(
            [str(python), "-m", "tts_bench.backend.worker", engine, "--describe"],
            capture_output=True, text=True, timeout=timeout, env=env, cwd=str(config.repo_root),
        )
    except subprocess.TimeoutExpired:
        return {"descriptor": None, "availability": {"status": "unavailable", "reason": "error",
                                                       "hint": "The availability check timed out."}}
    try:
        data = json.loads(proc.stdout.strip().splitlines()[-1])
    except (IndexError, ValueError):
        return {"descriptor": None, "availability": {"status": "unavailable", "reason": "error",
                                                       "hint": scrub_paths(proc.stderr.strip()[-300:])}}
    if proc.returncode == 0:
        return {"descriptor": data, "availability": {"status": "available"}}
    reason = data.get("reason", "error")
    if reason not in ("not_installed", "weights_missing", "error"):
        reason = "error"
    return {"descriptor": None, "availability": {"status": "unavailable", "reason": reason,
                                                   "hint": scrub_paths(str(data.get("hint", "")))}}


def static_descriptor(engine: str) -> dict | None:
    """Descriptor from the adapter class itself (adapters import their engine only at load),
    used for engines whose probe failed so the listing still shows licence and streaming facts."""
    import dataclasses

    from ..core.registry import get_adapter

    try:
        return json.loads(json.dumps(dataclasses.asdict(get_adapter(engine).descriptor)))
    except Exception:  # noqa: BLE001
        return None


class Catalog:
    def __init__(self, config: BackendConfig, library, supervisors: dict) -> None:
        self.config = config
        self.library = library
        self.supervisors = supervisors
        self._cache: dict[str, dict] = {}

    def refresh(self) -> None:
        self._cache.clear()
        for sup in self.supervisors.values():
            sup.clear_unavailable()

    def engines(self) -> list[str]:
        return registered_engines()

    def _probe(self, engine: str) -> dict:
        if engine not in self._cache:
            self._cache[engine] = probe(engine, self.config)
        return self._cache[engine]

    def availability(self, engine: str) -> dict:
        sup = self.supervisors.get(engine)
        if sup is not None and sup.unavailable:
            return sup.unavailable
        return self._probe(engine)["availability"]

    def descriptor(self, engine: str) -> dict | None:
        sup = self.supervisors.get(engine)
        if sup is not None and sup.descriptor:
            return sup.descriptor
        return self._probe(engine)["descriptor"]

    def listing(self, engine: str) -> dict:
        self._probe(engine)
        availability = self.availability(engine)
        desc = self.descriptor(engine)
        sup = self.supervisors.get(engine)
        voices = voices_for(engine, self.library)
        d = desc or static_descriptor(engine) or {}
        limit = self.config.max_chars
        if d.get("input_limits", {}).get("max_chars") is not None:
            limit = min(limit, d["input_limits"]["max_chars"])
        item = {
            "name": engine,
            "engine_version": d.get("engine_version", "unknown (read at load)"),
            "model_id": d.get("model_id"),
            "license_code": d.get("license_code"),
            "license_model": d.get("license_model"),
            "license_flags": list(d.get("license_flags", [])),
            "language": d.get("language"),
            "spanish_variant": d.get("spanish_variant"),
            "supports_cloning": d.get("supports_cloning"),
            "voice_kind": d.get("voice_kind"),
            "streaming": {"granularity": d.get("streaming", {}).get("granularity")},
            "input_limit_chars": limit,
            "voices": voices,
            "availability": availability,
            "state": sup.state if sup is not None else "not_started",
            "queue_depth": sup.queue_depth if sup is not None else 0,
        }
        if not voices:
            item["note"] = NO_VOICES_NOTE
        return item

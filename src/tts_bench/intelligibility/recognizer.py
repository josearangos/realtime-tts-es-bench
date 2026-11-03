"""Speech recognizers: protocol, scripted fake, and faster-whisper (imported lazily)."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
from typing import Protocol

from .model import ACCENT_NOTE, RecognizerRecord


class RecognizerUnavailableError(Exception):
    """The recognizer package or its weights are missing (CLI exit 2)."""


class Recognizer(Protocol):
    def record(self) -> RecognizerRecord: ...
    def transcribe(self, path: str | Path) -> str: ...


def settings_hash(settings: dict) -> str:
    return hashlib.sha256(json.dumps(settings, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


class FakeRecognizer:
    """Returns scripted text per sentence id (the WAV file stem). Never for reported results."""

    def __init__(self, scripted: dict[str, str] | None = None) -> None:
        self.scripted = dict(scripted or {})
        self.calls: list[str] = []
        self._settings = {"language": "es", "model": "fake"}

    def record(self) -> RecognizerRecord:
        return RecognizerRecord(
            name="fake", checkpoint="fake", license="n/a", library_versions={},
            settings=self._settings, settings_hash=settings_hash(self._settings), device="cpu",
            accent_note=ACCENT_NOTE,
        )

    def transcribe(self, path: str | Path) -> str:
        stem = Path(path).stem
        self.calls.append(stem)
        return self.scripted.get(stem, "")


# License text per checkpoint, taken from the model card; verified when pinned (T038).
KNOWN_LICENSES = {
    "large-v3": ("MIT (Systran/faster-whisper-large-v3 model card)", None),
}
PERMISSIVE = ("mit", "apache", "bsd")


class FasterWhisperRecognizer:
    """faster-whisper with fixed greedy settings; identical for every engine."""

    def __init__(self, model: str = "large-v3", device: str = "cpu", compute_type: str = "int8") -> None:
        self.settings = {
            "model": model, "device": device, "compute_type": compute_type, "language": "es",
            "beam_size": 1, "temperature": 0, "vad_filter": False,
            "condition_on_previous_text": False, "initial_prompt": None,
        }
        try:
            import faster_whisper
        except ImportError as exc:
            raise RecognizerUnavailableError(
                "faster-whisper is not installed. Create the recognizer environment: "
                "python3.11 -m venv .venv-asr && .venv-asr/bin/pip install -e '.[asr]'"
            ) from exc
        self._version = getattr(faster_whisper, "__version__", None)
        try:
            self._model = faster_whisper.WhisperModel(model, device=device, compute_type=compute_type)
        except Exception as exc:  # weights missing, offline, bad compute type
            raise RecognizerUnavailableError(
                f"could not load the '{model}' weights ({exc}). The first run downloads them "
                "once; after that the recognizer works offline."
            ) from exc

    def record(self) -> RecognizerRecord:
        import importlib.metadata as md

        def ver(pkg: str):
            try:
                return md.version(pkg)
            except md.PackageNotFoundError:
                return None

        model = self.settings["model"]
        lic, flag = KNOWN_LICENSES.get(model, ("unknown", "license not verified for this checkpoint"))
        if flag is None and not lic.lower().startswith(PERMISSIVE):
            flag = "license is not a known permissive license"
        return RecognizerRecord(
            name="faster-whisper", checkpoint=model, license=lic,
            library_versions={"faster-whisper": ver("faster-whisper") or self._version,
                              "ctranslate2": ver("ctranslate2")},
            settings=self.settings, settings_hash=settings_hash(self.settings),
            device=f"{self.settings['device']}/{self.settings['compute_type']}",
            accent_note=ACCENT_NOTE, license_flag=flag,
        )

    def transcribe(self, path: str | Path) -> str:
        s = self.settings
        segments, _info = self._model.transcribe(
            str(path), language=s["language"], beam_size=s["beam_size"], temperature=s["temperature"],
            vad_filter=s["vad_filter"], condition_on_previous_text=s["condition_on_previous_text"],
            initial_prompt=s["initial_prompt"],
        )
        return " ".join(seg.text.strip() for seg in segments).strip()

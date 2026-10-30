from __future__ import annotations

from pathlib import Path
from typing import Iterator

import numpy as np

from ..core.adapter import BaseAdapter
from ..core.descriptor import EngineDescriptor, InputLimits, StreamingInfo
from ..core.errors import EngineNotInstalledError, WeightsMissingError
from ..core.voices import VoiceReference

_INSTALL = "Run: pip install -e '.[phonon]' (in its own virtual environment)."
_WEIGHTS = (
    "Download the model with: huggingface-cli download gradium/phonon-40m-es "
    "--local-dir ./phonon-40m-es"
)


class PhononAdapter(BaseAdapter):
    def __init__(self, model_dir: str | Path = "phonon-40m-es") -> None:
        super().__init__()
        self.model_dir = Path(model_dir)
        self._tts = None
        self._voices: set[str] = set()
        self.descriptor = EngineDescriptor(
            name="phonon",
            engine_version="unknown (read at load)",
            model_id="hf://gradium/phonon-40m-es",
            license_code="MIT OR Apache-2.0",
            license_model="CC BY-NC 4.0",
            license_flags=("non-commercial",),
            language="es",
            spanish_variant="es-CO (cloned stored voice)",
            voice_kind="stored_voice_file",
            supports_cloning=True,
            streaming=StreamingInfo("chunk"),
            input_limits=InputLimits(None),
            install_hint=_INSTALL,
            weights_hint=_WEIGHTS,
        )

    def _load(self) -> None:
        try:
            import ptts
        except ImportError as exc:
            raise EngineNotInstalledError("phonon", _INSTALL) from exc
        if not self.model_dir.is_dir():
            raise WeightsMissingError("phonon", f"Expected {self.model_dir}/. {_WEIGHTS}")
        from importlib.metadata import version

        self.descriptor = _with_version(self.descriptor, version("ptts"))
        self._tts = ptts.TTS(str(self.model_dir), lang="es")

    def _close(self) -> None:
        self._tts = None
        self._voices.clear()

    def _ensure_voice(self, voice: VoiceReference) -> None:
        if voice.name not in self._voices:
            self._tts.add_voice(voice.name, voice.path_or_id)
            self._voices.add(voice.name)

    def _iter_engine(self, text: str, voice: VoiceReference) -> Iterator[tuple[np.ndarray, int, int]]:
        self._ensure_voice(voice)
        with self._tts.stream(text, voice=voice.name) as audio:
            rate = audio.sample_rate
            for chunk in audio:
                yield np.asarray(chunk, dtype=np.float32).reshape(-1), rate, 1


def _with_version(d: EngineDescriptor, v: str) -> EngineDescriptor:
    from dataclasses import replace

    return replace(d, engine_version=v)

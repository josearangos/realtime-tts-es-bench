from __future__ import annotations

from importlib.metadata import version
from typing import Iterator

import numpy as np

from ..core.adapter import BaseAdapter
from ..core.descriptor import EngineDescriptor, InputLimits, StreamingInfo
from ..core.errors import EngineNotInstalledError, WeightsMissingError
from ..core.voices import VoiceReference
from .phonon import _with_version

_INSTALL = "Run: pip install -e '.[pocket]' (in its own virtual environment)."
_GATED = (
    "Voice cloning weights are gated: accept the terms at https://huggingface.co/kyutai/pocket-tts "
    "and log in locally (`hf auth login`)."
)


class PocketTTSAdapter(BaseAdapter):
    def __init__(self, language: str = "spanish") -> None:
        super().__init__()
        self.language = language
        self._model = None
        self._states: dict[str, object] = {}
        self.descriptor = EngineDescriptor(
            name="pocket_tts",
            engine_version="unknown (read at load)",
            model_id=f"hf://kyutai/pocket-tts (language={language})",
            license_code="MIT (package LICENSE file)",
            license_model="Hugging Face model card kyutai/pocket-tts (owner-verified usable)",
            license_flags=(),
            language="es",
            spanish_variant="es-CO (cloned from reference audio)",
            voice_kind="reference_audio",
            supports_cloning=True,
            streaming=StreamingInfo("chunk"),
            input_limits=InputLimits(None),
            install_hint=_INSTALL,
            weights_hint="Weights download from Hugging Face on first load; keep them cached for offline use.",
        )

    def _load(self) -> None:
        try:
            from pocket_tts import TTSModel
        except ImportError as exc:
            raise EngineNotInstalledError("pocket_tts", _INSTALL) from exc
        self.descriptor = _with_version(self.descriptor, version("pocket-tts"))
        try:
            self._model = TTSModel.load_model(language=self.language)
        except OSError as exc:  # offline / weights not cached
            raise WeightsMissingError("pocket_tts", f"{self.descriptor.weights_hint} ({exc})") from exc

    def _close(self) -> None:
        self._model = None
        self._states.clear()

    def _iter_engine(self, text: str, voice: VoiceReference) -> Iterator[tuple[np.ndarray, int, int]]:
        if voice.name not in self._states:
            try:
                self._states[voice.name] = self._model.get_state_for_audio_prompt(voice.path_or_id)
            except ValueError as exc:
                if "voice cloning" in str(exc):
                    raise WeightsMissingError("pocket_tts", _GATED) from exc
                raise
        rate = self._model.sample_rate
        for chunk in self._model.generate_audio_stream(self._states[voice.name], text):
            yield chunk.detach().cpu().numpy().astype(np.float32, copy=False).reshape(-1), rate, 1

from __future__ import annotations

from importlib.metadata import version
from pathlib import Path
from typing import Iterator

import numpy as np

from ..core.adapter import BaseAdapter
from ..core.descriptor import EngineDescriptor, InputLimits, StreamingInfo
from ..core.errors import EngineNotInstalledError, WeightsMissingError
from ..core.voices import VoiceReference
from .phonon import _with_version

_INSTALL = "Run: pip install -e '.[piper]' (in its own virtual environment)."


class PiperAdapter(BaseAdapter):
    def __init__(self) -> None:
        super().__init__()
        self._voices: dict[str, object] = {}
        self._ready = False
        self.descriptor = EngineDescriptor(
            name="piper",
            engine_version="unknown (read at load)",
            model_id="rhasspy/piper-voices es_MX-claude-high",
            license_code="GPL-3.0",
            license_model="per-voice model card (owner-verified usable)",
            license_flags=("copyleft",),
            language="es",
            spanish_variant="es-MX (closest available to es-CO; NOT Colombian)",
            voice_kind="fixed_voice",
            supports_cloning=False,
            streaming=StreamingInfo("sentence"),
            input_limits=InputLimits(None),
            install_hint=_INSTALL,
            weights_hint="Run: python3 -m piper.download_voices --download-dir cloned_voices es_MX-claude-high",
        )

    def _load(self) -> None:
        try:
            import piper  # noqa: F401
        except ImportError as exc:
            raise EngineNotInstalledError("piper", _INSTALL) from exc
        self.descriptor = _with_version(self.descriptor, version("piper-tts"))
        self._ready = True

    def _close(self) -> None:
        self._voices.clear()
        self._ready = False

    def _voice(self, ref: VoiceReference):
        if ref.name not in self._voices:
            from piper import PiperVoice

            path = Path(ref.path_or_id)
            if not path.is_file():
                raise WeightsMissingError("piper", self.descriptor.weights_hint)
            self._voices[ref.name] = PiperVoice.load(path)
        self._label(ref.name)
        return self._voices[ref.name]

    def _label(self, voice_name: str) -> None:
        """Descriptor follows the selected voice: accent and model id are per voice."""
        from dataclasses import replace

        region = voice_name.split("-")[0].replace("_", "-")  # es_MX-... -> es-MX
        self.descriptor = replace(
            self.descriptor,
            model_id=f"rhasspy/piper-voices {voice_name}",
            license_model=f"per-voice model card ({voice_name}, owner-verified usable)",
            spanish_variant=f"{region} (closest available to es-CO; NOT Colombian)",
        )

    def _iter_engine(self, text: str, voice: VoiceReference) -> Iterator[tuple[np.ndarray, int, int]]:
        for chunk in self._voice(voice).synthesize(text):
            samples = np.frombuffer(chunk.audio_int16_bytes, dtype=np.int16)
            yield samples, chunk.sample_rate, chunk.sample_channels

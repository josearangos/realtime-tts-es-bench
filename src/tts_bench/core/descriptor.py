from __future__ import annotations

from dataclasses import dataclass, field
from typing import Literal

Granularity = Literal["chunk", "sentence", "none"]
VoiceKind = Literal["catalog_name", "reference_audio", "stored_voice_file", "fixed_voice"]


@dataclass(frozen=True)
class StreamingInfo:
    """Declared (never inferred) streaming capability. `none` means TTFA is not available."""

    granularity: Granularity


@dataclass(frozen=True)
class InputLimits:
    max_chars: int | None = None


@dataclass(frozen=True)
class EngineDescriptor:
    name: str
    engine_version: str
    model_id: str
    license_code: str
    license_model: str
    license_flags: tuple[str, ...]
    language: str
    spanish_variant: str
    voice_kind: VoiceKind
    supports_cloning: bool
    streaming: StreamingInfo
    input_limits: InputLimits = field(default_factory=InputLimits)
    install_hint: str = ""
    weights_hint: str = ""

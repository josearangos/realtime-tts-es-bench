from __future__ import annotations

from dataclasses import dataclass
from typing import Protocol

from .descriptor import VoiceKind


@dataclass(frozen=True)
class VoiceReference:
    name: str
    kind: VoiceKind
    path_or_id: str


class VoiceLibrary(Protocol):
    def resolve(
        self,
        name: str,
        kind: VoiceKind | None = None,
        *,
        engine: str | None = None,
        use: str | None = None,
        content: str | None = None,
    ) -> VoiceReference: ...

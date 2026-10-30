from __future__ import annotations

import tomllib
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from .descriptor import VoiceKind
from .errors import VoiceNotFoundError


@dataclass(frozen=True)
class VoiceReference:
    name: str
    kind: VoiceKind
    path_or_id: str


class VoiceLibrary(Protocol):
    def resolve(self, name: str, kind: VoiceKind) -> VoiceReference: ...


class DirectoryVoiceLibrary:
    """Temporary library over a git-ignored directory with a `voices.toml`.

    Sections are voice kinds, keys are voice names, values are files relative to the
    directory (or plain ids, e.g. a Piper voice name, if no such file exists).
    Replaced by feature 003's library without changing any adapter.
    """

    def __init__(self, root: str | Path = "cloned_voices"):
        self.root = Path(root)
        index = self.root / "voices.toml"
        if not index.is_file():
            raise VoiceNotFoundError(f"Voice index not found: {index}")
        with index.open("rb") as f:
            self._index = tomllib.load(f)

    def resolve(self, name: str, kind: VoiceKind) -> VoiceReference:
        entry = self._index.get(kind, {}).get(name)
        if entry is None:
            known = sorted(self._index.get(kind, {}))
            raise VoiceNotFoundError(f"No {kind} voice '{name}'. Known: {known}")
        path = self.root / entry
        return VoiceReference(name, kind, str(path) if path.exists() else entry)

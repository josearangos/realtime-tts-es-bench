"""Data types for performance measurements and results files."""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any

SCHEMA_VERSION = 1


@dataclass(frozen=True)
class ChunkTiming:
    index: int
    at_ms: float
    gap_ms: float

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "ChunkTiming":
        return cls(int(d["index"]), float(d["at_ms"]), float(d["gap_ms"]))


@dataclass(frozen=True)
class Measurement:
    """One sentence in one repetition.

    `rtf` is never computed from zero audio duration (such results are `invalid`).
    Only `ok` + `steady` measurements enter summaries.

    `ttfa_ms`: null means 'not available' (granularity `none`) or not `ok`.
    `network_time_ms` is reserved for remote engines and always null in this feature.
    """

    sentence_id: str
    repetition: int  # 1-based
    phase: str  # "first_request" | "steady"
    status: str  # "ok" | "failed" | "invalid"
    error: str | None = None
    audio_seconds: float | None = None
    generation_ms: float | None = None
    rtf: float | None = None
    ttfa_ms: float | None = None
    chunks: tuple[ChunkTiming, ...] = ()
    network_time_ms: float | None = None

    def to_dict(self) -> dict:
        d = asdict(self)
        d["chunks"] = [c.to_dict() for c in self.chunks]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "Measurement":
        return cls(
            sentence_id=d["sentence_id"],
            repetition=int(d["repetition"]),
            phase=d["phase"],
            status=d["status"],
            error=d.get("error"),
            audio_seconds=d.get("audio_seconds"),
            generation_ms=d.get("generation_ms"),
            rtf=d.get("rtf"),
            ttfa_ms=d.get("ttfa_ms"),
            chunks=tuple(ChunkTiming.from_dict(c) for c in d.get("chunks", [])),
            network_time_ms=d.get("network_time_ms"),
        )


@dataclass(frozen=True)
class RunSummary:
    """Derived figures; `data` follows data-model.md (kept as a plain dict for JSON)."""

    data: dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> dict:
        return dict(self.data)

    @classmethod
    def from_dict(cls, d: dict) -> "RunSummary":
        return cls(dict(d))

    def __getitem__(self, key: str) -> Any:
        return self.data[key]

    def get(self, key: str, default: Any = None) -> Any:
        return self.data.get(key, default)


@dataclass(frozen=True)
class ResultsFile:
    environment: dict
    summary: RunSummary
    resources: dict
    measurements: tuple[Measurement, ...]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version,
            "environment": self.environment,
            "summary": self.summary.to_dict(),
            "resources": self.resources,
            "measurements": [m.to_dict() for m in self.measurements],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResultsFile":
        return cls(
            environment=d["environment"],
            summary=RunSummary.from_dict(d["summary"]),
            resources=d["resources"],
            measurements=tuple(Measurement.from_dict(m) for m in d["measurements"]),
            schema_version=int(d["schema_version"]),
        )

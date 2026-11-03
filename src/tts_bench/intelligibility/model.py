"""Data types for the intelligibility pipeline (data-model.md).

Every type serializes with `to_dict()` and loads with `from_dict()`. Every file
carries `schema_version`.
"""

from __future__ import annotations

from dataclasses import dataclass

from .align import ErrorBreakdown

SCHEMA_VERSION = 1

NOTICE = (
    "WER and CER measure intelligibility as heard by one recognizer, not naturalness; "
    "results reflect the recognizer and the engine together."
)

MANIFEST_STATUSES = ("ok", "failed", "silent")
TRANSCRIPT_STATUSES = ("ok", "skipped_silent", "skipped_failed")
FLAGS = ("silent_audio", "synthesis_failed", "empty_transcript", "empty_reference")
LANGUAGE = "es"
LOW_SAMPLE_BELOW = 10  # low_sample is true when n_sentences < 10
UNRELIABLE_ABOVE = 0.10  # reliable is false when more than 10% of sentences are flagged

ACCENT_NOTE = (
    "Recognizer accuracy varies with regional accent; a rate here mixes the engine's "
    "Spanish variant with the recognizer's coverage of it."
)


@dataclass(frozen=True)
class ManifestItem:
    sentence_id: str
    file: str | None
    status: str  # ok / failed / silent
    error: str | None = None
    sample_rate: int | None = None
    duration_s: float | None = None
    sha256: str | None = None

    def __post_init__(self) -> None:
        if self.status not in MANIFEST_STATUSES:
            raise ValueError(f"manifest status must be one of {MANIFEST_STATUSES}, got {self.status!r}")

    def to_dict(self) -> dict:
        return {
            "sentence_id": self.sentence_id, "file": self.file, "status": self.status,
            "error": self.error, "sample_rate": self.sample_rate,
            "duration_s": self.duration_s, "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ManifestItem":
        return cls(d["sentence_id"], d.get("file"), d["status"], d.get("error"),
                   d.get("sample_rate"), d.get("duration_s"), d.get("sha256"))


@dataclass(frozen=True)
class Manifest:
    engine: dict  # name, engine_version, model_id, spanish_variant, streaming_granularity, voice
    corpus: dict  # corpus_version, corpus_hash, subset, limit
    command: str
    environment: dict
    items: tuple[ManifestItem, ...]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "engine": self.engine, "corpus": self.corpus,
            "command": self.command, "environment": self.environment,
            "items": [i.to_dict() for i in self.items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Manifest":
        return cls(d["engine"], d["corpus"], d.get("command", ""), d.get("environment", {}),
                   tuple(ManifestItem.from_dict(i) for i in d["items"]), d["schema_version"])


@dataclass(frozen=True)
class Transcript:
    sentence_id: str
    audio_sha256: str | None
    status: str  # ok / skipped_silent / skipped_failed
    text: str = ""
    language: str = LANGUAGE

    def __post_init__(self) -> None:
        if self.status not in TRANSCRIPT_STATUSES:
            raise ValueError(f"transcript status must be one of {TRANSCRIPT_STATUSES}, got {self.status!r}")
        if self.language != LANGUAGE:
            raise ValueError("language is forced to 'es'")

    def to_dict(self) -> dict:
        return {"sentence_id": self.sentence_id, "audio_sha256": self.audio_sha256,
                "status": self.status, "text": self.text, "language": self.language}

    @classmethod
    def from_dict(cls, d: dict) -> "Transcript":
        return cls(d["sentence_id"], d.get("audio_sha256"), d["status"], d.get("text", ""),
                   d.get("language", LANGUAGE))


@dataclass(frozen=True)
class RecognizerRecord:
    name: str
    checkpoint: str
    license: str
    library_versions: dict
    settings: dict
    settings_hash: str
    device: str
    accent_note: str = ACCENT_NOTE
    license_flag: str | None = None  # set when the license is not permissive or unverified

    def to_dict(self) -> dict:
        return {
            "name": self.name, "checkpoint": self.checkpoint, "license": self.license,
            "license_flag": self.license_flag, "library_versions": self.library_versions,
            "settings": self.settings, "settings_hash": self.settings_hash,
            "device": self.device, "accent_note": self.accent_note,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "RecognizerRecord":
        return cls(d["name"], d["checkpoint"], d["license"], d["library_versions"], d["settings"],
                   d["settings_hash"], d["device"], d.get("accent_note", ACCENT_NOTE), d.get("license_flag"))


@dataclass(frozen=True)
class Transcripts:
    recognizer: RecognizerRecord
    engine: dict
    corpus: dict
    manifest_sha256: str
    command: str
    environment: dict
    transcripts: tuple[Transcript, ...]
    schema_version: int = SCHEMA_VERSION

    def by_id(self) -> dict[str, Transcript]:
        return {t.sentence_id: t for t in self.transcripts}

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "recognizer": self.recognizer.to_dict(),
            "engine": self.engine, "corpus": self.corpus, "manifest_sha256": self.manifest_sha256,
            "command": self.command, "environment": self.environment,
            "transcripts": [t.to_dict() for t in self.transcripts],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Transcripts":
        return cls(RecognizerRecord.from_dict(d["recognizer"]), d["engine"], d["corpus"],
                   d.get("manifest_sha256", ""), d.get("command", ""), d.get("environment", {}),
                   tuple(Transcript.from_dict(t) for t in d["transcripts"]), d["schema_version"])


@dataclass(frozen=True)
class NormalizationRecord:
    ruleset_version: str
    lexicon_version: str
    steps: tuple[str, ...]
    accent_folding: str

    def to_dict(self) -> dict:
        return {"ruleset_version": self.ruleset_version, "lexicon_version": self.lexicon_version,
                "steps": list(self.steps), "accent_folding": self.accent_folding}

    @classmethod
    def from_dict(cls, d: dict) -> "NormalizationRecord":
        return cls(d["ruleset_version"], d["lexicon_version"], tuple(d["steps"]), d["accent_folding"])


def _levels(d: dict[str, ErrorBreakdown], *, ops: bool) -> dict:
    return {k: v.to_dict(with_ops=ops and k == "word") for k, v in d.items()}


def _levels_from(d: dict) -> dict[str, ErrorBreakdown]:
    return {k: ErrorBreakdown.from_dict(v) for k, v in d.items()}


@dataclass(frozen=True)
class SentenceResult:
    sentence_id: str
    campaign: str
    tags: tuple[str, ...]
    probes: str
    reference: str
    hypothesis: str
    number_readings: tuple[str, ...]
    primary: dict[str, ErrorBreakdown]  # word, char (accents folded)
    accent_sensitive: dict[str, ErrorBreakdown]
    flags: tuple[str, ...] = ()
    counted_as_failure: bool = False

    def __post_init__(self) -> None:
        for f in self.flags:
            if f not in FLAGS:
                raise ValueError(f"unknown flag {f!r}")

    def to_dict(self) -> dict:
        return {
            "sentence_id": self.sentence_id, "campaign": self.campaign, "tags": list(self.tags),
            "probes": self.probes, "reference": self.reference, "hypothesis": self.hypothesis,
            "number_readings": list(self.number_readings),
            "primary": _levels(self.primary, ops=True),
            "accent_sensitive": _levels(self.accent_sensitive, ops=True),
            "flags": list(self.flags), "counted_as_failure": self.counted_as_failure,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "SentenceResult":
        return cls(d["sentence_id"], d["campaign"], tuple(d["tags"]), d["probes"], d["reference"],
                   d["hypothesis"], tuple(d.get("number_readings", ())), _levels_from(d["primary"]),
                   _levels_from(d["accent_sensitive"]), tuple(d.get("flags", ())),
                   d.get("counted_as_failure", False))


@dataclass(frozen=True)
class GroupSummary:
    group: str  # overall, tag:<name>, campaign:<name>, untagged
    n_sentences: int
    n_flagged: int
    reference_words: int
    reference_chars: int
    primary: dict[str, ErrorBreakdown]
    accent_sensitive: dict[str, ErrorBreakdown]

    @property
    def low_sample(self) -> bool:
        return self.n_sentences < LOW_SAMPLE_BELOW

    def to_dict(self) -> dict:
        return {
            "group": self.group, "n_sentences": self.n_sentences, "n_flagged": self.n_flagged,
            "reference_words": self.reference_words, "reference_chars": self.reference_chars,
            "primary": _levels(self.primary, ops=False),
            "accent_sensitive": _levels(self.accent_sensitive, ops=False),
            "low_sample": self.low_sample,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GroupSummary":
        return cls(d["group"], d["n_sentences"], d["n_flagged"], d["reference_words"],
                   d["reference_chars"], _levels_from(d["primary"]), _levels_from(d["accent_sensitive"]))


@dataclass(frozen=True)
class ResultsFile:
    recognizer: RecognizerRecord
    normalization: NormalizationRecord
    engine: dict
    corpus: dict
    environment: dict
    command: str
    reliable: bool
    groups: tuple[GroupSummary, ...]
    sentences: tuple[SentenceResult, ...]
    notice: str = NOTICE
    schema_version: int = SCHEMA_VERSION

    def group(self, name: str) -> GroupSummary | None:
        return next((g for g in self.groups if g.group == name), None)

    @property
    def overall(self) -> GroupSummary:
        return self.group("overall")  # type: ignore[return-value]

    def summary_dict(self) -> dict:
        return {"reliable": self.reliable, "groups": [g.to_dict() for g in self.groups]}

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "notice": self.notice,
            "recognizer": self.recognizer.to_dict(), "normalization": self.normalization.to_dict(),
            "engine": self.engine, "corpus": self.corpus, "environment": self.environment,
            "command": self.command, "summary": self.summary_dict(),
            "sentences": [s.to_dict() for s in self.sentences],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResultsFile":
        return cls(
            RecognizerRecord.from_dict(d["recognizer"]), NormalizationRecord.from_dict(d["normalization"]),
            d["engine"], d["corpus"], d.get("environment", {}), d.get("command", ""),
            d["summary"]["reliable"], tuple(GroupSummary.from_dict(g) for g in d["summary"]["groups"]),
            tuple(SentenceResult.from_dict(s) for s in d["sentences"]), d.get("notice", NOTICE),
            d["schema_version"],
        )

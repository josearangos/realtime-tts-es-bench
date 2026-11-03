"""Data types for the speaker similarity pipeline (data-model.md).

Every type serializes with `to_dict()` and loads with `from_dict()`. Every file carries
`schema_version`. `ResultsFile` has no field able to hold a vector, an audio path or an
absolute path (Constitution Principle VI).
"""

from __future__ import annotations

from dataclasses import dataclass, field

SCHEMA_VERSION = 1

NOTICE = (
    "Speaker similarity scores come from one embedding model and are not a substitute for "
    "human judgment; a score near 1 does not guarantee the voice sounds identical."
)
LIMITATION_NOTE = (
    "Embeddings capture channel, noise and prosody as well as voice; the model is trained on "
    "English-dominant celebrity speech, so Spanish (es-CO) scores need the EER check; "
    "similarity near 1 is not identity."
)
SHORT_AUDIO_S = 3.0
AUDIO_LANGUAGE = "es"

MANIFEST_STATUSES = ("ok", "failed", "silent")
SUMMARY_STATUSES = ("scored", "not_applicable")
FLAGS = ("short_audio", "silent_audio", "synthesis_failed", "embedding_failed")
EXCLUDING_FLAGS = ("silent_audio", "synthesis_failed", "embedding_failed")
CV_REASONS = ("near_zero_mean", "fewer_than_two")
SUBSET = "cloning"


@dataclass(frozen=True)
class ReferenceQuality:
    recording_id: str
    duration_s: float
    speech_seconds: float
    snr_estimate_db: float
    accent: str
    warnings: tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "recording_id": self.recording_id, "duration_s": self.duration_s,
            "speech_seconds": self.speech_seconds, "snr_estimate_db": self.snr_estimate_db,
            "accent": self.accent, "warnings": list(self.warnings),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ReferenceQuality":
        return cls(d["recording_id"], d["duration_s"], d["speech_seconds"], d["snr_estimate_db"],
                   d["accent"], tuple(d.get("warnings", ())))


@dataclass(frozen=True)
class ManifestItem:
    sentence_id: str
    repetition: int
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
            "sentence_id": self.sentence_id, "repetition": self.repetition, "file": self.file,
            "status": self.status, "error": self.error, "sample_rate": self.sample_rate,
            "duration_s": self.duration_s, "sha256": self.sha256,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ManifestItem":
        return cls(d["sentence_id"], d["repetition"], d.get("file"), d["status"], d.get("error"),
                   d.get("sample_rate"), d.get("duration_s"), d.get("sha256"))


@dataclass(frozen=True)
class Manifest:
    engine: dict  # name, engine_version, model_id, spanish_variant, supports_cloning, voice
    corpus: dict  # corpus_version, corpus_hash, subset, limit
    repetitions: int
    designated_repetition: int
    reference: ReferenceQuality
    command: str
    environment: dict
    items: tuple[ManifestItem, ...]
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "engine": self.engine, "corpus": self.corpus,
            "repetitions": {"n": self.repetitions, "designated": self.designated_repetition},
            "reference": self.reference.to_dict(), "command": self.command,
            "environment": self.environment, "items": [i.to_dict() for i in self.items],
        }

    @classmethod
    def from_dict(cls, d: dict) -> "Manifest":
        return cls(d["engine"], d["corpus"], d["repetitions"]["n"], d["repetitions"]["designated"],
                   ReferenceQuality.from_dict(d["reference"]), d.get("command", ""),
                   d.get("environment", {}), tuple(ManifestItem.from_dict(i) for i in d["items"]),
                   d["schema_version"])


@dataclass(frozen=True)
class EmbedderRecord:
    name: str
    checkpoint: str
    license: str
    library_versions: dict
    settings: dict
    settings_hash: str
    device: str = "cpu"
    limitation_note: str = LIMITATION_NOTE
    training_data_note: str = ""

    def to_dict(self) -> dict:
        return {
            "name": self.name, "checkpoint": self.checkpoint, "license": self.license,
            "library_versions": self.library_versions, "settings": self.settings,
            "settings_hash": self.settings_hash, "device": self.device,
            "limitation_note": self.limitation_note, "training_data_note": self.training_data_note,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmbedderRecord":
        return cls(d["name"], d["checkpoint"], d["license"], d["library_versions"], d["settings"],
                   d["settings_hash"], d.get("device", "cpu"), d.get("limitation_note", ""),
                   d.get("training_data_note", ""))


@dataclass(frozen=True)
class ClipEmbedding:
    sentence_id: str
    repetition: int
    audio_sha256: str | None
    duration_s: float | None
    vector: tuple[float, ...] | None
    status: str  # ok / failed / silent (from the manifest)

    def to_dict(self) -> dict:
        return {
            "sentence_id": self.sentence_id, "repetition": self.repetition,
            "audio_sha256": self.audio_sha256, "duration_s": self.duration_s,
            "vector": None if self.vector is None else list(self.vector), "status": self.status,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ClipEmbedding":
        v = d.get("vector")
        return cls(d["sentence_id"], d["repetition"], d.get("audio_sha256"), d.get("duration_s"),
                   None if v is None else tuple(v), d["status"])


@dataclass(frozen=True)
class ExtraEmbedding:
    label: str
    role: str  # other_voice_reference
    audio_sha256: str
    vector: tuple[float, ...]

    def to_dict(self) -> dict:
        return {"label": self.label, "role": self.role, "audio_sha256": self.audio_sha256,
                "vector": list(self.vector)}

    @classmethod
    def from_dict(cls, d: dict) -> "ExtraEmbedding":
        return cls(d["label"], d["role"], d["audio_sha256"], tuple(d["vector"]))


@dataclass(frozen=True)
class EmbeddingsFile:
    """Voice-derived data: stays under git-ignored `output/speaker/`, never in `results/`."""

    embedder: EmbedderRecord
    engine: dict
    corpus: dict
    repetitions: int
    designated_repetition: int
    reference_quality: ReferenceQuality
    reference_sha256: str
    reference_vector: tuple[float, ...]
    clips: tuple[ClipEmbedding, ...]
    extras: tuple[ExtraEmbedding, ...] = ()
    command: str = ""
    environment: dict = field(default_factory=dict)
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "embedder": self.embedder.to_dict(),
            "engine": self.engine, "corpus": self.corpus,
            "repetitions": {"n": self.repetitions, "designated": self.designated_repetition},
            "reference_quality": self.reference_quality.to_dict(),
            "reference": {"audio_sha256": self.reference_sha256, "vector": list(self.reference_vector)},
            "clips": [c.to_dict() for c in self.clips], "extras": [e.to_dict() for e in self.extras],
            "command": self.command, "environment": self.environment,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "EmbeddingsFile":
        return cls(
            EmbedderRecord.from_dict(d["embedder"]), d["engine"], d["corpus"],
            d["repetitions"]["n"], d["repetitions"]["designated"],
            ReferenceQuality.from_dict(d["reference_quality"]), d["reference"]["audio_sha256"],
            tuple(d["reference"]["vector"]), tuple(ClipEmbedding.from_dict(c) for c in d["clips"]),
            tuple(ExtraEmbedding.from_dict(e) for e in d.get("extras", ())),
            d.get("command", ""), d.get("environment", {}), d["schema_version"])


@dataclass(frozen=True)
class SimilarityScore:
    sentence_id: str
    campaign: str
    tags: tuple[str, ...]
    similarity: float | None
    duration_s: float | None
    flags: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        bad = [f for f in self.flags if f not in FLAGS]
        if bad:
            raise ValueError(f"unknown flag(s) {bad}; allowed: {FLAGS}")

    def to_dict(self) -> dict:
        return {"sentence_id": self.sentence_id, "campaign": self.campaign, "tags": list(self.tags),
                "similarity": self.similarity, "duration_s": self.duration_s, "flags": list(self.flags)}

    @classmethod
    def from_dict(cls, d: dict) -> "SimilarityScore":
        return cls(d["sentence_id"], d["campaign"], tuple(d["tags"]), d["similarity"],
                   d["duration_s"], tuple(d["flags"]))


@dataclass(frozen=True)
class EngineSummary:
    status: str  # scored / not_applicable
    n_sentences: int = 0
    n_scored: int = 0
    n_flagged: int = 0  # sentences excluded from the mean (silent, failed, embedding failed)
    n_short_audio: int = 0  # scored clips shorter than 3.0 s
    similarity: dict | None = None  # mean, sd, min, max
    warnings: tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if self.status not in SUMMARY_STATUSES:
            raise ValueError(f"summary status must be one of {SUMMARY_STATUSES}, got {self.status!r}")

    def to_dict(self) -> dict:
        return {"status": self.status, "n_sentences": self.n_sentences, "n_scored": self.n_scored,
                "n_flagged": self.n_flagged, "n_short_audio": self.n_short_audio,
                "similarity": self.similarity, "warnings": list(self.warnings)}

    @classmethod
    def from_dict(cls, d: dict) -> "EngineSummary":
        return cls(d["status"], d["n_sentences"], d["n_scored"], d["n_flagged"],
                   d.get("n_short_audio", 0), d.get("similarity"), tuple(d.get("warnings", ())))


@dataclass(frozen=True)
class ConsistencyRecord:
    repetitions: int
    duration: dict  # cv_median, cv_mean, n_sentences_valid, n_declined, n_unavailable
    similarity: dict
    per_sentence: tuple[dict, ...]  # sentence_id, n, duration_cv, similarity_cv, *_reason, reason

    def to_dict(self) -> dict:
        return {"repetitions": self.repetitions, "duration": self.duration,
                "similarity": self.similarity, "per_sentence": list(self.per_sentence)}

    @classmethod
    def from_dict(cls, d: dict) -> "ConsistencyRecord":
        return cls(d["repetitions"], d["duration"], d["similarity"], tuple(d["per_sentence"]))


@dataclass(frozen=True)
class EERRecord:
    available: bool
    eer: float | None
    threshold: float | None
    n_same: int
    n_different: int
    high_eer_warning: bool
    separation: float | None
    gate_passed: bool
    reason: str | None
    pair_construction: str

    def to_dict(self) -> dict:
        return {"available": self.available, "eer": self.eer, "threshold": self.threshold,
                "n_same": self.n_same, "n_different": self.n_different,
                "high_eer_warning": self.high_eer_warning, "separation": self.separation,
                "gate_passed": self.gate_passed, "reason": self.reason,
                "pair_construction": self.pair_construction}

    @classmethod
    def from_dict(cls, d: dict) -> "EERRecord":
        return cls(d["available"], d["eer"], d["threshold"], d["n_same"], d["n_different"],
                   d["high_eer_warning"], d["separation"], d["gate_passed"], d["reason"],
                   d["pair_construction"])


@dataclass(frozen=True)
class ResultsFile:
    embedder: EmbedderRecord
    reference_quality: ReferenceQuality
    engine: dict
    corpus: dict
    environment: dict
    command: str
    summary: EngineSummary
    sentences: tuple[SimilarityScore, ...]
    consistency: ConsistencyRecord | None
    eer: EERRecord | None = None
    audio_language: str = AUDIO_LANGUAGE
    notice: str = NOTICE
    schema_version: int = SCHEMA_VERSION

    def to_dict(self) -> dict:
        return {
            "schema_version": self.schema_version, "notice": self.notice,
            "audio_language": self.audio_language, "embedder": self.embedder.to_dict(),
            "reference_quality": self.reference_quality.to_dict(), "engine": self.engine,
            "corpus": self.corpus, "environment": self.environment, "command": self.command,
            "summary": self.summary.to_dict(), "sentences": [s.to_dict() for s in self.sentences],
            "consistency": None if self.consistency is None else self.consistency.to_dict(),
            "eer": None if self.eer is None else self.eer.to_dict(),
        }

    @classmethod
    def from_dict(cls, d: dict) -> "ResultsFile":
        return cls(
            EmbedderRecord.from_dict(d["embedder"]), ReferenceQuality.from_dict(d["reference_quality"]),
            d["engine"], d["corpus"], d.get("environment", {}), d.get("command", ""),
            EngineSummary.from_dict(d["summary"]),
            tuple(SimilarityScore.from_dict(s) for s in d["sentences"]),
            None if d.get("consistency") is None else ConsistencyRecord.from_dict(d["consistency"]),
            None if d.get("eer") is None else EERRecord.from_dict(d["eer"]),
            d.get("audio_language", AUDIO_LANGUAGE), d.get("notice", NOTICE), d["schema_version"])

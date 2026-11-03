"""Labeled same-speaker and different-speaker pairs from the project's own Spanish audio (research R5)."""

from __future__ import annotations

from .eer import equal_error_rate
from .model import EERRecord, EmbeddingsFile
from .similarity import ZeroNormError, cosine_similarity

NEEDS_OTHER_VOICE = "at least one other voice is needed"

PAIR_CONSTRUCTION = (
    "Same-speaker pairs: a voice's reference against each of its cloned clips of the designated run. "
    "Different-speaker pairs: that reference against the other consented voice's reference and clips "
    "(and its extra reference vectors). Pooled across cloning engines. With two speakers the EER "
    "measures the separation of those two voices only, and cloned clips are not natural recordings, "
    "so it is a sanity check on Spanish audio, not a general model evaluation."
)


def _voice(f: EmbeddingsFile) -> str:
    return f.reference_quality.recording_id


def build_pairs(files: list[EmbeddingsFile]) -> tuple[list[float], list[float], str]:
    """-> (same_scores, different_scores, description). Only scores leave this function."""
    same: list[float] = []
    diff: list[float] = []
    seen: set[tuple[str, str]] = set()

    def add_diff(f: EmbeddingsFile, source_id: str, vector) -> None:
        key = (f.reference_sha256, source_id)
        if key in seen:
            return
        try:
            score = cosine_similarity(f.reference_vector, vector)
        except ZeroNormError:
            return
        seen.add(key)
        diff.append(score)

    for f in files:
        for c in f.clips:
            if c.repetition != f.designated_repetition or c.status != "ok" or c.vector is None:
                continue
            try:
                same.append(cosine_similarity(f.reference_vector, c.vector))
            except ZeroNormError:
                continue
        for e in f.extras:
            add_diff(f, f"ref:{e.audio_sha256}", e.vector)  # same id as a pooled file's reference
        for g in files:
            if _voice(g) == _voice(f):
                continue
            add_diff(f, f"ref:{g.reference_sha256}", g.reference_vector)
            for c in g.clips:
                if c.repetition == g.designated_repetition and c.status == "ok" and c.vector is not None:
                    add_diff(f, f"clip:{c.audio_sha256}", c.vector)
    return same, diff, PAIR_CONSTRUCTION


def compute_eer(files: list[EmbeddingsFile]) -> EERRecord:
    """One EER record for a set of embeddings files (pooled across engines)."""
    same, diff, description = build_pairs(files)
    if not diff:
        return EERRecord(False, None, None, len(same), 0, False, None, False, NEEDS_OTHER_VOICE, description)
    return equal_error_rate(same, diff, pair_construction=description)

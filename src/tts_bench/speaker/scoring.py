"""Score an embeddings file: similarity per sentence and per engine, consistency, warnings (pure).

Imports numpy and the standard library only: no engine, no model, no network (FR-010).
"""

from __future__ import annotations

import statistics

from ..corpus import Corpus
from .model import (
    NOTICE, SHORT_AUDIO_S, ConsistencyRecord, EERRecord, EmbeddingsFile, EngineSummary, ResultsFile,
    SimilarityScore,
)
from .similarity import ZeroNormError, cosine_similarity
from .variation import coefficient_of_variation


def _similarity(reference, clip) -> tuple[float | None, str | None]:
    """-> (similarity, flag). A zero-norm embedding is a failure flag, never a score."""
    if clip is None or clip.status == "failed":
        return None, "synthesis_failed"
    if clip.status == "silent":
        return None, "silent_audio"
    if clip.vector is None:
        return None, "embedding_failed"
    try:
        return cosine_similarity(reference, clip.vector), None
    except ZeroNormError:
        return None, "embedding_failed"


def _stats(values: list[float]) -> dict | None:
    if not values:
        return None
    return {
        "mean": statistics.fmean(values),
        "sd": statistics.stdev(values) if len(values) > 1 else None,
        "min": min(values),
        "max": max(values),
    }


def _aggregate(cvs: list) -> dict:
    valid = [c.value for c in cvs if c.status == "ok"]
    return {
        "cv_median": statistics.median(valid) if valid else None,
        "cv_mean": statistics.fmean(valid) if valid else None,
        "n_sentences_valid": len(valid),
        "n_declined": sum(1 for c in cvs if c.status == "near_zero_mean"),
        "n_unavailable": sum(1 for c in cvs if c.status == "fewer_than_two"),
    }


def _consistency(emb: EmbeddingsFile, sentences) -> ConsistencyRecord:
    """From every repetition of each sentence; failed and silent repetitions are left out."""
    by_sentence: dict[str, list] = {}
    for c in emb.clips:
        by_sentence.setdefault(c.sentence_id, []).append(c)
    rows, dur_cvs, sim_cvs = [], [], []
    for s in sentences:
        clips = sorted((c for c in by_sentence.get(s.id, []) if c.status == "ok"), key=lambda c: c.repetition)
        durations = [c.duration_s for c in clips if c.duration_s is not None]
        sims = [v for v in (_similarity(emb.reference_vector, c)[0] for c in clips) if v is not None]
        d, m = coefficient_of_variation(durations), coefficient_of_variation(sims)
        dur_cvs.append(d)
        sim_cvs.append(m)
        rows.append({
            "sentence_id": s.id, "n": len(clips), "duration_cv": d.value, "similarity_cv": m.value,
            "duration_reason": d.reason, "similarity_reason": m.reason,
            "reason": m.reason or d.reason,
        })
    return ConsistencyRecord(emb.repetitions, _aggregate(dur_cvs), _aggregate(sim_cvs), tuple(rows))


def score_embeddings(emb: EmbeddingsFile, corpus: Corpus, *, command: str = "",
                     environment: dict | None = None, eer: EERRecord | None = None) -> ResultsFile:
    """Per-sentence similarity (designated repetition only), engine summary and consistency.

    The headline similarity uses only the designated repetition; all repetitions feed consistency.
    """
    env = environment if environment is not None else {}
    engine = emb.engine
    limit = emb.corpus.get("limit")
    sentences = corpus.sentences[:limit] if limit is not None else corpus.sentences
    if not engine.get("supports_cloning", True):
        return ResultsFile(emb.embedder, emb.reference_quality, engine, emb.corpus, env, command,
                           EngineSummary("not_applicable"), (), None, eer)
    designated = {c.sentence_id: c for c in emb.clips if c.repetition == emb.designated_repetition}
    scores, values, n_short = [], [], 0
    for s in sentences:
        clip = designated.get(s.id)
        sim, flag = _similarity(emb.reference_vector, clip)
        flags = [flag] if flag else []
        if sim is not None:
            values.append(sim)
            if clip.duration_s is not None and clip.duration_s < SHORT_AUDIO_S:
                flags.append("short_audio")
                n_short += 1
        scores.append(SimilarityScore(
            s.id, s.campaign.value, tuple(t.value for t in s.tags), sim,
            None if clip is None else clip.duration_s, tuple(flags)))
    n_flagged = len(sentences) - len(values)
    warnings = []
    if n_short:
        warnings.append(f"{n_short} clip(s) shorter than {SHORT_AUDIO_S} s: speaker embeddings of short "
                        "audio are less reliable (kept in the average)")
    if n_flagged:
        warnings.append(f"{n_flagged} sentence(s) excluded from the average (silent, failed or unusable embedding)")
    summary = EngineSummary("scored", len(sentences), len(values), n_flagged, n_short, _stats(values),
                            tuple(warnings))
    return ResultsFile(emb.embedder, emb.reference_quality, engine, emb.corpus, env, command, summary,
                       tuple(scores), _consistency(emb, sentences), eer, notice=NOTICE)

"""Per-sentence and pooled WER/CER from fixed transcripts (pure; no engine, no recognizer)."""

from __future__ import annotations

from ..corpus import Corpus
from .align import ErrorBreakdown, char_error_rate, word_error_rate
from .lexicon import LEXICON_VERSION
from .model import (
    NOTICE, GroupSummary, NormalizationRecord, ResultsFile, SentenceResult,
    Transcript, Transcripts,
)
from .normalize import RULESET_VERSION, STEPS, normalize, normalize_pair

ACCENT_FOLDING = "primary folds á é í ó ú ü (ñ kept); accent_sensitive keeps every accent"


def _score_text(reference: str, transcript: str | None, fold: bool):
    """-> (ref_norm, hyp_norm, readings, word, char). transcript None = full failure."""
    if transcript is None:
        ref_n = normalize(reference, fold_accents=fold)
        return (ref_n, "", [], ErrorBreakdown.full_failure(ref_n.split()),
                ErrorBreakdown.full_failure(ref_n))
    ref_n, hyp_n, readings = normalize_pair(reference, transcript, fold_accents=fold)
    return ref_n, hyp_n, readings, word_error_rate(ref_n, hyp_n), char_error_rate(ref_n, hyp_n)


def score_sentence(sentence, transcript: Transcript | None) -> SentenceResult:
    reference = sentence.spoken if sentence.spoken is not None else sentence.text
    flags: list[str] = []
    failure = transcript is None or transcript.status != "ok"
    if transcript is not None and transcript.status == "skipped_silent":
        flags.append("silent_audio")
    elif failure:
        flags.append("synthesis_failed")
    text = None if failure else transcript.text  # type: ignore[union-attr]
    ref_n, hyp_n, readings, word, char = _score_text(reference, text, True)
    _, _, _, word_a, char_a = _score_text(reference, text, False)
    if not ref_n:
        flags.append("empty_reference")
    if not failure and not hyp_n and ref_n:
        flags.append("empty_transcript")
    return SentenceResult(
        sentence_id=sentence.id, campaign=sentence.campaign.value,
        tags=tuple(t.value for t in sentence.tags), probes=sentence.probes.value,
        reference=ref_n, hypothesis=hyp_n, number_readings=tuple(readings),
        primary={"word": word, "char": char}, accent_sensitive={"word": word_a, "char": char_a},
        flags=tuple(flags), counted_as_failure=failure,
    )


def _group(name: str, results: list[SentenceResult]) -> GroupSummary:
    scored = [r for r in results if "empty_reference" not in r.flags]  # excluded from pooled rates

    def pooled(kind: str, level: str) -> ErrorBreakdown:
        return ErrorBreakdown.pooled(getattr(r, kind)[level] for r in scored)

    primary = {lv: pooled("primary", lv) for lv in ("word", "char")}
    return GroupSummary(
        group=name, n_sentences=len(results), n_flagged=sum(1 for r in results if r.flags),
        reference_words=primary["word"].reference_length, reference_chars=primary["char"].reference_length,
        primary=primary, accent_sensitive={lv: pooled("accent_sensitive", lv) for lv in ("word", "char")},
    )


def build_groups(results: list[SentenceResult]) -> list[GroupSummary]:
    groups = [_group("overall", results)]
    for c in sorted({r.campaign for r in results}):
        groups.append(_group(f"campaign:{c}", [r for r in results if r.campaign == c]))
    for t in sorted({t for r in results for t in r.tags}):
        groups.append(_group(f"tag:{t}", [r for r in results if t in r.tags]))
    untagged = [r for r in results if not r.tags]
    if untagged:
        groups.append(_group("untagged", untagged))
    return groups


def score_transcripts(
    transcripts: Transcripts, corpus: Corpus, *, recognizer=None, engine: dict | None = None,
    command: str = "", environment: dict | None = None,
) -> ResultsFile:
    """Score every sentence of `corpus` against its transcript. A sentence with no transcript
    is a full failure. `recognizer` and `engine` default to those recorded with the transcripts."""
    by_id = transcripts.by_id()
    results = [score_sentence(s, by_id.get(s.id)) for s in corpus.sentences]
    groups = build_groups(results)
    flagged = sum(1 for r in results if r.flags)
    return ResultsFile(
        recognizer=recognizer or transcripts.recognizer,
        normalization=NormalizationRecord(RULESET_VERSION, LEXICON_VERSION, tuple(STEPS), ACCENT_FOLDING),
        engine=engine or transcripts.engine,
        corpus=transcripts.corpus,
        environment=environment if environment is not None else transcripts.environment,
        command=command, reliable=not (results and flagged * 10 > len(results)),
        groups=tuple(groups), sentences=tuple(results), notice=NOTICE,
    )

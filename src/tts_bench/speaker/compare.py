"""Merge results files into Markdown tables (pure)."""

from __future__ import annotations

from .model import NOTICE, ResultsFile

CAUTION = "similarity scores should be interpreted cautiously"


class MergeRefused(Exception):
    """Results made with different embedders, settings, corpus or references cannot be merged."""

    def __init__(self, field: str, values: list) -> None:
        super().__init__(f"results differ in {field}: {values}")
        self.field = field


def _guards(r: ResultsFile) -> dict:
    return {
        "embedder name": r.embedder.name,
        "embedder checkpoint": r.embedder.checkpoint,
        "embedder settings": r.embedder.settings,
        "embedder settings_hash": r.embedder.settings_hash,
        "corpus_hash": r.corpus.get("corpus_hash"),
        "corpus subset": r.corpus.get("subset"),
        "reference recording_id": r.reference_quality.recording_id,
    }


def check_mergeable(results: list[ResultsFile]) -> None:
    """Raise MergeRefused naming the first differing field (FR-002). Hardware may differ."""
    scored = [r for r in results if r.summary.status == "scored"]
    for field in _guards(scored[0]) if scored else ():
        values = [_guards(r)[field] for r in scored]
        if any(v != values[0] for v in values[1:]):
            raise MergeRefused(field, values)


def _num(x, nd=3) -> str:
    return "n/a" if x is None else f"{x:.{nd}f}"


def _cv_cell(block: dict) -> str:
    if block["n_sentences_valid"]:
        return f"{_num(block['cv_median'])} / {_num(block['cv_mean'])}"
    if block["n_declined"]:
        return "declined (unreliable)"
    return "not available"


def not_reliable(results: list[ResultsFile]) -> bool:
    return any(r.eer is not None and r.eer.available and (r.eer.high_eer_warning or not r.eer.gate_passed)
               for r in results)


def compare_results(results: list[ResultsFile]) -> str:
    check_mergeable(results)
    lines = [f"> {NOTICE}", ""]
    eer = next((r.eer for r in results if r.eer is not None), None)
    if not_reliable(results):
        lines += [f"> **Not reliable for ranking:** {CAUTION}; the Spanish speaker-verification check failed.", ""]
    elif eer is None or not eer.available:
        lines += ["> The EER check on the project's Spanish audio has not been run (or was not available); "
                  "it is required before these scores are trusted.", ""]
    scored = [r for r in results if r.summary.status == "scored"]
    first = scored[0] if scored else None
    if first:
        e = first.embedder
        lines += [f"Embedding model: `{e.name}` ({e.checkpoint}); settings hash `{e.settings_hash}`; "
                  f"audio language `{first.audio_language}`. Corpus subset `{first.corpus.get('subset')}` "
                  f"(`{first.corpus.get('corpus_hash')}`). Reference `{first.reference_quality.recording_id}` "
                  f"({first.reference_quality.accent}, {first.reference_quality.duration_s} s, "
                  f"SNR {first.reference_quality.snr_estimate_db} dB).", ""]
    lines += ["## Similarity to the reference (designated run)", "",
              "| Engine | Voice | Mean | SD | Min | Max | Scored | Flagged | Warnings |",
              "|---|---|---|---|---|---|---|---|---|"]
    for r in results:
        name, voice = r.engine["name"], r.engine.get("voice", {}).get("name", "")
        s = r.summary
        if s.status != "scored":
            lines.append(f"| {name} | {voice} | not applicable | | | | | | does not clone voices |")
            continue
        st = s.similarity or {}
        lines.append(f"| {name} | {voice} | {_num(st.get('mean'))} | {_num(st.get('sd'))} | {_num(st.get('min'))} "
                     f"| {_num(st.get('max'))} | {s.n_scored}/{s.n_sentences} | {s.n_flagged} | "
                     f"{'; '.join(s.warnings) or '-'} |")
    consist = [r for r in scored if r.consistency is not None]
    if consist:
        lines += ["", "## Consistency across repetitions (coefficient of variation, median / mean over sentences)", "",
                  "| Engine | Repetitions | Duration CV | Similarity CV | Declined | Unavailable |",
                  "|---|---|---|---|---|---|"]
        for r in consist:
            c = r.consistency
            lines.append(f"| {r.engine['name']} | {c.repetitions} | {_cv_cell(c.duration)} | {_cv_cell(c.similarity)} "
                         f"| {c.duration['n_declined'] + c.similarity['n_declined']} "
                         f"| {c.duration['n_unavailable'] + c.similarity['n_unavailable']} |")
    if eer is not None:
        lines += ["", "## Speaker-verification check (EER on the project's Spanish audio)", ""]
        if eer.available:
            lines += [f"- EER: {_num(eer.eer, 4)} at threshold {_num(eer.threshold)} "
                      f"({eer.n_same} same-speaker and {eer.n_different} different-speaker pairs)",
                      f"- Separation (mean same minus mean different): {_num(eer.separation)}",
                      f"- Spanish gate (EER <= 10% and separation >= 0.20): "
                      f"{'passed' if eer.gate_passed else 'FAILED'}"]
            if eer.high_eer_warning:
                lines.append(f"- Warning: EER above 10%; {CAUTION}.")
        else:
            lines.append(f"- not available: {eer.reason}")
        lines += [f"- Pairs: {eer.pair_construction}",
                  "- The audio is es-CO and the model is trained mostly on English-dominant data, so this check on "
                  "the project's own Spanish pairs is the acceptance test for the scores above."]
    return "\n".join(lines) + "\n"

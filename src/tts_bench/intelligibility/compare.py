"""Merge results files into Markdown tables, and the per-sentence error report."""

from __future__ import annotations

from .files import read_results
from .model import NOTICE, ResultsFile


class MixedResultsError(Exception):
    """Results cannot be compared; `field` names the first differing field."""

    def __init__(self, field: str, detail: str = "") -> None:
        self.field = field
        super().__init__(f"results differ in {field}" + (f" ({detail})" if detail else "")
                         + "; WER is only comparable with the same recognizer, settings, ruleset and corpus")


def _check_same(files: list[ResultsFile]) -> None:
    base = files[0]
    for other in files[1:]:
        pairs = [
            ("recognizer.name", base.recognizer.name, other.recognizer.name),
            ("recognizer.checkpoint", base.recognizer.checkpoint, other.recognizer.checkpoint),
            ("recognizer.library_versions", base.recognizer.library_versions, other.recognizer.library_versions),
        ]
        for key in sorted(set(base.recognizer.settings) | set(other.recognizer.settings)):
            pairs.append((f"recognizer.settings.{key}", base.recognizer.settings.get(key),
                          other.recognizer.settings.get(key)))
        pairs += [
            ("normalization.ruleset_version", base.normalization.ruleset_version, other.normalization.ruleset_version),
            ("normalization.lexicon_version", base.normalization.lexicon_version, other.normalization.lexicon_version),
        ]
        for key in ("corpus_hash", "subset", "limit"):
            pairs.append((f"corpus.{key}", base.corpus.get(key), other.corpus.get(key)))
        for name, a, b in pairs:
            if a != b:
                raise MixedResultsError(name, f"{a!r} vs {b!r}")


def pct(rate) -> str:
    return "n/a" if rate is None else f"{rate * 100:.1f}%"


def _voice(r: ResultsFile) -> str:
    return (r.engine.get("voice") or {}).get("name") or "-"


_HEAD_OVERALL = ("engine", "voice", "WER", "CER", "S", "D", "I", "accent-sensitive WER",
                 "n sentences", "flagged", "reliable")
_HEAD_GROUP = ("engine", "group", "n sentences", "reference words", "WER", "CER", "S", "D", "I",
               "accent-sensitive WER", "low sample")


def _table(head, rows) -> list[str]:
    lines = ["| " + " | ".join(head) + " |", "|" + "|".join("---" for _ in head) + "|"]
    lines += ["| " + " | ".join(str(c) for c in row) + " |" for row in rows]
    return lines


def _group_row(r: ResultsFile, g) -> tuple:
    w = g.primary["word"]
    return (r.engine["name"], g.group, g.n_sentences, g.reference_words, pct(w.rate),
            pct(g.primary["char"].rate), w.substitutions, w.deletions, w.insertions,
            pct(g.accent_sensitive["word"].rate), "yes" if g.low_sample else "no")


def compare_results(files, *, notice: str = NOTICE) -> str:
    """Markdown comparison of results files. Refuses (MixedResultsError) when the recognizer,
    its settings, the ruleset versions or the corpus differ; hardware differences are listed."""
    results = [f if isinstance(f, ResultsFile) else read_results(f) for f in files]
    if not results:
        raise ValueError("compare needs at least one results file")
    _check_same(results)
    base = results[0]
    out = [f"> {notice}", ""]
    rec = base.recognizer
    out += [f"Recognizer: {rec.name} {rec.checkpoint} ({rec.device}), ruleset "
            f"{base.normalization.ruleset_version}, lexicon {base.normalization.lexicon_version}, "
            f"corpus {base.corpus.get('corpus_version')} subset {base.corpus.get('subset')} "
            f"limit {base.corpus.get('limit')}.",
            f"Sampling variance across syntheses is not measured (one synthesis per sentence). "
            f"{rec.accent_note}", ""]
    rows = []
    for r in results:
        o = r.overall
        w = o.primary["word"]
        rows.append((r.engine["name"], _voice(r), pct(w.rate), pct(o.primary["char"].rate),
                     w.substitutions, w.deletions, w.insertions, pct(o.accent_sensitive["word"].rate),
                     o.n_sentences, o.n_flagged, "yes" if r.reliable else "NO"))
    out += ["## Overall", "", *_table(_HEAD_OVERALL, rows), ""]
    for title, prefix in (("Per tag", "tag:"), ("Per campaign", "campaign:")):
        names = sorted({g.group for r in results for g in r.groups if g.group.startswith(prefix)})
        if prefix == "tag:" and any(r.group("untagged") for r in results):
            names.append("untagged")
        rows = [_group_row(r, r.group(n)) for n in names for r in results if r.group(n)]
        out += [f"## {title}", "", *_table(_HEAD_GROUP, rows), ""]
        if prefix == "tag:":
            out += ["Tag groups overlap: a sentence with several tags is counted in each of them, "
                    "so group rows do not add up to the overall row.", ""]
    hw = {(r.environment.get("os_name"), r.environment.get("os_release")) for r in results}
    if len(hw) > 1:
        out += ["Environments differ (not blocking, WER is not a timing metric): "
                + "; ".join(sorted(f"{a} {b}" for a, b in hw)), ""]
    return "\n".join(out).rstrip() + "\n"


def error_report(results: ResultsFile, *, sentence: str | None = None, tag: str | None = None,
                 worst: int | None = None) -> str:
    """Per-sentence substitutions, deletions and insertions with the words involved."""
    sel = list(results.sentences)
    if sentence is not None:
        sel = [s for s in sel if s.sentence_id == sentence]
    else:
        sel = [s for s in sel if s.primary["word"].errors > 0]
    if tag is not None:
        sel = [s for s in sel if tag in s.tags]
    sel.sort(key=lambda s: ((-s.primary["word"].errors, s.sentence_id) if worst is not None
                            else (s.sentence_id,)))
    if worst is not None:
        sel = sel[:worst]
    out = [f"> {NOTICE}", "", f"Engine: {results.engine['name']} - {len(sel)} sentence(s) listed", ""]
    for s in sel:
        w = s.primary["word"]
        out += [f"### {s.sentence_id} ({s.campaign}; tags: {', '.join(s.tags) or '-'}"
                f"; flags: {', '.join(s.flags) or '-'})",
                f"- reference: {s.reference}", f"- hypothesis: {s.hypothesis}",
                f"- S={w.substitutions} D={w.deletions} I={w.insertions} "
                f"WER={pct(w.rate)} CER={pct(s.primary['char'].rate)}"]
        if s.number_readings:
            out.append(f"- number readings: {', '.join(s.number_readings)}")
        for op in w.ops:
            if op["op"] == "sub":
                out.append(f"  - substitution: {op['ref']} → {op['hyp']}")
            elif op["op"] == "del":
                out.append(f"  - deletion: {op['ref']}")
            elif op["op"] == "ins":
                out.append(f"  - insertion: {op['hyp']}")
        out.append("")
    return "\n".join(out).rstrip() + "\n"

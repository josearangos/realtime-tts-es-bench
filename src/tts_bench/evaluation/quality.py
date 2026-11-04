"""Per-annotator quality metrics from joined annotation records. Flags only; nothing is excluded."""

from __future__ import annotations


def _diff(a: dict, b: dict) -> tuple[float, float] | None:
    keys = [k for k in a if k in b]
    if not keys:
        return None
    ds = [abs(a[k] - b[k]) for k in keys]
    return sum(ds) / len(ds), max(ds)


def _passes(answers: dict, expected: dict) -> bool:
    return all(answers.get(q) in allowed for q, allowed in expected.items())


def compute_quality(records: list[dict], thresholds: dict) -> dict:
    """records: dicts with project, item_id, annotator_id, role, repeat_of, answers{question:int}, expected{question:[int]}|None."""
    min_within = thresholds.get("repeat_within_1_min", 0.7)
    max_failed = thresholds.get("max_failed_checks", 1)
    by_annotator: dict[str, list[dict]] = {}
    for r in records:
        by_annotator.setdefault(r["annotator_id"], []).append(r)
    out = {}
    for ann, rows in sorted(by_annotator.items()):
        by_item = {r["item_id"]: r for r in rows}
        mads, within = [], []
        for r in rows:
            if r["role"] == "repeat" and r.get("repeat_of") in by_item:
                d = _diff(r["answers"], by_item[r["repeat_of"]]["answers"])
                if d:
                    mads.append(d[0])
                    within.append(d[1] <= 1)
        checks = [r for r in rows if r["role"].startswith("attention") and r.get("expected")]
        failed = sum(not _passes(r["answers"], r["expected"]) for r in checks)
        reasons = []
        if failed > max_failed:
            reasons.append(f"failed {failed} of {len(checks)} attention checks (max allowed {max_failed})")
        share = sum(within) / len(within) if within else None
        if share is not None and share < min_within:
            reasons.append(f"repeat consistency {share:.2f} below {min_within}")
        out[ann] = {
            "n_annotations": len(rows),
            "repeat_pairs": len(mads),
            "repeat_mad": round(sum(mads) / len(mads), 4) if mads else None,
            "repeat_within_1": round(share, 4) if share is not None else None,
            "attention_total": len(checks),
            "attention_failed": failed,
            "flagged": bool(reasons),
            "reasons": reasons,
        }
    return {"annotators": out, "thresholds": {"repeat_within_1_min": min_within, "max_failed_checks": max_failed}}

"""Equal error rate from labeled same-speaker and different-speaker scores (pure)."""

from __future__ import annotations

import statistics

from .model import EERRecord

HIGH_EER = 0.10
MIN_SEPARATION = 0.20
MIN_PAIRS = 2
_ROUND = 9


def _unavailable(reason: str, n_same: int, n_diff: int, description: str) -> EERRecord:
    return EERRecord(False, None, None, n_same, n_diff, False, None, False, reason, description)


def equal_error_rate(
    same_scores, different_scores, *, high_threshold: float = HIGH_EER,
    min_separation: float = MIN_SEPARATION, pair_construction: str = "",
) -> EERRecord:
    """Sweep the threshold over the sorted distinct scores (accept when score >= threshold).

    False-accept rate: share of different-speaker scores accepted. False-reject rate: share of
    same-speaker scores rejected. The crossing is found between the two nearest thresholds by
    linear interpolation. Ties are deterministic because only distinct sorted values are used.
    """
    same = [float(s) for s in same_scores]
    diff = [float(s) for s in different_scores]
    if len(same) < MIN_PAIRS or len(diff) < MIN_PAIRS:
        return _unavailable(
            f"at least {MIN_PAIRS} same-speaker and {MIN_PAIRS} different-speaker pairs are needed "
            f"(got {len(same)} and {len(diff)})", len(same), len(diff), pair_construction)

    def far(t: float) -> float:
        return sum(1 for d in diff if d >= t) / len(diff)

    def frr(t: float) -> float:
        return sum(1 for s in same if s < t) / len(same)

    thresholds = sorted(set(same) | set(diff))
    prev_t, prev_far, prev_frr = None, None, None
    eer = threshold = None
    for t in thresholds:
        f_a, f_r = far(t), frr(t)
        gap = f_a - f_r
        if gap <= 0:
            if prev_t is None or gap == 0:
                eer, threshold = f_a, t
            else:
                prev_gap = prev_far - prev_frr
                alpha = prev_gap / (prev_gap - gap)
                eer = prev_far + alpha * (f_a - prev_far)
                threshold = prev_t + alpha * (t - prev_t)
            break
        prev_t, prev_far, prev_frr = t, f_a, f_r
    separation = statistics.fmean(same) - statistics.fmean(diff)
    eer = round(eer, _ROUND)
    separation = round(separation, _ROUND)
    return EERRecord(
        True, eer, round(threshold, _ROUND), len(same), len(diff), eer > high_threshold,
        separation, eer <= high_threshold and separation >= min_separation, None, pair_construction)

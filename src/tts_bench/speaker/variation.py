"""Coefficient of variation with near-zero-mean and too-few-values guards (pure)."""

from __future__ import annotations

import statistics
from dataclasses import dataclass

MIN_ABS_MEAN = 0.05  # below this |mean|, in the metric's own unit, the CV is declined


@dataclass(frozen=True)
class CV:
    value: float | None
    status: str  # ok / near_zero_mean / fewer_than_two

    @property
    def reason(self) -> str | None:
        return None if self.status == "ok" else self.status


def coefficient_of_variation(values, *, min_abs_mean: float = MIN_ABS_MEAN) -> CV:
    """Sample standard deviation (n-1) divided by |mean|.

    Fewer than two values: `fewer_than_two`. |mean| below `min_abs_mean`: `near_zero_mean`
    (a ratio over a near-zero mean is not a reliable number, so none is returned).
    """
    vals = [float(v) for v in values]
    if len(vals) < 2:
        return CV(None, "fewer_than_two")
    mean = statistics.fmean(vals)
    if abs(mean) < min_abs_mean:
        return CV(None, "near_zero_mean")
    return CV(statistics.stdev(vals) / abs(mean), "ok")

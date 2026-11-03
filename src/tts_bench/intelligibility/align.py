"""Edit-distance alignment and error counting (pure, standard library only).

Definitions are in docs/intelligibility.md. WER and CER are
(S + D + I) / reference length with unit costs; they are not capped at 100%.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class ErrorBreakdown:
    substitutions: int
    deletions: int
    insertions: int
    reference_length: int
    ops: tuple = field(default=(), compare=False)

    @property
    def errors(self) -> int:
        return self.substitutions + self.deletions + self.insertions

    @property
    def rate(self) -> float | None:
        """(S + D + I) / reference_length; None when the reference is empty. Not capped."""
        if self.reference_length == 0:
            return None
        return self.errors / self.reference_length

    def to_dict(self, *, with_ops: bool = False) -> dict:
        d = {
            "S": self.substitutions,
            "D": self.deletions,
            "I": self.insertions,
            "reference_length": self.reference_length,
            "rate": self.rate,
        }
        if with_ops:
            d["ops"] = [dict(o) for o in self.ops]
        return d

    @classmethod
    def from_dict(cls, d: dict) -> "ErrorBreakdown":
        return cls(d["S"], d["D"], d["I"], d["reference_length"], tuple(d.get("ops", ())))

    @classmethod
    def pooled(cls, items) -> "ErrorBreakdown":
        s = dl = i = n = 0
        for b in items:
            s += b.substitutions
            dl += b.deletions
            i += b.insertions
            n += b.reference_length
        return cls(s, dl, i, n)

    @classmethod
    def full_failure(cls, reference: list[str] | str) -> "ErrorBreakdown":
        """Every reference unit counted as a deletion."""
        ref = list(reference)
        ops = tuple({"op": "del", "ref": r, "hyp": None} for r in ref)
        return cls(0, len(ref), 0, len(ref), ops)


@dataclass(frozen=True)
class Alignment:
    ops: tuple  # {"op": "match"|"sub"|"del"|"ins", "ref": str|None, "hyp": str|None}

    @property
    def substitutions(self) -> int:
        return sum(1 for o in self.ops if o["op"] == "sub")

    @property
    def deletions(self) -> int:
        return sum(1 for o in self.ops if o["op"] == "del")

    @property
    def insertions(self) -> int:
        return sum(1 for o in self.ops if o["op"] == "ins")


def align(reference: list[str], hypothesis: list[str]) -> Alignment:
    """Unit-cost Levenshtein alignment.

    Backtrace tie-break is fixed: substitution, then deletion, then insertion.
    """
    n, m = len(reference), len(hypothesis)
    cost = [[0] * (m + 1) for _ in range(n + 1)]
    for i in range(1, n + 1):
        cost[i][0] = i
    for j in range(1, m + 1):
        cost[0][j] = j
    for i in range(1, n + 1):
        for j in range(1, m + 1):
            sub = cost[i - 1][j - 1] + (0 if reference[i - 1] == hypothesis[j - 1] else 1)
            cost[i][j] = min(sub, cost[i - 1][j] + 1, cost[i][j - 1] + 1)

    ops: list[dict] = []
    i, j = n, m
    while i > 0 or j > 0:
        if i > 0 and j > 0:
            same = reference[i - 1] == hypothesis[j - 1]
            if cost[i][j] == cost[i - 1][j - 1] + (0 if same else 1):
                ops.append({"op": "match" if same else "sub", "ref": reference[i - 1], "hyp": hypothesis[j - 1]})
                i, j = i - 1, j - 1
                continue
        if i > 0 and cost[i][j] == cost[i - 1][j] + 1:
            ops.append({"op": "del", "ref": reference[i - 1], "hyp": None})
            i -= 1
        else:
            ops.append({"op": "ins", "ref": None, "hyp": hypothesis[j - 1]})
            j -= 1
    ops.reverse()
    return Alignment(tuple(ops))


def _breakdown(ref: list[str], hyp: list[str], keep_ops: bool) -> ErrorBreakdown:
    a = align(ref, hyp)
    return ErrorBreakdown(
        a.substitutions, a.deletions, a.insertions, len(ref), a.ops if keep_ops else ()
    )


def word_error_rate(reference: str, hypothesis: str) -> ErrorBreakdown:
    """Word level breakdown on whitespace-separated tokens (inputs already normalized)."""
    return _breakdown(reference.split(), hypothesis.split(), True)


def char_error_rate(reference: str, hypothesis: str) -> ErrorBreakdown:
    """Character level breakdown on the normalized strings; single spaces are counted."""
    return _breakdown(list(reference), list(hypothesis), False)

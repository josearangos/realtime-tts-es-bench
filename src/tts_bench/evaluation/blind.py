"""Opaque ids, seeded randomness and the private blind mapping."""

from __future__ import annotations

import json
import random
from dataclasses import asdict, dataclass, field
from pathlib import Path

ID_ALPHABET = "0123456789abcdef"


def make_rng(seed: int) -> random.Random:
    return random.Random(seed)


class IdGenerator:
    """12-hex ids, unique within the generator, reproducible for a seed."""

    def __init__(self, rng: random.Random, taken: set[str] | None = None):
        self._rng = rng
        self._taken = set(taken or ())

    def new(self) -> str:
        while True:
            item_id = "".join(self._rng.choice(ID_ALPHABET) for _ in range(12))
            if item_id not in self._taken:
                self._taken.add(item_id)
                return item_id


@dataclass
class MappingRow:
    item_id: str
    project: str                      # mos | cmos | sim
    role: str = "test"                # test | repeat | attention_instructed | attention_degraded
    repeat_of: str | None = None
    sentence_id: str | None = None
    corpus_version: str | None = None
    engine: str | None = None
    voice: str | None = None
    accent: str | None = None
    cloned: bool | None = None
    a: dict | None = None             # cmos: condition shown as A
    b: dict | None = None             # cmos: condition shown as B
    position: str | None = None       # cmos: "ab" (first pair member is A) or "ba"
    expected: dict | None = None      # attention checks: {question: [allowed answers]}
    served_files: list = field(default_factory=list)


def write_mapping(path: str | Path, rows: list[MappingRow]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for r in rows:
            f.write(json.dumps(asdict(r), ensure_ascii=False, sort_keys=True) + "\n")


def read_mapping(path: str | Path) -> list[MappingRow]:
    rows = []
    with Path(path).open(encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(MappingRow(**json.loads(line)))
    return rows

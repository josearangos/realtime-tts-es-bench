from __future__ import annotations

import json
import re
from dataclasses import asdict, dataclass
from pathlib import Path

USES = ("internal_benchmarking", "published_results", "published_demo_audio", "human_evaluation")
CONTENT = ("outbound_sales", "collections", "inbound", "cloning_prompts")
_ALIAS = re.compile(r"[a-z0-9_-]+")
_DATE = re.compile(r"\d{4}(-\d{2}-\d{2})?")


@dataclass
class ConsentRecord:
    alias: str
    date: str
    permitted_uses: list[str]
    allowed_content: list[str]
    notes: str = ""

    def __post_init__(self) -> None:
        if not _ALIAS.fullmatch(self.alias or ""):
            raise ValueError(f"alias must match [a-z0-9_-]+ (a pseudonym, no real name): {self.alias!r}")
        if not _DATE.fullmatch(self.date or ""):
            raise ValueError(f"date must be YYYY or YYYY-MM-DD: {self.date!r}")
        if self.date[4:]:
            import datetime

            try:
                datetime.date.fromisoformat(self.date)
            except ValueError as exc:
                raise ValueError(f"invalid date {self.date!r}") from exc
        for field, values, allowed in (
            ("permitted_uses", self.permitted_uses, USES),
            ("allowed_content", self.allowed_content, CONTENT),
        ):
            if not values:
                raise ValueError(f"{field} must not be empty")
            bad = [v for v in values if v not in allowed]
            if bad:
                raise ValueError(f"{field}: unknown value(s) {bad}; allowed: {list(allowed)}")

    def permits(self, use: str | None = None, content: str | None = None) -> str | None:
        """Name of the first missing permission, or None when permitted."""
        if use is not None and use not in self.permitted_uses:
            return use
        if content is not None and content not in self.allowed_content:
            return content
        return None

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(asdict(self), indent=2, ensure_ascii=False), encoding="utf-8")

    @classmethod
    def load(cls, path: Path) -> "ConsentRecord":
        return cls(**json.loads(path.read_text(encoding="utf-8")))

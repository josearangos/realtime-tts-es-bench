"""Read corpus files from disk and compute the content hash."""

from __future__ import annotations

import hashlib
import json
import re
from pathlib import Path

from .model import Address, Campaign, CorpusVersion, Probe, Scenario, Sentence, Subset, Tag

SENTENCES_FILE = "sentences.jsonl"
CLONING_FILE = "cloning.jsonl"
VERSION_FILE = "VERSION.json"

ID_RE = re.compile(r"^(VEN|COB|ENT|CLO)-\d{3}$")
REQUIRED = ("id", "text", "campaign", "scenario", "tags", "probes", "reviewed", "subset")


class CorpusError(ValueError):
    """Malformed corpus data. The message names the file and line."""


def default_corpus_dir() -> Path:
    """`corpus/` at the repository root (three levels above this package)."""
    return Path(__file__).resolve().parents[3] / "corpus"


def _enum(enum_cls, value, where: str, field: str):
    try:
        return enum_cls(value)
    except ValueError:
        raise CorpusError(f"{where}: unknown {field} {value!r}") from None


def parse_record(raw: dict, where: str) -> Sentence:
    if not isinstance(raw, dict):
        raise CorpusError(f"{where}: record is not a JSON object")
    missing = [k for k in REQUIRED if k not in raw]
    if missing:
        raise CorpusError(f"{where}: missing field(s) {', '.join(missing)}")
    if not isinstance(raw["id"], str) or not ID_RE.match(raw["id"]):
        raise CorpusError(f"{where}: invalid id {raw['id']!r}")
    if not isinstance(raw["text"], str):
        raise CorpusError(f"{where}: text must be a string")
    if not isinstance(raw["tags"], list):
        raise CorpusError(f"{where}: tags must be a list")
    if not isinstance(raw["reviewed"], bool):
        raise CorpusError(f"{where}: reviewed must be true or false")
    spoken = raw.get("spoken")
    if spoken is not None and not isinstance(spoken, str):
        raise CorpusError(f"{where}: spoken must be a string")
    return Sentence(
        id=raw["id"],
        text=raw["text"],
        campaign=_enum(Campaign, raw["campaign"], where, "campaign"),
        scenario=_enum(Scenario, raw["scenario"], where, "scenario"),
        tags=tuple(_enum(Tag, t, where, "tag") for t in raw["tags"]),
        probes=_enum(Probe, raw["probes"], where, "probes"),
        address=_enum(Address, raw.get("address", "usted"), where, "address"),
        spoken=spoken,
        reviewed=raw["reviewed"],
        subset=_enum(Subset, raw["subset"], where, "subset"),
    )


def read_sentences(path: Path) -> list[Sentence]:
    """Parse a .jsonl file into sentences ordered by id."""
    out: list[Sentence] = []
    text = Path(path).read_text(encoding="utf-8")
    for n, line in enumerate(text.splitlines(), start=1):
        if not line.strip():
            continue
        where = f"{Path(path).name}:{n}"
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as exc:
            raise CorpusError(f"{where}: invalid JSON ({exc.msg})") from None
        out.append(parse_record(raw, where))
    return sorted(out, key=lambda s: s.id)


def read_version(directory: Path) -> CorpusVersion:
    path = Path(directory) / VERSION_FILE
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        raise CorpusError(f"{VERSION_FILE}: file not found in {directory}") from None
    except json.JSONDecodeError as exc:
        raise CorpusError(f"{VERSION_FILE}: invalid JSON ({exc.msg})") from None
    for key in ("version", "date", "counts", "content_sha256"):
        if key not in raw:
            raise CorpusError(f"{VERSION_FILE}: missing field {key}")
    if not re.fullmatch(r"\d+\.\d+\.\d+", str(raw["version"])):
        raise CorpusError(f"{VERSION_FILE}: version {raw['version']!r} is not MAJOR.MINOR.PATCH")
    return CorpusVersion(raw["version"], raw["date"], raw["counts"], raw["content_sha256"])


def compute_hash(directory: Path) -> str:
    """SHA-256 over sentences.jsonl and cloning.jsonl (missing file counts as empty)."""
    h = hashlib.sha256()
    for name in (SENTENCES_FILE, CLONING_FILE):
        p = Path(directory) / name
        data = p.read_bytes() if p.exists() else b""
        h.update(name.encode() + b"\0" + data + b"\0")
    return h.hexdigest()

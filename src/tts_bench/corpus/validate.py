"""Offline corpus validator: errors block use, warnings are reported."""

from __future__ import annotations

import glob
import json
import re
from collections import Counter
from dataclasses import dataclass, field
from pathlib import Path

from .loader import (
    CLONING_FILE, SENTENCES_FILE, VERSION_FILE, CorpusError, compute_hash,
    read_sentences, read_version,
)
from .model import (
    CAMPAIGN_SCENARIOS, CROSS_CUTTING_SCENARIOS, PROBE_TAG, Address, Campaign,
    Probe, Scenario, Sentence, Subset, Tag,
)

MIN_MAIN = 100
MIN_PER_CAMPAIGN = 25
MIN_PER_SCENARIO = 2
MIN_CROSS_CUTTING = 5
MIN_PER_PROBE = 5
MIN_PER_TAG = 10
MIN_PER_ADDRESS = 5
MIN_CLONING_PER_CAMPAIGN = 5
LONG_WORDS = 25
SHORT_WORDS = 5
NEAR_DUP = 0.9
TRANSCRIPT_OVERLAP = 0.8
MIN_FRAGMENT_WORDS = 3

BANNED_FILE = Path(__file__).with_name("banned_phrases.txt")

_DIGIT = re.compile(r"\d")
_SYMBOL = re.compile(r"[%$#&@+=/*<>\\_°]")
_ACRONYM = re.compile(r"\b[A-ZÁÉÍÓÚÑ]{2,}\b|\b\d+[A-Za-z]\b")
_SPLIT = re.compile(r"[.!?¡¿;:\n]+")


@dataclass(frozen=True)
class Issue:
    code: str
    message: str

    def __str__(self) -> str:
        return f"[{self.code}] {self.message}"


@dataclass
class Report:
    errors: list[Issue] = field(default_factory=list)
    warnings: list[Issue] = field(default_factory=list)
    counts: dict = field(default_factory=dict)
    overlap: str = "not run"  # passed | failed | not run

    @property
    def ok(self) -> bool:
        return not self.errors

    def error(self, code: str, message: str) -> None:
        self.errors.append(Issue(code, message))

    def warn(self, code: str, message: str) -> None:
        self.warnings.append(Issue(code, message))

    def codes(self) -> set[str]:
        return {i.code for i in self.errors}


def normalize(text: str) -> str:
    """Lowercase, keep accents, drop punctuation and extra spaces."""
    text = re.sub(r"[^\w\s]|_", " ", text.lower())
    return " ".join(text.split())


def jaccard(a: str, b: str) -> float:
    sa, sb = set(a.split()), set(b.split())
    if not sa or not sb:
        return 0.0
    return len(sa & sb) / len(sa | sb)


def needs_spoken(text: str) -> bool:
    return bool(_DIGIT.search(text) or _SYMBOL.search(text) or _ACRONYM.search(text))


def word_count(text: str) -> int:
    return len(text.split())


def load_banned(path: Path = BANNED_FILE) -> list[str]:
    out = []
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#"):
            out.append(line.lower())
    return out


def _read(path: Path, report: Report) -> list[Sentence]:
    if not path.exists():
        report.error("missing_file", f"{path.name} not found")
        return []
    try:
        return read_sentences(path)
    except CorpusError as exc:
        report.error("malformed", str(exc))
        return []


def _check_sentence(s: Sentence, expected: Subset, banned: list[str], report: Report) -> None:
    if not s.text.strip():
        report.error("empty_text", f"{s.id}: text is empty")
    elif s.text != s.text.strip():
        report.error("text_spaces", f"{s.id}: text has leading or trailing spaces")
    if s.subset != expected:
        report.error("subset_mismatch", f"{s.id}: subset {s.subset.value!r} in the {expected.value} file")
    prefix = s.id.split("-")[0]
    want = {"VEN": Campaign.OUTBOUND_SALES, "COB": Campaign.COLLECTIONS, "ENT": Campaign.INBOUND}.get(prefix)
    if want is not None and s.campaign != want:
        report.error("campaign_prefix", f"{s.id}: prefix does not match campaign {s.campaign.value}")
    if s.scenario not in CROSS_CUTTING_SCENARIOS and s.scenario not in CAMPAIGN_SCENARIOS[s.campaign]:
        report.error("scenario_campaign", f"{s.id}: scenario {s.scenario.value} does not belong to {s.campaign.value}")

    # probe/tag agreement
    need = PROBE_TAG.get(s.probes)
    if need is not None and need not in s.tags:
        report.error("probe_tag", f"{s.id}: probe {s.probes.value} requires tag {need.value}")

    # tags consistent with the text
    words = word_count(s.text)
    tags = set(s.tags)
    if Tag.LONG in tags and words < LONG_WORDS:
        report.error("tag_long", f"{s.id}: tag long needs {LONG_WORDS}+ words, has {words}")
    if Tag.SHORT in tags and words > SHORT_WORDS:
        report.error("tag_short", f"{s.id}: tag short needs {SHORT_WORDS} or fewer words, has {words}")
    if Tag.QUESTION in tags and "?" not in s.text:
        report.error("tag_question", f"{s.id}: tag question needs a question mark")
    for t in (Tag.AMOUNT_COP, Tag.NUMBER):
        if t in tags and not _DIGIT.search(s.text):
            report.error("tag_digits", f"{s.id}: tag {t.value} needs digits in the text")
    if Tag.ACRONYM in tags and not _ACRONYM.search(s.text):
        report.error("tag_acronym", f"{s.id}: tag acronym needs an acronym (uppercase run or form like 4G)")

    # spoken reading
    if needs_spoken(s.text):
        if not s.spoken:
            report.error("missing_spoken", f"{s.id}: text has digits, symbols or acronyms but no spoken reading")
    if s.spoken is not None and needs_spoken(s.spoken):
        report.error("spoken_symbols", f"{s.id}: spoken reading still contains digits, symbols or acronyms")

    if s.campaign == Campaign.COLLECTIONS:
        low = s.text.lower()
        for phrase in banned:
            if phrase in low:
                report.error("banned_phrase", f"{s.id}: banned phrase {phrase!r} in collections text")


def _changelog_has(directory: Path, version: str) -> bool:
    p = directory / "CHANGELOG.md"
    if not p.exists():
        return False
    pat = re.compile(rf"^#{{2,3}}\s*\[?v?{re.escape(version)}\]?(\s|$)", re.MULTILINE)
    return bool(pat.search(p.read_text(encoding="utf-8")))


def _regionalism_ids(directory: Path) -> set[str]:
    p = directory / "REGIONALISMS.md"
    if not p.exists():
        return set()
    return set(re.findall(r"\b(?:VEN|COB|ENT|CLO)-\d{3}\b", p.read_text(encoding="utf-8")))


def _segments(text: str) -> list[str]:
    out = []
    for part in _SPLIT.split(text):
        n = normalize(part)
        if len(n.split()) >= MIN_FRAGMENT_WORDS:
            out.append(n)
    return out


def default_transcripts(directory: Path) -> list[Path]:
    root = Path(directory).resolve().parent
    return [Path(p) for p in sorted(glob.glob(str(root / "cloned_voices" / "*" / "transcript.txt")))]


def check_transcript_overlap(cloning: list[Sentence], transcripts: list[Path], report: Report) -> None:
    if not transcripts:
        report.overlap = "not run"
        return
    refs: list[tuple[Path, str]] = []
    for t in transcripts:
        try:
            body = Path(t).read_text(encoding="utf-8")
        except OSError as exc:
            report.error("transcript_unreadable", f"{t}: {exc}")
            continue
        refs.extend((Path(t), seg) for seg in _segments(body))
    failed = False
    for s in cloning:
        for part in _segments(s.text):
            for path, seg in refs:
                if part == seg or jaccard(part, seg) >= TRANSCRIPT_OVERLAP:
                    report.error("cloning_overlap", f"{s.id}: overlaps transcript {path} ({seg!r})")
                    failed = True
                    break
            else:
                continue
            break
    report.overlap = "failed" if failed else "passed"


def validate(
    directory: str | Path,
    transcripts: list[str | Path] | None = None,
    release: bool = False,
) -> Report:
    directory = Path(directory)
    report = Report()
    banned = load_banned()

    main = _read(directory / SENTENCES_FILE, report)
    cloning = _read(directory / CLONING_FILE, report)

    for s in main:
        _check_sentence(s, Subset.MAIN, banned, report)
    for s in cloning:
        _check_sentence(s, Subset.CLONING, banned, report)

    # ids
    ids = Counter(s.id for s in main + cloning)
    for sid, n in sorted(ids.items()):
        if n > 1:
            report.error("duplicate_id", f"{sid}: id appears {n} times")

    # sizes and coverage (main)
    if len(main) < MIN_MAIN:
        report.error("too_few", f"main corpus has {len(main)} sentences, needs {MIN_MAIN}")
    by_campaign = Counter(s.campaign for s in main)
    for c in Campaign:
        if by_campaign[c] < MIN_PER_CAMPAIGN:
            report.error("campaign_below", f"campaign {c.value} has {by_campaign[c]} sentences, needs {MIN_PER_CAMPAIGN}")
    by_scenario = Counter(s.scenario for s in main)
    for c, scenarios in CAMPAIGN_SCENARIOS.items():
        for sc in scenarios:
            n = sum(1 for s in main if s.scenario == sc and s.campaign == c)
            if n < MIN_PER_SCENARIO:
                report.error("scenario_below", f"scenario {sc.value} has {n} sentences, needs {MIN_PER_SCENARIO}")
    for sc in CROSS_CUTTING_SCENARIOS:
        if by_scenario[sc] < MIN_CROSS_CUTTING:
            report.error("scenario_below", f"scenario {sc.value} has {by_scenario[sc]} sentences, needs {MIN_CROSS_CUTTING}")
    by_probe = Counter(s.probes for s in main)
    for p in Probe:
        if by_probe[p] < MIN_PER_PROBE:
            report.error("probe_below", f"probe {p.value} has {by_probe[p]} sentences, needs {MIN_PER_PROBE}")
    by_tag = Counter(t for s in main for t in set(s.tags))
    for t in Tag:
        if by_tag[t] < MIN_PER_TAG:
            report.error("tag_below", f"tag {t.value} has {by_tag[t]} sentences, needs {MIN_PER_TAG}")
    by_addr = Counter(s.address for s in main)
    for a in (Address.TU, Address.VOS):
        if by_addr[a] < MIN_PER_ADDRESS:
            report.error("address_below", f"address {a.value} has {by_addr[a]} sentences, needs {MIN_PER_ADDRESS}")

    # regionalisms document
    known = {s.id for s in main + cloning}
    reg_ids = _regionalism_ids(directory)
    for rid in sorted(reg_ids - known):
        report.error("regionalism_id", f"REGIONALISMS.md references unknown sentence id {rid}")
    if main and not (directory / "REGIONALISMS.md").exists():
        report.error("missing_file", "REGIONALISMS.md not found")

    # duplicates and near-duplicates
    norm = [(s, normalize(s.text)) for s in main + cloning]
    seen: dict[str, Sentence] = {}
    for s, n in norm:
        if n in seen:
            other = seen[n]
            code = "cloning_overlap" if {s.subset, other.subset} == {Subset.MAIN, Subset.CLONING} else "duplicate_text"
            report.error(code, f"{s.id} has the same text as {other.id}")
        else:
            seen[n] = s
    for i in range(len(norm)):
        for j in range(i + 1, len(norm)):
            (a, na), (b, nb) = norm[i], norm[j]
            if na != nb and jaccard(na, nb) >= NEAR_DUP:
                report.warn("near_duplicate", f"{a.id} and {b.id} are near-duplicates")

    # cloning subset
    by_clo = Counter(s.campaign for s in cloning)
    for c in Campaign:
        if by_clo[c] < MIN_CLONING_PER_CAMPAIGN:
            report.error("cloning_campaign_below", f"cloning has {by_clo[c]} {c.value} sentences, needs {MIN_CLONING_PER_CAMPAIGN}")
    paths = [Path(t) for t in transcripts] if transcripts else default_transcripts(directory)
    check_transcript_overlap(cloning, paths, report)

    # version file
    try:
        ver = read_version(directory)
    except CorpusError as exc:
        report.error("version_file", str(exc))
        ver = None
    if ver is not None:
        actual = compute_hash(directory)
        if ver.content_sha256 != actual:
            msg = f"{VERSION_FILE} content_sha256 does not match the sentence files (run `stamp`)"
            if ver.version.startswith("0."):
                report.warn("hash_mismatch", msg)
            else:
                report.error("hash_mismatch", msg)
        if not _changelog_has(directory, ver.version):
            report.error("changelog", f"CHANGELOG.md has no heading for version {ver.version}")

    if release:
        for s in main + cloning:
            if not s.reviewed:
                report.error("unreviewed", f"{s.id}: not reviewed by a native speaker")

    report.counts = {
        "main": len(main),
        "cloning": len(cloning),
        "campaign": {c.value: by_campaign[c] for c in Campaign},
        "scenario": {sc.value: by_scenario[sc] for sc in Scenario},
        "tag": {t.value: by_tag[t] for t in Tag},
        "probe": {p.value: by_probe[p] for p in Probe},
        "address": {a.value: by_addr[a] for a in Address},
        "cloning_campaign": {c.value: by_clo[c] for c in Campaign},
        "reviewed": sum(1 for s in main + cloning if s.reviewed),
    }
    return report


def stamp(directory: str | Path) -> dict:
    """Recompute counts and content_sha256 in VERSION.json; returns the new content."""
    directory = Path(directory)
    path = directory / VERSION_FILE
    raw = json.loads(path.read_text(encoding="utf-8"))
    main = read_sentences(directory / SENTENCES_FILE)
    cloning = read_sentences(directory / CLONING_FILE)
    raw["counts"] = {
        "main": len(main),
        "cloning": len(cloning),
        "outbound_sales": sum(1 for s in main if s.campaign == Campaign.OUTBOUND_SALES),
        "collections": sum(1 for s in main if s.campaign == Campaign.COLLECTIONS),
        "inbound": sum(1 for s in main if s.campaign == Campaign.INBOUND),
        "total": len(main) + len(cloning),
    }
    raw["content_sha256"] = compute_hash(directory)
    path.write_text(json.dumps(raw, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return raw

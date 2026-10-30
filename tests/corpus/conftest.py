import json
import shutil
from pathlib import Path

import pytest

REPO_CORPUS = Path(__file__).resolve().parents[2] / "corpus"


def record(id="VEN-001", text="Buenos días, le habla Laura.", **over):
    base = {
        "id": id, "text": text, "campaign": "outbound_sales", "scenario": "mobile_prepaid",
        "tags": [], "address": "usted", "probes": "regionalism", "reviewed": False, "subset": "main",
    }
    base.update(over)
    return base


def write_jsonl(path: Path, records: list[dict]) -> None:
    path.write_text("\n".join(json.dumps(r, ensure_ascii=False) for r in records) + "\n", encoding="utf-8")


def read_jsonl(path: Path) -> list[dict]:
    return [json.loads(l) for l in path.read_text(encoding="utf-8").splitlines() if l.strip()]


@pytest.fixture
def small_corpus(tmp_path):
    """Tiny valid-structure corpus for loader tests."""
    d = tmp_path / "small"
    d.mkdir()
    write_jsonl(d / "sentences.jsonl", [
        record("VEN-002", "Segunda frase."),
        record("VEN-001", "Primera frase."),
    ])
    write_jsonl(d / "cloning.jsonl", [record("CLO-001", "Frase de clonación.", subset="cloning")])
    (d / "VERSION.json").write_text(json.dumps(
        {"version": "0.1.0", "date": "2026-10-29", "counts": {}, "content_sha256": ""}), encoding="utf-8")
    return d


@pytest.fixture
def shipped_copy(tmp_path):
    """Writable copy of the shipped corpus, to mutate one rule at a time."""
    d = tmp_path / "corpus"
    shutil.copytree(REPO_CORPUS, d)
    return d


def mutate(directory: Path, filename: str, fn) -> None:
    rows = read_jsonl(directory / filename)
    fn(rows)
    write_jsonl(directory / filename, rows)

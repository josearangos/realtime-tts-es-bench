"""Spanish call center test corpus: loader and version stamp."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from .loader import (
    CLONING_FILE, SENTENCES_FILE, CorpusError, compute_hash, default_corpus_dir,
    read_sentences, read_version,
)
from .model import Address, Campaign, CorpusVersion, Probe, Scenario, Sentence, Subset, Tag

__all__ = [
    "Address", "Campaign", "Corpus", "CorpusError", "CorpusVersion", "Probe",
    "Scenario", "Sentence", "Subset", "Tag", "corpus_stamp", "load_corpus",
]


@dataclass(frozen=True)
class Corpus:
    version: str
    content_hash: str
    sentences: tuple[Sentence, ...]

    def by_campaign(self, name) -> tuple[Sentence, ...]:
        name = Campaign(name)
        return tuple(s for s in self.sentences if s.campaign == name)

    def by_tag(self, name) -> tuple[Sentence, ...]:
        name = Tag(name)
        return tuple(s for s in self.sentences if name in s.tags)

    def by_scenario(self, name) -> tuple[Sentence, ...]:
        name = Scenario(name)
        return tuple(s for s in self.sentences if s.scenario == name)


def load_corpus(path: str | Path | None = None, subset: str = "main") -> Corpus:
    """Load a subset ("main" or "cloning"), ordered by id.

    Checks structure only; coverage rules belong to `python -m tts_bench.corpus validate`.
    """
    directory = Path(path) if path is not None else default_corpus_dir()
    subset = Subset(subset)
    filename = SENTENCES_FILE if subset is Subset.MAIN else CLONING_FILE
    sentences = read_sentences(directory / filename)
    for s in sentences:
        if s.subset != subset:
            raise CorpusError(f"{filename}: {s.id} has subset {s.subset.value!r}, expected {subset.value!r}")
    return Corpus(
        version=read_version(directory).version,
        content_hash=compute_hash(directory),
        sentences=tuple(sentences),
    )


def corpus_stamp(corpus: Corpus) -> dict:
    """Keys every result file must embed (FR-010)."""
    return {"corpus_version": corpus.version, "corpus_hash": corpus.content_hash}

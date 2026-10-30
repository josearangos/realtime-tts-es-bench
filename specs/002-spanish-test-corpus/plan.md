# Implementation Plan: Spanish Call Center Test Corpus

**Branch**: `002-spanish-test-corpus` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/002-spanish-test-corpus/spec.md`

## Summary

Ship a versioned, plain-text corpus of at least 100 fictitious Colombian-Spanish call center sentences (outbound sales, collections, inbound), stored as one JSON object per line, plus a separate cloning subset file, a version file with a changelog, and a documented Colombian/Latin American regionalism list. A small standard-library loader exposes the sentences and the corpus version to every other feature, and an offline validator enforces the counts, the per-difficulty coverage, the native-speaker review flag, required fields, duplicate detection, normalized readings, and zero overlap with reference transcripts. See [research.md](research.md) for the decisions.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: none beyond the standard library (core package already depends on numpy only)

**Storage**: plain files in `corpus/` at the repository root: `sentences.jsonl`, `cloning.jsonl`, `VERSION.json`, `CHANGELOG.md`, `REGIONALISMS.md`

**Testing**: pytest; validator tests use small fixture corpora, plus one test that validates the shipped corpus

**Target Platform**: macOS and Linux, no network

**Project Type**: library plus a small validation command (`python -m tts_bench.corpus`)

**Performance Goals**: validation of the full corpus in well under one minute (expected under one second)

**Constraints**: offline; diff-friendly; no real personal data or company names; respectful collections wording; no audio in the corpus

**Scale/Scope**: about 100 to 150 main sentences and about 20 cloning sentences; 5 small modules

## Constitution Check

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | short utterances and long sentences tagged so TTFA and RTF can be broken down by length |
| II Spanish by default | Pass | all text Spanish, Colombian focus, regionalisms and address forms documented |
| III Apples-to-apples | Pass | single shared corpus, fixed order by id, version recorded in every result |
| IV Deterministic vs human | N/A | no evaluation here |
| V Honest reporting | Pass | version plus content hash allow results to be tied to exact text |
| VI Licensing/consent | Pass | fictitious data only; reference transcripts come from `cloned_voices/` (git-ignored) and are never copied into the corpus |
| VII Modular | Pass | corpus package has no dependency on adapters, backend, or frontend |
| VIII Verifiable | Pass | every requirement maps to a validator check with fixture tests |

Post-design re-check: no violations; Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/002-spanish-test-corpus/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── corpus-interface.md
└── tasks.md             # created later by /speckit-tasks
```

### Source Code (repository root)

```text
corpus/
├── sentences.jsonl       # main corpus, one sentence per line, ordered by id
├── cloning.jsonl         # held-out cloning subset
├── VERSION.json          # version id, date, sentence counts, content hash
├── CHANGELOG.md
└── REGIONALISMS.md       # documented Colombian/Latin American vocabulary and address forms

src/tts_bench/corpus/
├── __init__.py           # load_corpus(), Corpus, Sentence
├── model.py              # Sentence, CorpusVersion, enums for campaign/scenario/tags
├── loader.py             # reads files, computes content hash
├── validate.py           # rules, report, transcript overlap check
└── __main__.py           # python -m tts_bench.corpus validate [--transcripts PATH...]

tests/corpus/
├── test_loader.py
├── test_validate.py
└── test_shipped_corpus.py
```

**Structure Decision**: data lives at the repository root so it is reviewed as content, separate from code; the loader lives in the existing `tts_bench` package, extending the single-project layout from feature 001.

## Complexity Tracking

No violations to justify.

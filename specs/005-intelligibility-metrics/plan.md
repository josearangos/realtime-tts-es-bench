# Implementation Plan: Intelligibility Metrics (WER and CER)

**Branch**: `005-intelligibility-metrics` | **Date**: 2026-11-02 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/005-intelligibility-metrics/spec.md`

## Summary

Add a package `tts_bench.intelligibility` with a CLI in four independent stages: `synthesize` (one engine, one synthesis per corpus sentence, WAV files plus a manifest), `transcribe` (one fixed recognizer, identical settings, transcripts file), `score` (pure computation of WER and CER with the documented Spanish normalization, no recognizer and no engine), and `compare`/`errors` (Markdown tables and per-sentence error breakdown). The stages run in separate virtual environments because each engine has its own and the recognizer has its own; only `score`, `compare` and `errors` need no heavy dependency, so the whole computation is tested with fixed transcripts (FR-010). See [research.md](research.md) for decisions, [data-model.md](data-model.md) for entities, [contracts/](contracts/) for the CLI and file formats, and [quickstart.md](quickstart.md) for validation.

## Technical Context

**Language/Version**: Python 3.11 (repo requires >=3.11)

**Primary Dependencies**: `score`, `compare`, `errors` and `synthesize`: standard library plus `numpy` (already core). `transcribe` only: `faster-whisper` in its own `.venv-asr`, optional extra `asr = ["faster-whisper"]`. No text-normalization or edit-distance library (own small, tested implementations so results are reproducible and auditable).

**Storage**: audio in `output/intelligibility/<engine>-<voice>/` (WAV, already git-ignored) with `manifest.json`; transcripts and results as JSON in `results/intelligibility/` (tracked; contain recognized text, never audio or voice material); Markdown summaries written by `compare`.

**Testing**: pytest in `tests/intelligibility/` with fixed transcript pairs, a `FakeRecognizer` (scripted text per audio), the existing fake engine and synthetic WAV files (tone, digital silence). A `@pytest.mark.engine` test runs the real recognizer in `.venv-asr`.

**Target Platform**: macOS (Apple Silicon) and Linux, CPU

**Project Type**: library plus CLI (`python -m tts_bench.intelligibility`)

**Performance Goals**: none beyond practicality: scoring 123 sentences takes under a second; transcription time is not a metric.

**Constraints**: local-first (no network use after the one-time model download); one engine per process; no engine-specific logic; same recognizer and settings for all engines; deterministic scoring (SC-004).

**Scale/Scope**: 123 main sentences per engine, one synthesis each; about 13 small modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | adds the intelligibility signal next to TTFA/RTF; does not rank on size or cloning |
| II Spanish by Default | Pass | Spanish corpus, recognizer forced to Spanish, voice variant stored; regional-accent caveat recorded in metadata |
| III Apples-to-apples | Pass | same corpus and order, same recognizer and settings, one engine per process; `compare` refuses mixed recognizer, corpus, subset or limit. The principle's "multiple repetitions, p50/p95" bullet applies to timing metrics; WER uses one synthesis per sentence by clarification (2026-11-02), pooled over sentences, and the report states that sampling variance across syntheses is not measured |
| IV Deterministic vs human | Pass | outputs state that WER measures intelligibility, not naturalness (FR-009); no MOS here |
| V Honest reporting | Pass | recognizer identity, version, settings, environment and exact command stored; raw transcripts and per-sentence alignments kept so anyone can recompute; the recognizer's own errors are stated as a limitation |
| VI Licensing/consent | Pass | voices only via `LocalVoiceLibrary.resolve`; no audio or voice material in `results/`; recognizer model license recorded in the results and to be verified per checkpoint when pinned (task) |
| VII Modular | Pass | stages are independently usable; `score` imports only `corpus`; no backend or frontend; new engines need no change |
| VIII Verifiable | Pass | each FR maps to a fixed-transcript test; every metric and the normalization are defined in `docs/intelligibility.md` |

Post-design re-check: no violations; Complexity Tracking not needed. No change to features 001 to 004 is required.

## Decisions Confirmed Before Task Generation

Confirmed by the maintainer on 2026-11-02 (all suggested defaults accepted):

1. **Recognizer**: `faster-whisper` with a multilingual Whisper checkpoint (`large-v3` as the default, int8 on CPU), language forced to `es`, greedy decoding (`beam_size=1`, `temperature=0`), no VAD filter, no prompt, no conditioning on previous text. Model name and revision are a recorded setting. The exact checkpoint and its license are verified when it is first downloaded.
2. **Per-category groups**: every feature tag (9), every campaign (3), plus overall. A sentence with several tags counts in each of its tag groups, so tag groups overlap; sample sizes (sentences and reference words) are shown.
3. **Numbers and acronyms on the transcript side**: recognizers often write digits and letters ("$1.847.300", "PSE") where the corpus `spoken` form has words. The normalizer expands numerals and a small documented lexicon of acronyms and units (`pse`→`pe ese e`, `sms`, `pqr`, `tv`, `4g`, `gb`→`gigas`, `nit`, `iva`) on both sides. A digit run can be read as a cardinal or digit by digit; the reading closest to the reference is used, documented, and reported per sentence (see research R4).
4. **Silence threshold**: peak below 1e-4 full scale (about -80 dBFS) or duration zero counts as silent; the recognizer is not run on it.
5. **Failure inputs**: synthesis failures and invalid audio recorded by `synthesize` are carried through the manifest and scored as full failures.
6. **Minor defaults**: `low_sample` below 10 sentences per group; the lexicon starts with the eight entries found in the corpus and grows only with a `lexicon_version` bump; the first real run covers piper, phonon and pocket_tts with the voices used in feature 004; a run always finishes the corpus and is marked not reliable above 10% flagged sentences (FR-011); sampling variance across syntheses is not measured and is stated in reports.

## Project Structure

### Documentation (this feature)

```text
specs/005-intelligibility-metrics/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── intelligibility-cli.md
│   └── results-file.md
├── checklists/requirements.md
└── tasks.md              # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/tts_bench/intelligibility/
├── __init__.py       # exports score_transcripts, normalize, word_error_rate, char_error_rate
├── __main__.py       # CLI: synthesize, transcribe, score, compare, errors
├── normalize.py      # Spanish normalization ruleset (pure)
├── numbers.py        # Spanish numeral to words, digit-by-digit reading, currency, times (pure)
├── lexicon.py        # acronym and unit lexicon (data + lookup)
├── align.py          # word/char alignment: substitutions, deletions, insertions (pure)
├── scoring.py        # per-sentence rates, pooled per-category and overall rates (pure)
├── audio_check.py    # silence and empty detection on a WAV
├── synth.py          # one synthesis per sentence through an EngineAdapter; writes WAV + manifest
├── recognizer.py     # Recognizer protocol, FasterWhisperRecognizer, FakeRecognizer
├── transcribe.py     # transcription stage: skips silent/failed audio, caches by audio hash + settings hash
├── files.py          # manifest, transcripts and results files: write/read/schema check
└── compare.py        # merge rules, Markdown tables, error breakdown report
docs/
└── intelligibility.md  # definitions, normalization ruleset, limitations
results/
└── intelligibility/    # transcripts and results JSON
tests/intelligibility/
├── conftest.py
├── test_align.py
├── test_normalize.py
├── test_numbers.py
├── test_corpus_normalization.py   # normalize_pair(spoken, text) gives identical strings for every corpus sentence
├── test_audio_check.py
├── test_scoring.py
├── test_failures.py
├── test_pipeline_fake.py
├── test_files_compare.py
├── test_determinism.py
├── test_errors_report.py
├── test_recognizer_real.py        # engine-marked, runs in .venv-asr
└── test_offline.py
```

**Structure Decision**: single project, one new subpackage beside `corpus`, `voices` and `metrics`. Pure functions (`normalize`, `numbers`, `align`, `scoring`) are separate from engine and recognizer I/O so FR-010 holds; only `recognizer.py` imports `faster-whisper`, lazily.

## Complexity Tracking

No violations to justify.

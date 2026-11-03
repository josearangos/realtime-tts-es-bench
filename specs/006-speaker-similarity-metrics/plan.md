# Implementation Plan: Speaker Similarity and Consistency Metrics

**Branch**: `006-speaker-similarity-metrics` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/006-speaker-similarity-metrics/spec.md`

## Summary

Add a package `tts_bench.speaker` with a CLI in independent stages, mirroring feature 005: `synthesize` (one cloning engine, one cloned voice, the 21 cloning-subset sentences, N repetitions, WAV files plus a manifest), `embed` (one fixed speaker-embedding model, identical settings, embeddings file for the reference, the synthesized audio and optional extra-voice recordings), `score` (pure computation: cosine similarity, per-engine averages, coefficient of variation, EER, warnings; no model and no engine) and `compare` (Markdown tables with the FR-008 notice). Only `synthesize` needs an engine venv and only `embed` needs the embedding model venv; `score` and `compare` use the standard library plus `numpy`, so every computation is tested with fixed embeddings and no weights (FR-010). See [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/) and [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.11 (repo requires >=3.11)

**Primary Dependencies**: `synthesize`, `score`, `compare`: standard library plus `numpy` (core). `embed` only: `speechbrain` + `torch`/`torchaudio` in its own `.venv-spk`, optional extra `speaker = ["speechbrain", "torchaudio"]`; model `speechbrain/spkrec-ecapa-voxceleb` (192-dimensional ECAPA-TDNN). No scoring, EER or statistics library: own small tested implementations.

**Storage**: audio in `output/speaker/<engine>-<voice>/` (WAV, git-ignored) with `manifest.json`; embeddings are derived voice material and are **not** tracked: `output/speaker/…/embeddings.json` (git-ignored). Tracked results in `results/speaker/` contain only scores, statistics and metadata, never audio, embeddings or reference paths.

**Testing**: pytest in `tests/speaker/` with fixed embedding vectors, a `FakeEmbedder` (scripted vector per audio hash or per tone frequency), the fake engine extended with controlled duration variation, and synthetic WAV files. An `@pytest.mark.engine` test runs the real model in `.venv-spk`.

**Target Platform**: macOS (Apple Silicon) and Linux, CPU

**Project Type**: library plus CLI (`python -m tts_bench.speaker`)

**Performance Goals**: none beyond practicality: scoring takes under a second; embedding time is not a metric.

**Constraints**: local-first (no network after the one-time model download); one engine per process; no engine-specific logic; same embedding model, version and settings for all engines (FR-002); deterministic scoring (SC-005); reference audio and embeddings never committed (Principle VI).

**Scale/Scope**: 2 cloning engines × 21 cloning sentences × N repetitions (default 5) = 210 clips for the real run; about 11 small modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | adds voice fidelity and stability next to TTFA/RTF; cloning support alone does not rank an engine |
| II Spanish by Default | Pass | Spanish cloning sentences and es-CO reference voices; accent label stored; embedding model trained mostly on English/multilingual celebrity speech, stated as a limitation |
| III Apples-to-apples | Pass | same sentences, same reference, same embedding model and settings; `compare` refuses mixed model, version, settings, corpus hash or reference. Repetitions apply to the consistency statistics; the headline similarity uses one designated run (clarification 2026-11-03) |
| IV Deterministic vs human | Pass | every output carries the FR-008 notice (not a substitute for human judgment); no naturalness claim |
| V Honest reporting | Pass | model identity, checkpoint revision, library versions, settings, environment and command stored; the same embedding model for all engines is enforced; limitations (similarity near 1 is not identity, noise, language, prosody) stated |
| VI Licensing/consent | **Pass, with care** | reference audio only through `LocalVoiceLibrary.resolve`; recordings, WAVs and embeddings stay git-ignored (embeddings can identify a speaker, so they are treated like voice material); results hold only scores. Model license and the VoxCeleb training-data terms are recorded and verified when the checkpoint is pinned (task) |
| VII Modular | Pass | stages independent; `score` imports nothing heavy; Piper excluded via `supports_cloning=False`, no engine-specific code |
| VIII Verifiable | Pass | each FR maps to a fixed-embedding test; metric definitions go to `docs/speaker-similarity.md` |

Post-design re-check: no violations; Complexity Tracking not needed. No change to features 001 to 005 is required beyond reading the voice library and corpus.

## Decisions to Confirm Before Task Generation

Proposed defaults (the maintainer may override; see [research.md](research.md)):

1. **Embedding model**: SpeechBrain ECAPA-TDNN `spkrec-ecapa-voxceleb`, pinned revision, 16 kHz mono input, cosine similarity on the raw embedding. Resemblyzer and WeSpeaker considered.
2. **Minimum duration for reliable embeddings**: 3.0 s of audio (shorter audio is flagged `short_audio`, still scored and kept in the average, and the count is shown).
3. **Coefficient of variation**: sample standard deviation (n−1) over mean; declined (marked unreliable) when |mean| < 0.05 in the metric's own unit (seconds for duration, cosine units for similarity), and "not available" with fewer than 2 values. The guard is tested on synthetic data.
4. **High EER and separation margin**: warn above 10% EER; the Spanish gate also requires a separation (mean same − mean different) of at least 0.20; below 2 pairs of either kind, "not available".
5. **Different-speaker pairs** (clarified): reference vs. other voices' recordings (`recordings/` in the voice library) and vs. other engines' outputs for a different voice. With the two consented voices (Valentina, Emiliano) both directions are available.
6. **Reference quality** recorded from the voice library entry: duration, speech seconds, SNR estimate, accent label, warnings (FR-012).
7. **First real run**: phonon with `valentina-phonon`, pocket_tts with `valentina-pocket`, 21 cloning sentences, 5 repetitions, designated run = repetition 1.
8. **Spanish coherence gate**: all reference and generated audio is Spanish (es-CO), so the embedding model must be shown to work on Spanish before its scores are trusted. ECAPA-TDNN is trained mostly on English-dominant VoxCeleb, so this is a check, not an assumption: (a) the EER check on the project's own Spanish pairs is **required, not optional**, for the first real run; (b) results record the audio language (`es`) and the model's training-language note; (c) if EER exceeds 10% **or** the mean similarity of same-speaker pairs does not exceed the mean of different-speaker pairs by at least 0.20 ("clearly" means a separation of 0.20 cosine units, approved 2026-11-03), the run is marked not reliable and a multilingual model (for example a WeSpeaker multilingual checkpoint) replaces ECAPA before any ranking is published. Only Spanish sentences and Spanish reference audio are used; no English fixtures in reported results (Constitution II).

## Project Structure

### Documentation (this feature)

```text
specs/006-speaker-similarity-metrics/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── speaker-cli.md
│   └── results-file.md
├── checklists/requirements.md
└── tasks.md              # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/tts_bench/speaker/
├── __init__.py       # exports cosine_similarity, coefficient_of_variation, equal_error_rate, score_embeddings
├── __main__.py       # CLI: synthesize, embed, score, compare
├── similarity.py     # cosine similarity (pure)
├── variation.py      # coefficient of variation with near-zero-mean and n<2 guards (pure)
├── eer.py            # equal error rate from labeled scores (pure)
├── scoring.py        # per-sentence similarity, per-engine averages, consistency records, warnings (pure)
├── embedder.py       # Embedder protocol, SpeechBrainEmbedder (lazy import), FakeEmbedder
├── synth.py          # cloning-subset synthesis, N repetitions, WAV + manifest (reuses 005 write_pcm16)
├── embed.py          # embedding stage: reference, clips, extra-voice recordings; cache by audio hash + settings hash
├── pairs.py          # builds labeled same/different pairs from the project's own audio
├── files.py          # manifest, embeddings and results files: write/read/schema check
└── compare.py        # merge rules and Markdown tables
docs/
└── speaker-similarity.md  # definitions, thresholds, limitations
results/
└── speaker/               # scores only, tracked
tests/speaker/
├── conftest.py
├── test_similarity.py
├── test_variation.py
├── test_eer.py
├── test_scoring.py
├── test_pairs.py
├── test_exclusions.py         # non-cloning engines excluded, short and silent audio flagged
├── test_pipeline_fake.py
├── test_files_compare.py      # same-model enforcement (SC-002), limitation notice (SC-004)
├── test_determinism.py
├── test_privacy.py            # results hold no embeddings, paths or audio
├── test_embedder_real.py      # engine-marked, runs in .venv-spk
└── test_offline.py
```

**Structure Decision**: single project, one new subpackage beside `corpus`, `voices`, `metrics` and `intelligibility`. Pure functions (`similarity`, `variation`, `eer`, `scoring`) are separate from engine and model I/O so FR-010 holds; only `embedder.py` imports `speechbrain`, lazily. Shared helpers (WAV writing, sha256, environment block) are imported from `tts_bench.intelligibility` rather than copied.

## Complexity Tracking

No violations to justify.

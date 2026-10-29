# Implementation Plan: TTS Engine Adapters

**Branch**: `001-tts-engine-adapters` | **Date**: 2026-10-29 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/001-tts-engine-adapters/spec.md`

**Note**: This template is filled in by the `/speckit-plan` command; its definition describes the execution workflow.

## Summary

Provide one adapter interface (load, synthesize, stream, descriptor) behind a name registry, with thin adapters for Phonon, Pocket TTS, and Piper plus a configurable fake engine. Each adapter declares its streaming granularity, stamps chunk arrival times, never resamples, and reports actionable errors. Engine dependencies are optional extras expected to live in separate virtual environments. See [research.md](research.md) for engine facts (vendor-published, partly unverified).

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: core: numpy only; engines (optional extras): `ptts` (Phonon), `pocket-tts` (Pocket TTS), `piper-tts` (Piper)

**Storage**: N/A (voices come from the feature 003 library; WAV files written by the smoke tool)

**Testing**: pytest; contract tests parametrized over the fake engine and, when installed, real engines (marked `engine`)

**Target Platform**: macOS and Linux, CPU-only

**Project Type**: library (core package plus per-engine adapters)

**Performance Goals**: adapter overhead must not distort measurements; chunk timestamps taken on receipt with a monotonic clock

**Constraints**: local-first after download; one engine per process; no silent resampling or text rewriting; no weights or voices committed

**Scale/Scope**: 3 real adapters plus 1 fake; roughly a dozen small modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | chunk arrival timestamps support TTFA |
| II Spanish by default | Pass | accent stated per descriptor; Colombian goal, closest-accent labeling where impossible |
| III Apples-to-apples | Pass | one engine per process enforced; load time separate from synthesis; "not available" for non-streaming |
| IV Deterministic vs human | N/A | no evaluation here |
| V Honest reporting | Pass | vendor facts labeled unverified; versions recorded in descriptor |
| VI Licensing/consent | Pass, flagged | Phonon CC BY-NC (non-commercial); Piper GPL-3.0 (copyleft); `cloned_voices/` and weights git-ignored; cloning needs consented references with source and licence recorded |
| VII Modular | Pass | core has no engine deps; adding an engine = adapter + one registration |
| VIII Verifiable | Pass | fake engine, contract tests per requirement |

Post-design re-check: no violations; Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/[###-feature]/
├── plan.md              # This file (/speckit-plan command output)
├── research.md          # Phase 0 output (/speckit-plan command)
├── data-model.md        # Phase 1 output (/speckit-plan command)
├── quickstart.md        # Phase 1 output (/speckit-plan command)
├── contracts/           # Phase 1 output (/speckit-plan command)
└── tasks.md             # Phase 2 output (/speckit-tasks command - NOT created by /speckit-plan)
```

### Source Code (repository root)

```text
src/tts_bench/
├── core/
│   ├── adapter.py        # EngineAdapter protocol, base class with guard + timing helpers
│   ├── descriptor.py     # EngineDescriptor, StreamingInfo, InputLimits
│   ├── audio.py          # AudioChunk, SynthesisResult
│   ├── errors.py
│   ├── registry.py       # name -> "module:Class", lazy import
│   └── voices.py         # VoiceReference, VoiceLibrary protocol (003 boundary)
├── adapters/
│   ├── fake.py
│   ├── phonon.py
│   ├── pocket_tts.py
│   └── piper.py
└── smoke.py              # python -m tts_bench.smoke <engine> --voice <name>

tests/
├── contract/             # one suite run against every adapter
├── integration/          # real engines, skipped if not installed
└── unit/
pyproject.toml            # extras: phonon, pocket, piper, dev
```

**Structure Decision**: single Python library; engine libraries are optional extras imported lazily inside each adapter's `load()`.

## Complexity Tracking

No constitution violations; nothing to justify.

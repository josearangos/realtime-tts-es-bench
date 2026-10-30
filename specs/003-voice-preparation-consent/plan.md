# Implementation Plan: Voice Preparation and Consent

**Branch**: `003-voice-preparation-consent` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/003-voice-preparation-consent/spec.md`

## Summary

Add a local voice library (`tts_bench.voices`) that replaces the temporary `DirectoryVoiceLibrary` from feature 001. It stores consent records, registers prepared voice files by name with engine, checksum, source recording and consent, and resolves them by name with consent-use, engine-match and integrity checks. A small CLI prepares reference segments, registers externally created voice files (Phonon), assigns Piper's fixed voice, withdraws consent in one action, and checks the repository for leaked voice material. See [research.md](research.md) for the decisions and [contracts/voice-library.md](contracts/voice-library.md) for the interface.

## Technical Context

**Language/Version**: Python 3.11

**Primary Dependencies**: standard library only (`wave`, `hashlib`, `json`, `shutil`, `subprocess` for the git check) plus `numpy`, already a core dependency. No engine dependency, so the library runs in the core venv without weights.

**Storage**: files under the git-ignored `cloned_voices/` (index `library.json`, `consent/`, `recordings/`, `voices/`, `generated/`)

**Testing**: pytest in `tests/voices/`, using the fake engine and synthetic WAVs generated in the test (no real voice, no weights)

**Target Platform**: macOS and Linux, CPU-only

**Project Type**: library plus CLI (`python -m tts_bench.voices`)

**Performance Goals**: not latency-relevant. `resolve` hashes the voice file, so callers MUST resolve before a timed region, never inside it.

**Constraints**: local-first; WAV input only (16-bit PCM); no new dependency; nothing sensitive in tracked files; engines never see unregistered paths

**Scale/Scope**: a handful of speakers and voices (tens at most); about 8 small modules; initial voices: Phonon 1, Pocket TTS 2, Piper 2

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | resolution happens outside timed regions; documented in the contract |
| II Spanish by default | Pass | recording accent and engine variant recorded; mismatch warned |
| III Apples-to-apples | Pass | one recording id shared by Phonon and Pocket TTS; checkable for reports (SC-002) |
| IV Deterministic vs human | N/A | no evaluation here |
| V Honest reporting | Pass | segment, checksum, warnings and recording id are stored for reports; engine reference-length advice labeled unverified |
| VI Licensing/consent | Pass | consent required to prepare or register a cloned voice; use checked at resolve; voice material git-ignored and checked in tests; withdrawal is one action |
| VII Modular | Pass | library is independent of adapters, metrics, backend and frontend; they only call `resolve` |
| VIII Verifiable | Pass | every FR maps to a fake-engine test with synthetic audio |

Post-design re-check: no violations; Complexity Tracking not needed.

## Project Structure

### Documentation (this feature)

```text
specs/003-voice-preparation-consent/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── voice-library.md
├── checklists/requirements.md
└── tasks.md              # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/tts_bench/
├── core/
│   ├── voices.py          # keeps VoiceReference and the VoiceLibrary Protocol; DirectoryVoiceLibrary removed
│   └── errors.py          # + consent, engine-mismatch, integrity, duplicate-name errors
├── voices/
│   ├── __init__.py        # exports LocalVoiceLibrary
│   ├── __main__.py        # CLI: consent, add-recording, prepare, register, assign-fixed, list, show, verify, remove, withdraw, check-repo
│   ├── consent.py         # ConsentRecord load/validate/permits
│   ├── library.py         # LocalVoiceLibrary: register, resolve, remove, withdraw, public_index
│   ├── audio_check.py     # WAV read, segment trim, speech-length and noise estimate
│   ├── prepare.py         # per-engine preparation (segment extraction, manual-step instructions)
│   └── repocheck.py       # tracked-file and history scan for voice material
├── smoke.py               # switched to LocalVoiceLibrary, passes engine name
docs/
└── voice-preparation.md   # per-engine creation steps (FR-004), committed, no voice material
tests/voices/
├── conftest.py            # synthetic WAV factory, temporary library root
├── test_audio_check.py
├── test_consent.py
├── test_consent_use.py
├── test_library_register_resolve.py
├── test_engine_mismatch_and_integrity.py
├── test_prepare_segments_and_warnings.py
├── test_remove_and_withdraw.py
├── test_repocheck.py
└── test_no_hardcoded_paths.py
.gitignore                 # + *.onnx, *.pt, *.ckpt (voice and model files)
```

**Structure Decision**: single project, one new subpackage `tts_bench.voices` next to `core`, `corpus` and `adapters`. The `VoiceLibrary` Protocol stays in `core` so adapters depend only on `core`; the implementation lives in `voices` so adapters never import it.

## Complexity Tracking

No Constitution Check violations.

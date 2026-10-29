---

description: "Task list for TTS Engine Adapters"
---

# Tasks: TTS Engine Adapters

**Input**: Design documents from `/specs/001-tts-engine-adapters/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/adapter-interface.md, quickstart.md

**Tests**: Included. Constitution Principle VIII requires measurement code to be testable with a fake engine, and each requirement must map to a checkable scenario.

**Organization**: Grouped by user story. Paths follow plan.md (`src/tts_bench/`, `tests/`).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1 (all three engines through one interface), US2 (honest streaming declaration), US3 (add an engine with minimal code)

---

## Phase 1: Setup

- [ ] T001 Create the package layout from plan.md: `src/tts_bench/core/`, `src/tts_bench/adapters/`, `tests/contract/`, `tests/integration/`, `tests/unit/` with `__init__.py` files
- [ ] T002 Create `pyproject.toml` (Python >=3.11, core dependency `numpy` only) with optional extras `phonon` (`ptts`), `pocket` (`pocket-tts`), `piper` (`piper-tts`), and `dev` (`pytest`); no engine library in the core dependencies (FR-009)
- [x] T003 Download the Phonon Spanish model from Hugging Face (`gradium/phonon-40m-es`) into `phonon-40m-es/` at the repo root so it works offline; the directory is git-ignored
- [x] T004 [P] Add (already added; just verify) `.gitignore` entries for `.venv-*`, `*.wav`, `cloned_voices/`, `phonon-40m-es/`, `*.safetensors`, and model weights (Constitution Principle VI: nothing derived from voices or weights is committed)
- [ ] T005 [P] Configure pytest in `pyproject.toml` with an `engine` marker for tests that need a real installed engine

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: contract types, errors, registry, guard, and the fake engine

- [ ] T006 [P] Define `StreamingInfo` in `src/tts_bench/core/descriptor.py` with `granularity`: `chunk` | `sentence` | `none`, and `InputLimits` with `max_chars: int or None`
- [ ] T007 Define frozen `EngineDescriptor` in `src/tts_bench/core/descriptor.py` with fields name, engine_version, model_id, license_code, license_model, license_flags (list of str, e.g. `non-commercial`, `copyleft`), language (`es`), spanish_variant (accent actually produced), voice_kind (`catalog_name` | `reference_audio` | `stored_voice_file` | `fixed_voice`), supports_cloning, streaming, input_limits, install_hint, weights_hint (FR-003, FR-007)
- [ ] T008 [P] Define `AudioChunk` (samples, sample_rate, channels, produced_at_ns, index) and `SynthesisResult` (audio, sample_rate, request_started_ns, first_audio_ns that is None when granularity is `none`, finished_ns, chunks, descriptor) in `src/tts_bench/core/audio.py`; no resampling anywhere (FR-006)
- [ ] T009 [P] Define errors in `src/tts_bench/core/errors.py`: `EngineNotInstalledError`, `WeightsMissingError`, `EngineAlreadyLoadedError`, `InputLimitError`, `SynthesisError` (carries optional partial chunks for diagnosis only), `VoiceNotFoundError`, `StreamingNotSupportedError`; each message includes an actionable hint where relevant (FR-008)
- [ ] T010 [P] Define `VoiceReference` (name, kind, path_or_id) and the `VoiceLibrary` protocol (`resolve(name, kind)` raising `VoiceNotFoundError`) in `src/tts_bench/core/voices.py`, plus an in-memory test library in `tests/conftest.py` until feature 003 exists (FR-011)
- [ ] T011 Implement a temporary `DirectoryVoiceLibrary` in `src/tts_bench/core/voices.py` rooted at `cloned_voices/`: it reads a git-ignored `cloned_voices/voices.toml` (create it locally) mapping each name and kind to a file (`valentina` + `stored_voice_file` -> `valentina.safetensors`; `valentina` and `emiliano` + `reference_audio` -> the two es-CO `.wav` files; the chosen es_MX voice + `fixed_voice`), raises `VoiceNotFoundError` for unknown names, and is replaced by feature 003's library without changing any adapter (FR-011)
- [ ] T012 Implement `EngineAdapter` protocol and a base class in `src/tts_bench/core/adapter.py`: one-engine-per-process guard in `load()` raising `EngineAlreadyLoadedError` (FR-013), `InputLimitError` check before calling the engine with text passed unchanged (FR-015), `time.perf_counter_ns()` stamping helpers, and wrapping engine exceptions into `SynthesisError` (FR-012); `close()` releases the guard so tests and tools can load another engine afterwards (FR-013)
- [ ] T013 Implement the registry in `src/tts_bench/core/registry.py`: `register(name, "module:Class")` and `get_adapter(name)` with lazy import; unknown names list registered names
- [ ] T014 Implement `FakeAdapter` in `src/tts_bench/adapters/fake.py` with configurable granularity, first_chunk_delay_s, chunk_interval_s, audio_seconds, sample_rate, producing deterministic audio with exact timings (FR-010, SC-004); register it as `fake`
- [ ] T015 Register `fake`, `phonon`, `pocket_tts`, and `piper` in `src/tts_bench/adapters/__init__.py` as one-line `register(...)` calls (module paths as strings, so the adapter files may not exist yet), with each adapter importing its engine library only inside `load()`
- [ ] T016 [P] Unit tests for the base-class guard, input limits, and error wrapping using the fake engine in `tests/unit/test_adapter_base.py`

**Checkpoint**: foundation ready, user stories can start

---

## Phase 3: User Story 1 - Run all three engines through one interface (P1) MVP

**Goal**: select an engine by name and get Spanish audio plus its native sample rate.

**Independent Test**: for each installed engine, synthesize one short Spanish sentence and get playable audio with a recorded sample rate.

- [ ] T017 [P] [US1] Contract test suite in `tests/contract/test_adapter_contract.py`, parametrized over adapters: `synthesize` returns non-empty audio, a native `sample_rate`, a complete descriptor, and never alters the sample rate (FR-001, FR-006, FR-007); runs on `fake` by default; each adapter is exercised in its own `try/finally` that calls `close()`, so the one-engine guard does not break the shared test process
- [ ] T018 [P] [US1] Integration test `tests/integration/test_real_engines.py` (marker `engine`, skipped when the engine is not installed) running the same contract against `phonon`, `pocket_tts`, `piper` with one Spanish sentence (SC-001)
- [ ] T019 [P] [US1] Implement `PhononAdapter` in `src/tts_bench/adapters/phonon.py`: `ptts.TTS("./phonon-40m-es", lang="es")` (local model directory; no `quant` argument, exactly as in the owner's script), register the stored voice with `tts.add_voice(name, path)` where the path comes from the voice library (`valentina` -> `cloned_voices/valentina.safetensors`), native 24 kHz; descriptor flags `non-commercial` (CC BY-NC 4.0), `supports_cloning=True`, voice_kind `stored_voice_file`, accent Colombian; `weights_hint` explains how to place the model at `./phonon-40m-es`; first confirm the owner's cloning script runs and record the result in research.md (FR-002, FR-003); if the owner's cloning script does not run with the downloaded model, stop and report the failure; do not fall back silently to a catalog voice, because FR-003 requires a Colombian voice
- [ ] T020 [P] [US1] Implement `PocketTTSAdapter` in `src/tts_bench/adapters/pocket_tts.py`: `TTSModel.load_model()`, `get_state_for_audio_prompt(...)`, `generate_audio(...)`, rate from `tts_model.sample_rate`; first inspect the installed package to resolve the unverified items in research.md (Spanish selection from Python, streaming method, software license) and record the findings in the descriptor and research.md; `supports_cloning=True`, voice_kind `reference_audio`, with the two Colombian references `es-CO_B2_-_Valentina_-_Gentle_Service_v1_sample.wav` and `es-co-b2-04-emiliano_sample.wav` from `cloned_voices/` resolved by name from the voice library (FR-002, FR-011)
- [ ] T021 [P] [US1] Implement `PiperAdapter` in `src/tts_bench/adapters/piper.py`: `PiperVoice.load(<.onnx>)`, `synthesize()` chunks with their own `sample_rate`; descriptor flags `copyleft` (GPL-3.0), voice_kind `fixed_voice`, `supports_cloning=False`, a Mexican Spanish (es_MX) voice (owner's choice; pick one and record its name and licence), resolved from the voice library, accent labeled as the closest to Colombian, not Colombian, and a hint to run `python3 -m piper.download_voices <name>` when missing (FR-002, FR-008)
- [ ] T022 [US1] Add the smoke tool `src/tts_bench/smoke.py` (`python -m tts_bench.smoke <engine> --voice <name> [--text ...] [--out file.wav]`) that prints the descriptor and declared granularity and writes a WAV at the engine's native rate (quickstart.md step 2)
- [ ] T023 [US1] Run the smoke tool for each engine in its own virtual environment and record the actual accent heard, installed versions, and license findings in the descriptors and `research.md` (labeled as measured here vs vendor-published)

**Checkpoint**: US1 delivers the MVP, three engines behind one interface

---

## Phase 4: User Story 2 - Declare streaming capability honestly (P1)

**Goal**: every engine declares whether audio arrives incrementally and at what granularity; chunk times are stamped on receipt.

**Independent Test**: fake engine in `chunk`, `sentence`, and `none` modes reports the matching granularity, exposes chunks as produced, and reports time to first audio as not available for `none`.

- [ ] T024 [P] [US2] Contract tests in `tests/contract/test_streaming_contract.py`: `chunk` and `sentence` fakes yield chunks with monotonically increasing `produced_at_ns` matching the configured delays within ±20 ms; `none` fake has `first_audio_ns` of None and `stream()` raises `StreamingNotSupportedError` (FR-004, FR-005, FR-014)
- [ ] T025 [US2] Implement `stream()` and the per-chunk timing in the base class in `src/tts_bench/core/adapter.py`: stamp `produced_at_ns` when each chunk is received from the engine and `request_started_ns` immediately before the engine call; `first_audio_ns` is the first playable audio at the declared granularity (FR-014)
- [ ] T026 [P] [US2] Wire streaming for `PhononAdapter` in `src/tts_bench/adapters/phonon.py` using `tts.stream(...)` (declared `chunk`)
- [ ] T027 [P] [US2] Wire streaming for `PiperAdapter` in `src/tts_bench/adapters/piper.py` using the `synthesize()` chunk iterator (declared `sentence`; confirm chunk boundaries and update the declaration if they differ)
- [ ] T028 [US2] Wire streaming for `PocketTTSAdapter` in `src/tts_bench/adapters/pocket_tts.py` only after T020 confirms a streaming method; otherwise declare `none` and document why (SC-003)
- [ ] T029 [US2] Test that failures mid-stream raise `SynthesisError` carrying partial chunks and are never returned as a successful result in `tests/contract/test_failure_contract.py` (FR-012)
- [ ] T030 [US2] Test that each real adapter's declared granularity is a fixed constant of the descriptor, never computed from a run, in `tests/unit/test_declared_streaming.py` (SC-003)

**Checkpoint**: US1 and US2 both work independently

---

## Phase 5: User Story 3 - Add another engine with minimal code (P2)

**Goal**: a contributor adds an engine with one adapter file and one registration; missing dependencies give clear messages.

**Independent Test**: register a throwaway adapter and run it through the contract suite with no other changes.

- [ ] T031 [P] [US3] Test in `tests/unit/test_registry.py` that registering a new adapter name makes it usable via `get_adapter` and the contract suite unchanged, and that unknown names list the registered ones (SC-002)
- [ ] T032 [P] [US3] Test in `tests/unit/test_missing_deps.py` that selecting an engine whose library or weights are missing raises `EngineNotInstalledError` / `WeightsMissingError` with the descriptor's `install_hint` / `weights_hint`, and that the other engines still load (FR-008, FR-009)
- [ ] T033 [US3] Test in `tests/unit/test_one_engine_per_process.py` that loading a second engine in the same process raises `EngineAlreadyLoadedError` (FR-013), and that after `close()` a different engine can load
- [ ] T034 [US3] Write `docs/adding-an-engine.md` following quickstart.md step 4 (copy `fake.py`, implement the contract, one `register(...)` line, run the contract suite)

**Checkpoint**: all user stories independently functional

---

## Phase 6: Polish & Cross-Cutting

- [ ] T035 [P] Document per-engine voice meaning, Spanish accent, license flags (Phonon non-commercial, Piper copyleft), and how to obtain weights in `docs/engines.md` (Constitution Principle VI, FR-003)
- [ ] T036 [P] Note in `docs/engines.md` that Phonon and Pocket TTS use cloned Colombian voices while Piper uses a Latin American voice whose results must be labeled with the closest accent, and note that the project owner confirmed the voices in `cloned_voices/` are authorized (consent, Principle VI); record each file's source in the docs, and its licence if known
- [ ] T037 Run the full quickstart.md validation (fake suite, each real engine in its own venv, three failure paths) and fix gaps

---

## Dependencies & Execution Order

- Phase 1 -> Phase 2 -> Phases 3-5 -> Phase 6.
- US1 and US2 both need Phase 2; T025 (stream in the base class) must finish before T026-T028. T026-T028 also need their adapters from T019-T021.
- US3 tests (T031, T032, T033) need only Phase 2; registration (T015) is in Phase 2 and does not need the adapter files.
- T020 must finish before T028.
- Real adapters and the smoke tool (T019-T023) need the voice library (T010, T011) and the registration (T015).

## Parallel Opportunities

- Phase 2: T006, T008, T009, T010 in parallel.
- US1: T017, T018, T019, T020, T021 in parallel (separate files).
- US2: T024, T026, T027 in parallel.
- US3: T031, T032 in parallel.

## Implementation Strategy

- **MVP**: Phases 1-3 (US1) with the fake engine plus at least one real engine.
- Then add US2 (streaming timing, the key real-time metric), then US3 and polish.

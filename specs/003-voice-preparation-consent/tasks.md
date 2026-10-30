---

description: "Task list for Voice Preparation and Consent"
---

# Tasks: Voice Preparation and Consent

**Input**: Design documents from `/specs/003-voice-preparation-consent/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/voice-library.md, quickstart.md

**Tests**: Included. Constitution Principle VIII requires every functional requirement to map to a checkable scenario. All tests use synthetic WAVs and the fake engine: no real voice, no weights.

**Organization**: Grouped by user story. Paths follow plan.md (`src/tts_bench/voices/`, `tests/voices/`). All three P1 stories depend on each other's building blocks, so phases follow dependency order, not story number: consent gate (US3) → library (US2) → preparation (US1) → withdrawal (US3) → repository safety (US4).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1 (one recording for every cloning engine), US2 (voice library by name), US3 (block cloning without consent, and withdrawal), US4 (voice material out of git)

---

## Phase 1: Setup

- [X] T001 Create the package `src/tts_bench/voices/` with an empty `__init__.py` and the test package `tests/voices/__init__.py` (layout from plan.md)
- [X] T002 [P] Add `*.onnx`, `*.pt` and `*.ckpt` to `.gitignore` next to the existing voice entries (`cloned_voices/`, `*.wav`, `*.safetensors`); verify with `git check-ignore -v` that `cloned_voices/library.json` and `cloned_voices/voices/x/y.wav` are ignored (FR-007)

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: errors, shared types, audio analysis, consent type, index storage, test fixtures

- [X] T003 [P] Add to `src/tts_bench/core/errors.py`, all subclasses of `TTSBenchError`: `ConsentRequiredError`, `ConsentNotPermittedError` (message names the missing permission), `VoiceEngineMismatchError` (message names both engines), `VoiceIntegrityError` (attribute `reason` is `"missing"` or `"modified"`; message includes expected and actual checksum for `"modified"`), `VoiceAlreadyRegisteredError`
- [X] T004 [P] Implement `src/tts_bench/voices/audio_check.py`: read 16-bit PCM WAV only with the standard `wave` module (any other format raises a clear error saying to convert to 16-bit PCM WAV), downmix to mono, 30 ms frames with RMS level in dBFS; noise floor = 10th percentile; speech frames = level ≥ noise floor + 10 dB; return `sample_rate`, `duration_s`, `speech_seconds`, and `snr_estimate_db` = 90th − 10th percentile level; `warnings(analysis, noise_threshold_db=20.0)` returns `too_short` when `speech_seconds` < 10 and `noisy` when `snr_estimate_db` < `noise_threshold_db`; `write_segment(src, dst, start_s, length_s)` writes the trimmed WAV with the same sample rate and clamps to the file duration (FR-005, FR-006)
- [X] T005 [P] Implement `ConsentRecord` in `src/tts_bench/voices/consent.py` with JSON load/save and validation: `alias` is a pseudonym matching `[a-z0-9_-]+`, unique, no real name; `date` is `YYYY` or `YYYY-MM-DD`; `permitted_uses` is non-empty and each value is one of `internal_benchmarking`, `published_results`, `published_demo_audio`, `human_evaluation`; `allowed_content` is non-empty and each value is one of `outbound_sales`, `collections`, `inbound`, `cloning_prompts`; `notes` optional with no personal identifiers; add `permits(use, content)` returning the name of the first missing permission or `None` (FR-002)
- [X] T006 Implement the `LocalVoiceLibrary` storage skeleton in `src/tts_bench/voices/library.py`: root layout (`library.json`, `consent/`, `recordings/`, `voices/`, `generated/`), `library.json` shaped `{"version": 1, "recordings": {}, "voices": {}, "withdrawn": []}`, atomic save (write temp file, then rename), sha256 helper, and voice-name validation (non-empty, `[A-Za-z0-9_-]+`, uppercase allowed because Piper voices are registered under their real voice id, e.g. `es_MX-claude-high`: the Piper adapter derives accent, model id and licence from the voice name); a missing or unreadable index yields an empty library and never substitutes another voice (spec edge case)
- [X] T007 Extend the `VoiceLibrary` Protocol in `src/tts_bench/core/voices.py`: `resolve(name, kind=None, *, engine=None, use=None, content=None) -> VoiceReference`; keep `DirectoryVoiceLibrary` until T020; update the in-memory test library in `tests/conftest.py` to accept the new keyword arguments
- [X] T008 [P] Create `tests/voices/conftest.py` with a synthetic WAV factory (sine "speech" bursts of a given total seconds over a configurable noise floor, 16-bit PCM, 24 kHz) and a `library` fixture that builds a `LocalVoiceLibrary` on `tmp_path`

**Checkpoint**: foundation ready, user stories can start

---

## Phase 3: User Story 3 - Block cloning without consent (Priority: P1)

**Goal**: no recording enters the library, and so no voice can be prepared, without a consent record.

**Independent Test**: call `add_recording` for a speaker with no consent record; it refuses with "consent required" and writes nothing.

- [X] T009 [P] [US3] Tests in `tests/voices/test_consent.py`: invalid records are rejected (empty `permitted_uses`, unknown use value, alias with spaces or uppercase, date `2025-13-40`), `date` accepts both `2025` and `2025-06-01`, `permits()` names the missing permission, and `add_recording` without a consent record raises `ConsentRequiredError` and creates no file under `recordings/` (FR-001, FR-002)
- [X] T010 [US3] Implement `add_consent` and `add_recording` in `src/tts_bench/voices/library.py`: `add_recording(wav, consent_id, accent, no_music_confirmed=False)` raises `ConsentRequiredError` (message: consent required, run `consent add --alias …`) before copying anything; otherwise copies the WAV to `recordings/<recording_id>.wav` where `recording_id` is `rec-` + first 12 hex of the file's sha256, stores sample rate, duration, `speech_seconds`, `snr_estimate_db`, `accent`, `consent_id`, `added`, and `warnings` from T004 plus `music_not_ruled_out` when `no_music_confirmed` is false (FR-001, FR-006)
- [X] T011 [US3] CLI in `src/tts_bench/voices/__main__.py` with `--root` (default `cloned_voices`): `consent add --alias --date --uses --content` (exit 2 when invalid) and `add-recording FILE.wav --consent --accent [--no-music-confirmed] [--noise-threshold-db]` (prints `recording_id` and warnings; exit 1 on refusal); every refusal prints a one-line reason and the corrective command

**Checkpoint**: consent gate works on its own

---

## Phase 4: User Story 2 - Register voice files and resolve them by name (Priority: P1)

**Goal**: any prepared voice file is registered once and then used by name, with engine, integrity and consent-use checks.

**Independent Test**: register a sample voice for the fake engine, resolve it by name and obtain its location, engine and metadata; then request it for another engine and see the refusal.

- [X] T012 [P] [US2] Tests in `tests/voices/test_library_register_resolve.py`: registering a cloned voice stores `name`, `engine`, `kind`, `cloned`, `file`, `owned`, `sha256`, `recording_id`, `consent_id`, `segment`, `creation`, `accent_label`, `warnings`, `created` (FR-008, FR-011); a cloned registration without `recording_id`, `consent_id` or `segment` is refused; a fixed voice registers with no consent, recording or segment (FR-010); a Piper voice registered under a name different from its voice id is refused; `resolve` returns the absolute path; unknown names raise `VoiceNotFoundError` listing known names; a second registration of an existing name raises `VoiceAlreadyRegisteredError`; `public_index()` has only `name, engine, kind, cloned, accent_label, sha256, recording_id` and no paths (FR-015); `same_source` is true for two voices from one recording, true for a single cloned voice, and false for voices from different recordings or when a fixed voice is included
- [X] T013 [P] [US2] Tests in `tests/voices/test_engine_mismatch_and_integrity.py` using the fake engine name: resolving with a different `engine` raises `VoiceEngineMismatchError` naming both engines; a different `kind` is refused the same way; deleting the file raises `VoiceIntegrityError` with `reason="missing"`; appending a byte raises it with `reason="modified"`; deleting the consent file of a cloned voice raises `ConsentRequiredError`; `verify` over several voices reports every bad one (FR-013, FR-014)
- [X] T014 [P] [US2] Tests in `tests/voices/test_consent_use.py`: with consent `permitted_uses=[internal_benchmarking]`, `resolve(..., use="published_results")` raises `ConsentNotPermittedError` naming `published_results`; same for a `content` value not in `allowed_content`; a permitted `use` and `content` resolves; a `use` or `content` value outside the allowed vocabulary (for example `publish_results`) raises `ConsentNotPermittedError` naming the invalid value; calling without `use` resolves (opt-in check) (FR-016)
- [X] T015 [US2] Implement `register` and `register_fixed` in `src/tts_bench/voices/library.py`: `register` copies the file into `voices/<name>/` (`owned=true`) and checksums the copy; for a cloned voice, require an existing consent record and a registered recording whose `consent_id` matches, and a `segment` of `{start_s, length_s}`; refuse an existing or withdrawn name with `VoiceAlreadyRegisteredError`; `register_fixed` stores `cloned=false`, `recording_id=null`, `consent_id=null`, `segment=null`, and for a voice that is a file it references the existing path in place (`owned=false`) and checksums it, otherwise it stores the plain voice id (FR-008, FR-010, FR-011)
- [X] T016 [US2] Implement `resolve` with the check order from contracts/voice-library.md (name → engine and kind → consent exists → use and content → file exists and sha256 matches), returning `core.voices.VoiceReference` with an absolute path or the plain voice id (FR-012, FR-013, FR-014, FR-016)
- [X] T017 [US2] Implement `public_index`, `same_source` (false if any named voice has no `recording_id`, such as a fixed voice; true for a single cloned voice or for several from one recording), `verify(name=None)` (returns every failure instead of stopping at the first), and `show` data in `src/tts_bench/voices/library.py`
- [X] T018 [US2] CLI commands `register NAME --engine --kind --file --recording --start --length --creation --accent`, `assign-fixed NAME --engine --voice --accent` (for `piper`, NAME must equal `--voice`, otherwise exit 2 with that reason), `list [--json]` (public view), `show NAME`, `verify [NAME]` (exit 1 on any missing or modified file) in `src/tts_bench/voices/__main__.py`
- [X] T019 [US2] Switch `src/tts_bench/smoke.py` from `DirectoryVoiceLibrary` to `LocalVoiceLibrary`, passing `engine=<descriptor name>` and the descriptor `voice_kind` to `resolve`; keep `--voices-dir` as the library root
- [X] T020 [US2] Remove `DirectoryVoiceLibrary` and its `voices.toml` handling from `src/tts_bench/core/voices.py` and update every test or doc that references it (`grep -rn "DirectoryVoiceLibrary\|voices.toml" src tests docs specs/001-tts-engine-adapters`); adapters stay unchanged
- [X] T021 [P] [US2] Test in `tests/voices/test_no_hardcoded_paths.py` (SC-005): no file under `src/tts_bench/` outside `voices/` and `smoke.py` contains a literal `cloned_voices`, `.safetensors` or `voices.toml`

**Checkpoint**: voices register and resolve by name; consent, engine and integrity checks enforced

---

## Phase 5: User Story 1 - One reference recording for every cloning engine (Priority: P1)

**Goal**: Phonon `valentina` and Pocket TTS `valentina` come from the same recording; Pocket TTS `emiliano` comes from its own; Piper gets two fixed voices.

**Independent Test**: prepare a Pocket TTS and a Phonon voice from one synthetic recording and confirm both entries share the same `recording_id` and record their own segment.

- [X] T022 [P] [US1] Tests in `tests/voices/test_audio_check.py`: a 6 s speech recording warns `too_short`; a 12 s recording does not; a recording with a high noise floor warns `noisy` and a clean one does not; a non-16-bit WAV raises the convert-to-16-bit error; `write_segment` clamps to the file length (FR-005, FR-006)
- [X] T023 [P] [US1] Tests in `tests/voices/test_prepare_segments_and_warnings.py`: preparing `pocket_tts` writes the default segment (start 0, length `min(20, duration)`) and registers a `reference_audio` voice with that segment recorded; `--start` and `--length` override and are recorded; preparing `phonon` writes the segment, registers nothing and returns the manual steps text; a voice for `phonon` and one for `pocket_tts` from the same recording have equal `recording_id` and `same_source` is true; adding a voice from a second recording makes `same_source` false; `accent_mismatch:<engine>` is added only when the recording accent and the engine's known primary variant are both known and differ; preparing without consent is refused (FR-003, FR-005, SC-002)
- [X] T024 [US1] Implement `prepare_segment` in `src/tts_bench/voices/library.py` and `src/tts_bench/voices/prepare.py`: default segment starts at 0 and lasts `min(20, duration)` seconds; both values are returned and stored per voice; a table `ENGINE_PRIMARY_VARIANT` maps engine name to its known primary Spanish variant and defaults to `unknown` (labeled unverified in a comment); `prepare_for_engine(recording_id, engine, name, start_s, length_s)` for `pocket_tts` writes the segment under `voices/<name>/reference.wav` and registers it with `creation="automated"`; for `phonon` writes `voices/<name>/phonon-input.wav` and returns the instructions text without registering (FR-003, FR-004, FR-005)
- [X] T025 [US1] CLI command `prepare REC --engine --name [--start --length]` in `src/tts_bench/voices/__main__.py`; for `phonon` print the studio.gradium.ai steps and the exact `register …` command to run afterwards
- [X] T026 [US1] Update `docs/voice-preparation.md` so every command and flag matches the implemented CLI exactly (FR-004)

**Checkpoint**: preparation produces per-engine voices from one recording with documented steps

---

## Phase 6: User Story 3 (continued) - Remove a voice and withdraw consent (Priority: P1)

**Goal**: one documented action removes a voice, or every voice of a speaker, together with the audio generated with it.

**Independent Test**: register two voices of one speaker, create a generated-audio file and a result JSON naming the voice, run `withdraw`, and confirm only the tombstone and the marked result remain.

- [X] T027 [P] [US3] Tests in `tests/voices/test_remove_and_withdraw.py`: `remove` deletes `voices/<name>/`, `generated/<name>/` and the index entry but never a file with `owned=false`, writes a tombstone, marks result files and blocks reuse of the name; `withdraw <alias>` removes all voices of the alias, the recording copy, the consent file and writes a tombstone `{name, recording_id, date}` per voice; result JSON files whose `voice.name` is withdrawn get `"voice_withdrawn": true` with every other field byte-for-byte unchanged; a missing results directory is not an error; re-registering a withdrawn name raises `VoiceAlreadyRegisteredError`; `resolve` of a withdrawn name raises `VoiceNotFoundError`; the report counts voices, files and marked results (FR-009, SC-004)
- [X] T028 [US3] Implement `remove` and `withdraw(consent_id, results_dir=None)` in `src/tts_bench/voices/library.py`, returning `WithdrawReport` (voices removed, files deleted, results marked, tombstones written); the result scan reads `*.json` under the results directory (default `results/`) and only rewrites files that contain a `voice` object whose `name` is withdrawn (FR-009)
- [X] T029 [US3] CLI commands `remove NAME` and `withdraw ALIAS [--results-dir results]` in `src/tts_bench/voices/__main__.py`, printing the report

**Checkpoint**: removal and withdrawal work in one command

---

## Phase 7: User Story 4 - Keep voice material out of version control (Priority: P2)

**Goal**: voice material cannot be committed by default, and a check flags it if someone tries.

**Independent Test**: in a temporary git repository with this project's `.gitignore`, create voice files and confirm they are ignored; force-add one and confirm `check-repo` fails.

- [X] T030 [P] [US4] Tests in `tests/voices/test_repocheck.py` using a temporary `git init` repository: `cloned_voices/library.json`, `a.wav`, `a.safetensors`, `a.onnx` are ignored by the copied `.gitignore`; `git add -f` of any of them makes `check_repo` fail and name the file; a file that was added in an earlier commit and later deleted is still flagged through history (SC-003); a clean repository passes (FR-007)
- [X] T031 [US4] Implement `src/tts_bench/voices/repocheck.py`: scan `git ls-files` and `git log --all --name-only --diff-filter=A --pretty=format:` for paths under `cloned_voices/` or ending `.wav`, `.safetensors`, `.onnx`, `.pt`, `.ckpt`; return the offending paths; nothing is deleted or rewritten
- [X] T032 [US4] CLI command `check-repo` in `src/tts_bench/voices/__main__.py` (exit 0 clean, 1 with the list of paths); add a short "use as pre-commit" note to `docs/voice-preparation.md` (the user installs the hook; no tool modifies git config)

**Checkpoint**: all user stories independently functional

---

## Phase 8: Polish and cross-cutting

- [X] T033 Run the full suite in the core venv: `.venv-core/bin/pytest tests` and confirm features 001 and 002 tests still pass after the `VoiceLibrary` change
- [X] T034 Update `specs/001-tts-engine-adapters/quickstart.md` so its prerequisites reference the voice library commands instead of `cloned_voices/voices.toml` (T020 removed it)
- [X] T035 Owner step (real data, not committed): create consent records for `valentina` and `emiliano` with `--date 2025`, all four uses and all four content kinds; add both recordings with `--accent es-CO`; prepare Pocket TTS `valentina` and `emiliano`; prepare Phonon `valentina` (writes the segment; the voice is already cloned at studio.gradium.ai and downloaded as `cloned_voices/valentina.safetensors`, so no manual studio step remains) and `register` that file with the same `recording_id`; assign Piper `es_MX-claude-high` and `es_AR-daniela-high` (quickstart steps 3 and 4)
- [X] T036 Run the noise and length analysis on both real recordings, record `speech_seconds` and `snr_estimate_db` in `specs/003-voice-preparation-consent/research.md` as informational, without changing thresholds to force a pass; note any warning raised
- [X] T037 Run quickstart.md steps 2 to 6 end to end (use a copy of the data for the withdraw step) and `python -m tts_bench.voices check-repo` on the real repository; fix any divergence between the quickstart and the CLI

---

## Dependencies and order

- Phase 1 → Phase 2 → Phase 3 (US3 gate) → Phase 4 (US2 library) → Phase 5 (US1 preparation) → Phase 6 (withdrawal, needs voices and recordings) → Phase 7 (independent of 3 to 6 apart from the shared CLI file) → Phase 8.
- Within a phase, test tasks come first and should fail before the implementation task.
- Tasks that edit `src/tts_bench/voices/library.py` or `__main__.py` are sequential (same file): T010, T015 to T017, T024, T028 for the library; T011, T018, T025, T029, T032 for the CLI.
- T035 needs the real recordings and the existing `valentina.safetensors`; the rest runs without any real voice.

## Parallel opportunities

- Foundational: T003, T004, T005, T008 together.
- Phase 4 tests: T012, T013, T014 together; T021 alongside.
- Phase 5 tests: T022 and T023 together.
- T030 (repository check test) can be written any time after Phase 2.

## Implementation strategy

- **MVP**: Phases 1 to 4 (consent gate, library, resolve by name with all checks). That alone replaces the temporary library and gives every feature one resolution path.
- Then Phase 5 for the cross-engine recording guarantee, Phase 6 for withdrawal, Phase 7 for repository safety, and Phase 8 with the real voices.

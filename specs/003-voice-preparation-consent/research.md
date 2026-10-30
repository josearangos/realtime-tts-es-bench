# Research: Voice Preparation and Consent

No `NEEDS CLARIFICATION` remained after `/speckit-clarify`. Items below are design decisions; engine facts come from [feature 001's research](../001-tts-engine-adapters/research.md) and are labeled there as measured or unverified.

## Voice files per engine (FR-003, FR-004)

- **Decision**: one registered reference recording (`rec-<12 hex of its sha256>`) feeds every cloning-capable engine.
  - **Pocket TTS** (`reference_audio`): the prepared voice is the trimmed WAV segment, produced by the library. Automated.
  - **Phonon** (`stored_voice_file`): the prepared voice is a `.safetensors` file created by the owner's external step (feature 001 research: `add_voice(name, file.safetensors)`). The file is created in the hosted studio at studio.gradium.ai (clone the voice, download the `.safetensors`); the library writes the trimmed segment to upload and prints the instructions; the resulting file is then registered with `register`. The creation tool is not automated or invoked here.
  - **Piper** (`fixed_voice`): no cloning. Two documented fixed Spanish voices, `es_MX-claude-high` and `es_AR-daniela-high`, each registered as a non-cloned voice with no consent or recording.
- **Scope of voices**: Phonon `valentina` only; Pocket TTS `valentina` and `emiliano`. Only `valentina` is shared across engines, so cross-engine comparisons use `valentina`; `emiliano` is Pocket-only and `same_source` is false for any set that includes it with a Phonon voice.
- **Rationale**: the library cannot verify that an external file came from a given recording, so registration records the claim (recording id, segment) and the operator's attestation. Automating Phonon's creation step would couple the library to a hosted/owner-specific flow that this project has not re-run.
- **Alternatives**: calling the Phonon tooling from the library (rejected: unverified, engine dependency in the core); one shared segment for both engines (rejected by FR-005, which records the segment per engine because lengths may differ).

## Storage layout and what is tracked (FR-007, FR-015)

- **Decision**: everything lives under the existing git-ignored `cloned_voices/`: `library.json` (index), `consent/<alias>.json`, `recordings/<recording_id>.wav`, `voices/<name>/…`, `generated/<name>/…`. The index and consent are not tracked. Reports use `public_index()`, which exposes only name, engine, kind, cloned flag, accent label, checksum and recording id.
- **Rationale**: the folder is already ignored (`.gitignore`), so a new ignore rule is only needed for extra file types (`*.onnx`, `*.pt`, `*.ckpt`). No committed index is created, which satisfies FR-015 trivially; a future export can use `public_index()`.
- **Alternatives**: a committed `voices.index.json` with non-sensitive fields (rejected: not needed yet, adds a file that can drift from the local one).

## Registration copies files (FR-009, FR-011)

- **Decision**: `register` copies the file into `voices/<name>/` and checksums the copy (sha256). Fixed voices that point to a large model file (Piper `.onnx`) are registered by reference to the existing path and checksummed in place, and `remove` never deletes referenced files.
- **Rationale**: removal then has a well-defined set of files (the voice directory, the recording copy, `generated/<name>/`) without touching the user's originals or downloaded models.
- **Alternatives**: register in place (rejected: removal would delete files the library does not own); copy the Piper model (rejected: tens of MB for a non-sensitive file).

## Consent record and permission check (FR-001, FR-002, FR-016)

- **Decision**: one JSON per speaker alias with `alias`, `date` (`YYYY` or `YYYY-MM-DD`), `permitted_uses`, `allowed_content`, optional `notes`. `permitted_uses` takes `internal_benchmarking`, `published_results`, `published_demo_audio`, `human_evaluation`. `allowed_content` takes the corpus campaign values (`outbound_sales`, `collections`, `inbound`) and the literal `cloning_prompts`. `resolve(..., use=, content=)` refuses when a declared value is missing; when the caller declares nothing, the voice resolves (use-checking is opt-in per call; kept optional) and the call is logged as "use not declared". Preparation and registration of a cloned voice refuse without a valid record.
- **Rationale**: callers (metrics, backend, frontend) declare their use once; undeclared calls are not silently treated as permitted by default for published outputs: report builders MUST pass `use="published_results"`.
- **Alternatives**: always requiring a declaration (rejected: breaks quick local smoke runs); free-text uses (rejected: not checkable).

## Engine and integrity checks (FR-013, FR-014)

- **Decision**: each entry stores its `engine` (adapter registry name). `resolve(name, kind, engine=…)` refuses a different engine with `VoiceEngineMismatchError`; a missing file raises `VoiceIntegrityError("missing")`; a different sha256 raises `VoiceIntegrityError("modified")`. Hashing happens on every resolve (files are small); callers resolve before timed regions.
- **Rationale**: the existing adapter flow resolves in `smoke` and in later features, not inside adapters, so the check lives in `resolve`.
- **Alternatives**: cache by mtime (rejected: weakens the "modified" guarantee for little gain).

## Audio checks: short, noisy, music, accent (FR-005, FR-006)

- **Decision**: WAV (16-bit PCM) only, read with the standard `wave` module, downmixed to mono for analysis.
  - Frames of 30 ms; level = RMS in dBFS. Noise floor = 10th percentile. Speech frames = level ≥ noise floor + 10 dB. `speech_seconds` = speech frames × 0.03.
  - Warn `too_short` if `speech_seconds` < 10 (clarified in the spec).
  - Warn `noisy` if (90th percentile − 10th percentile) level < 20 dB. This is a heuristic proxy for signal-to-noise ratio, stored as `snr_estimate_db`, not a quality measurement. The 20 dB value is a starting default, overridable with `--noise-threshold-db`; a task runs the check on both real recordings and records the values (informational, no tuning to force a pass).
  - Music cannot be detected reliably without a model, so it is an operator attestation: `add-recording --no-music-confirmed` (absence produces a `music_not_ruled_out` warning).
  - Accent: recording has a declared `accent` (e.g. `es-CO`); each engine has a *known primary variant* table, `unknown` by default. Warn `accent_mismatch` only when both are known and differ.
- **Rationale**: simple, deterministic, testable with synthetic signals, no new dependency.
- **Alternatives**: a voice-activity or noise-estimation library (rejected: new dependency for an advisory warning); blocking on warnings (rejected: spec says warn).
- **Owner-confirmed default** (recommended per-engine lengths remain unverified): the default segment is the first 20 s of the recording (or all of it if shorter), overridable per engine with `--start` and `--length`; the values used are always recorded.

## Removal and consent withdrawal (FR-009, clarification 1)

- **Decision**: `remove <voice>` deletes the voice directory, `generated/<name>/`, and the index entry. `withdraw <alias>` removes every voice of that alias, the recording copy, the consent file, and then writes a tombstone `{name, recording_id, date}` to `library.json`. Then it scans the results directory (default `results/`) for JSON files containing a `voice` object whose `name` is withdrawn and sets a top-level `"voice_withdrawn": true`, leaving measurements unchanged. Report builders MUST skip or flag withdrawn voices. One command, one documented action (SC-004).
- **Rationale**: the tombstone lets later runs refuse a re-registered file with the same name, and lets reports exclude withdrawn voices without keeping any voice material.
- **Alternatives**: deleting result files (rejected in clarification); keeping voices but flagging them (rejected: withdrawal means removal).
- **Contract with later features**: generated audio goes under `cloned_voices/generated/<voice name>/`; result JSON carries `voice.name` and `voice.recording_id`.

## Keeping voice material out of the repository (FR-007, SC-003)

- **Decision**: `.gitignore` already ignores `cloned_voices/`, `*.wav`, `*.safetensors`; add `*.onnx`, `*.pt`, `*.ckpt`. `python -m tts_bench.voices check-repo` and a test fail when `git ls-files` lists a file with those extensions or under `cloned_voices/`, and (SC-003) when `git log --all --name-only --diff-filter=A` ever added one. The CLI exit code makes it usable as a pre-commit or CI check; the user installs it themselves, since commits are made by the user.
- **Alternatives**: an automatic git hook installed by the tool (rejected: modifies the user's git config without asking).

## Resolution API shape (FR-012)

- **Decision**: keep the `VoiceLibrary` Protocol in `core.voices` and extend `resolve` with keyword-only `engine`, `use` and `content`. `LocalVoiceLibrary` implements it. `DirectoryVoiceLibrary` and `voices.toml` are removed; `smoke` switches to the new library. The backend and frontend receive voice *names* only (`public_index()`), never paths.
- **Rationale**: adapters stay unchanged (they already take a `VoiceReference`); metrics, backend and scripts gain a single resolution path.

## Measured on the real recordings (informational, T036)

Heuristics from `add-recording` (30 ms frames; thresholds `too_short` < 10 s of speech, `noisy` < 20 dB). Thresholds were not changed.

| Speaker alias | Accent | `speech_seconds` | `snr_estimate_db` | Warnings |
|---------------|--------|------------------|-------------------|----------|
| valentina | es-CO | 14.01 | 48.2 | none |
| emiliano | es-CO | 11.79 | 49.2 | none |

Both recordings were added with `--no-music-confirmed`, so no `music_not_ruled_out` warning was raised; that flag is the operator's attestation, not a detection.

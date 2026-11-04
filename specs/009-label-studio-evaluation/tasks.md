---

description: "Task list for Label Studio Human Evaluation (Containerized)"
---

# Tasks: Label Studio Human Evaluation (Containerized)

**Input**: Design documents from `/specs/009-label-studio-evaluation/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (commands, task-schema, labeling-interfaces, environment, export-format), quickstart.md.

**Tests**: Included. Constitution VIII and FR-018 require provisioning logic to be testable with a fake dataset and a fake Label Studio server, with no engines, weights or Docker. Real-stack checks use the opt-in `docker` pytest marker.

**Organization**: Grouped by user story. US3 (blindness) is delivered by the foundational blind primitives plus its own verification phase, because US2 cannot create tasks without opaque ids.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: parallelizable (different files, no dependency on incomplete tasks)
- **[Story]**: US1–US5 (spec.md user stories)
- Paths are repository-relative.

## Path Conventions

- Container assets: `evaluation/`, `Makefile`
- Package: `src/tts_bench/evaluation/`
- Tests: `tests/evaluation/{unit,integration,docker}/`
- Runtime data (git-ignored): `output/evaluation/`, `backups/evaluation/`; exports: `results/human/`

---

## Phase 1: Setup

- [ ] T001 Verify against Label Studio **1.23.2** (Community Edition, official image `heartexlabs/label-studio:1.23.2`) every env variable and REST endpoint listed in `specs/009-label-studio-evaluation/contracts/environment.md` and `contracts/commands.md` (health, projects, task import/list/delete, users, annotation export, local-files serving (including whether a per-project "Local files" storage must be registered for `/data/local-files/` URLs to load), random sampling, telemetry-off variable, admin user/password/token env); write findings and exact names to `specs/009-label-studio-evaluation/research.md` under a new "R14 Verified against 1.23.2" section and flag any feature that turns out to be Enterprise-only (replace it, do not use it)
- [ ] T002 Create the package skeleton `src/tts_bench/evaluation/__init__.py` and test folders `tests/evaluation/unit/`, `tests/evaluation/integration/`, `tests/evaluation/docker/` with `__init__.py` files
- [ ] T003 [P] Add the `docker` marker to `[tool.pytest.ini_options].markers` in `pyproject.toml` (skipped unless `-m docker`) and add `evaluation = ["numpy"]` optional dependency group
- [ ] T004 [P] Create `evaluation/batch.toml` with `seed`, `sentences_per_condition = 20`, `repeat_rate = 0.10`, `attention_rate = 0.05`, `loudness_rms_dbfs = -23`, `peak_limit_dbfs = -1`, empty `conditions`, `cmos_pairs = "all"`, and `[quality_thresholds] repeat_within_1_min = 0.7, max_failed_checks = 1` (data-model.md BatchConfig)

---

## Phase 2: Foundational (blocks all stories)

**⚠️ CRITICAL**: no story work starts before this phase is complete.

- [ ] T005 [P] Implement `src/tts_bench/evaluation/config.py`: load and validate `batch.toml` (`repeat_rate` in 0–0.3, `attention_rate` in 0–0.2, `sentences_per_condition` ≥ 1), expose a frozen dataclass and a SHA-256 of the file
- [ ] T006 [P] Implement `src/tts_bench/evaluation/scales.py`: frozen Spanish scale and anchor definitions from `contracts/labeling-interfaces.md` (MOS naturalidad/pronunciación/prosodia 1–5, CMOS −3…+3, SIM 1–5) and a deterministic SHA-256 `scale_hash()`
- [ ] T007 [P] Implement `src/tts_bench/evaluation/loudness.py`: numpy RMS normalization to the configured dBFS with a peak limiter at −1 dBFS, silence-safe, WAV read/write via stdlib `wave` (16-bit mono, sample rate preserved)
- [ ] T008 [P] Implement `src/tts_bench/evaluation/blind.py`: seeded RNG (`random.Random(seed)`), 12-hex opaque id generator (unique, reproducible per seed), mapping row dataclass with the fields of data-model.md "BlindMapping row", JSONL read/write of `output/evaluation/private/mapping.jsonl`
- [ ] T009 [P] Implement `src/tts_bench/evaluation/sources.py`: discover synthesized clips from the layouts of features 004–006 (`output/speaker/*`, `output/intelligibility/*`) and from a generic `--source-manifest` JSONL (`engine, voice, accent, cloned, sentence_id, wav`); validate every `sentence_id` against the corpus loader (`tts_bench.corpus.loader`) and record `corpus_version` and `content_sha256` from `corpus/VERSION.json`; confirm and document the real on-disk sidecar fields (resolves research R12)
- [ ] T010 [P] Implement `src/tts_bench/evaluation/labelconfig.py`: generate the Spanish label configs (XML) for MOS (one `Audio`, three `Rating` controls), CMOS (`audio_a`, `audio_b`, 7-choice) and SIM (`reference`, `audio`, `Rating`), the instruction text, and enable random task ordering; use only Community Edition tags
- [ ] T011 [P] Implement `src/tts_bench/evaluation/lsclient.py`: stdlib `urllib` client with token auth for the endpoints verified in T001 (health, list/create project, list/import/delete tasks, list/create users, export annotations); timeouts, retries on connection errors, typed errors
- [ ] T012 Implement `src/tts_bench/evaluation/fakes.py`: (a) generator of a synthetic dataset (sine WAVs for ≥ 2 fake engines, ≥ 1 cloned voice with a reference WAV, a small fake corpus and `VERSION.json`) and (b) an in-process fake Label Studio HTTP server implementing the endpoints used by `lsclient.py` (that does not deduplicate on its own, so a double import is detectable by tests)
- [ ] T013 [P] Unit tests in `tests/evaluation/unit/test_config_scales_loudness.py`: config validation errors, scale hash stable and changes when an anchor changes, loudness hits −23 dBFS ±0.5 and never exceeds −1 dBFS peak, silence input safe
- [ ] T014 [P] Unit tests in `tests/evaluation/unit/test_blind_sources.py`: ids are 12-hex, unique, reproducible for a seed and different across seeds; mapping JSONL round-trip; sources discovery on the fake dataset; unknown `sentence_id` rejected
- [ ] T015 [P] Unit tests in `tests/evaluation/unit/test_labelconfig.py`: configs are well-formed XML, contain the Spanish questions and anchors from `contracts/labeling-interfaces.md`, MOS has exactly three `Rating` controls, no engine/voice words appear
- [ ] T016 Add `.gitignore` check: confirm `output/evaluation/`, `backups/` and `evaluation/.env` are ignored (added during planning) and add `results/human/` exceptions only for `*.jsonl`, `*.csv`, `*.json` text outputs (no audio)

**Checkpoint**: primitives and fakes ready.

---

## Phase 3: User Story 1 - Launch the whole environment (Priority: P1) 🎯 MVP

**Goal** (validated with `EVAL_PROVISION=0` until US2 lands; T032 enables it by default): `cp evaluation/.env.example evaluation/.env` + `make eval-up` gives a working, loopback-only Label Studio that persists data and works offline.

**Independent Test**: (with `EVAL_PROVISION=0` until T032) on a machine with only Docker, fresh clone → two commands → Label Studio reachable; `eval-down`/`eval-up` keeps data; `eval-reset` (confirmed) clears it.

- [ ] T017 [P] [US1] Create `evaluation/Dockerfile`: `ARG LS_VERSION=1.23.2`, `FROM heartexlabs/label-studio:${LS_VERSION}`, no run-time network use
- [ ] T018 [P] [US1] Create `evaluation/provisioner.Dockerfile`: `python:3.11-slim`, install `numpy` only, copy `src/tts_bench` and set `PYTHONPATH`, entrypoint `python -m tts_bench.evaluation`
- [ ] T019 [P] [US1] Create `evaluation/.env.example` per `contracts/environment.md` (`LS_VERSION=1.23.2`, `LS_BIND=127.0.0.1`, `LS_PORT=8080`, `LS_ADMIN_USER`, `LS_ADMIN_PASSWORD=change-me`, `LS_API_TOKEN=change-me-token`, `EVAL_PROVISION=1`); placeholders only
- [ ] T020 [US1] Create `evaluation/compose.yaml`: `label-studio` (build from Dockerfile, port `${LS_BIND:-127.0.0.1}:${LS_PORT:-8080}:8080`, named volume `ls-data` for DB and media, local-files serving enabled with `output/evaluation/served` mounted **read-only**, sign-up disabled, telemetry off, admin credentials and token from env, healthcheck on the verified health endpoint, `restart: unless-stopped`) and `provisioner` (build, `depends_on` label-studio `service_healthy`, mounts `corpus/`, `output/evaluation/`, and `output/speaker/`, `output/intelligibility/` plus any `--source-manifest` file read-only, runs `prepare` then `provision` only when `EVAL_PROVISION=1`, via a compose profile so that US1 can be validated with `EVAL_PROVISION=0` before the CLI of US2 exists); the private mapping directory MUST NOT be mounted into `label-studio`
- [ ] T021 [P] [US1] Create `evaluation/scripts/preflight.sh`: check `docker` and Compose v2 exist and the daemon runs, `.env` present, port free (suggest `LS_PORT=…`), refuse `change-me` passwords/tokens when `LS_BIND` is not loopback, print the plain-HTTP security warning when exposed, handle volume permission problems with an actionable message
- [ ] T022 [US1] Create `Makefile` with `eval-up` (preflight, detect the built images with `docker image inspect` and skip the build if present, `docker compose -f evaluation/compose.yaml --env-file evaluation/.env up -d --build`, wait healthy, show progress), `eval-down`, `eval-reset` (requires typing `RESET`, removes volume and `output/evaluation/`), and `help` listing all `eval-*` targets; use `--no-build` when the image already exists so start works offline
- [ ] T023 [P] [US1] Compose config test `tests/evaluation/integration/test_compose_config.py`: parse `evaluation/compose.yaml` and assert loopback default bind, named volume, healthcheck, `depends_on` healthy, read-only audio mount, private dir not mounted in `label-studio`, no secret values committed in `.env.example`
- [ ] T024 [P] [US1] Preflight tests `tests/evaluation/integration/test_preflight.py`: placeholder password refused on non-loopback bind, busy port reported with hint, missing `.env` message
- [ ] T025 [US1] Docker test `tests/evaluation/docker/test_lifecycle.py` (`-m docker`): up → healthy; down/up keeps a created project; reset with wrong confirmation does nothing, with `RESET` clears; start with the network disabled (run with `docker compose --profile` offline by disconnecting the host network or using `docker network disconnect`/`--network none` for the provisioner) after the first build works (SC-002, SC-007)

**Checkpoint**: environment launches, persists, resets.

---

## Phase 4: User Story 2 - Provision projects automatically (Priority: P1)

**Goal**: projects and tasks are created from synthesized audio with no manual setup, idempotently, in Spanish.

**Independent Test**: with the fake dataset and fake Label Studio, provisioning creates 3 projects and expected task counts; a second run creates nothing.

- [ ] T026 [US2] Implement `src/tts_bench/evaluation/tasks.py`: build MOS tasks (stratified selection of `sentences_per_condition` sentences, same sentences for every condition), CMOS pair tasks (all condition pairs per sentence subset), SIM tasks (cloned voices only, with the reference clip), producing task data per `contracts/task-schema.md` and mapping rows; stage normalized WAVs named `<item_id>.wav` into `output/evaluation/served/`
- [ ] T027 [US2] Implement `prepare` in `src/tts_bench/evaluation/batch.py`: pure function of config + sources + corpus version + seed; write `output/evaluation/batch.json` (fields in data-model.md "Batch", including `scale_hash`, loudness settings, `label_studio_version`, counts, `config_sha256`) and reuse it if present; refuse to change a frozen batch unless `--new-batch`
- [ ] T028 [US2] Implement `src/tts_bench/evaluation/provision.py`: wait for health (timeout → exit 3), create projects by fixed title (MOS, CMOS, SIM) with labeling config and instructions from `labelconfig.py`, abort with exit 4 if an existing project's config hash differs from `scale_hash`, register, idempotently, the Local files storage for each project when T001 shows it is required (path = served audio root), import only tasks whose `item_id` is missing, report created/skipped counts
- [ ] T029 [US2] Implement CLI `src/tts_bench/evaluation/__main__.py` subcommands `prepare` and `provision` (`--url`, `--token` from env) with exit codes 0/2/3/4 per `contracts/commands.md`
- [ ] T030 [P] [US2] Unit tests `tests/evaluation/unit/test_tasks.py`: counts per project match expectations for the fake dataset, same sentences across conditions, SIM only for cloned voices, task data keys exactly per `contracts/task-schema.md`
- [ ] T031 [P] [US2] Integration test `tests/evaluation/integration/test_provision.py` using the fake Label Studio: first run creates 3 projects and N tasks, second run creates 0 (SC-005), a changed anchor triggers exit 4, unreachable server times out with exit 3
- [ ] T032 [US2] Wire automatic provisioning: ensure the `provisioner` service command in `evaluation/compose.yaml` runs `prepare` then `provision` and exits 0 after success; docker test `tests/evaluation/docker/test_provision_stack.py` asserts 3 projects exist after `make eval-up` and still 3 projects with unchanged task counts after a second `make eval-up`
- [ ] T033 [P] [US2] Add `make eval-inspect` to `Makefile` and `inspect` subcommand in `src/tts_bench/evaluation/__main__.py` printing annotator-visible task data of all projects as JSON

**Checkpoint**: US1 + US2 deliver a working evaluation setup.

---

## Phase 5: User Story 3 - Blind and randomized evaluation (Priority: P1)

**Goal**: guarantee annotators cannot learn engine or voice, with randomized order and A/B positions and a private, traceable mapping.

**Independent Test**: inspect annotator-visible data and files; no names; A/B positions balanced; every mapping row complete.

- [ ] T034 [US3] Implement seeded randomization in `src/tts_bench/evaluation/blind.py` and `tasks.py`: shuffled task order, per-pair A/B swap recorded in the mapping `position` field, roughly balanced (document the exact rule: balanced swap per pair then shuffled)
- [ ] T035 [P] [US3] Leak test `tests/evaluation/unit/test_blind_leaks.py`: for the fake dataset, scan all task `data` values and served file names; fail if any contains an engine name, voice name, sentence id or a filename not matching `^[0-9a-f]{12}\.wav$` (SC-004); also assert the served directory contains only opaque names and that WAV metadata chunks carry no engine/voice text
- [ ] T036 [P] [US3] Randomization tests `tests/evaluation/unit/test_randomization.py`: same seed → identical batch; different seed → different order; A/B share within 40–60% over the fake pairs; mapping rows have non-null engine, voice, sentence_id, corpus_version for every item
- [ ] T037 [US3] Implement `purge-voice` in `src/tts_bench/evaluation/__main__.py` and `provision.py`: delete a voice's served WAVs, its tasks in Label Studio (via `lsclient`) and its mapping rows, record the purge in `output/evaluation/private/purges.jsonl`; add `make eval-purge-voice VOICE=…`
- [ ] T038 [P] [US3] Test `tests/evaluation/integration/test_purge_voice.py` against the fake Label Studio: files, tasks and mapping rows of the voice are gone, others untouched, reference clips of that voice removed

**Checkpoint**: blindness verified by automated tests.

---

## Phase 6: User Story 4 - Control annotation quality (Priority: P2)

**Goal**: repeats and attention checks in every batch, flagged privately, reported per annotator.

**Independent Test**: fake batch contains the configured share of QC items; a scripted annotator who fails them is flagged.

- [ ] T039 [US4] Implement `src/tts_bench/evaluation/qc.py`: repeats (default 10%: same audio, new `item_id`, `role=repeat`, `repeat_of`), instructed-response attention items over a generated tone (Spanish instruction in `text`, `expected` answers in mapping), degraded-anchor items (real clip mixed with noise at 0 dB SNR, expected ≤ 2 on every MOS criterion); QC items indistinguishable from test items in task data; integrate in `batch.py`
- [ ] T040 [US4] Implement `src/tts_bench/evaluation/quality.py`: per annotator `n_annotations`, `repeat_pairs`, `repeat_mad`, `repeat_within_1`, `attention_total`, `attention_failed`, `flagged` and `reasons[]` using thresholds from `batch.toml`; no automatic exclusion
- [ ] T041 [P] [US4] Unit tests `tests/evaluation/unit/test_qc.py`: QC shares match rates within rounding, repeats reference an existing item, QC items carry no distinguishing field in task data
- [ ] T042 [P] [US4] Unit tests `tests/evaluation/unit/test_quality.py` with scripted annotations: a consistent attentive annotator is not flagged; one failing 2 checks or with low repeat consistency is flagged with reasons
- [ ] T043 [US4] Add a test `tests/evaluation/unit/test_scales_frozen.py` that compares `scale_hash()` against a golden value stored in `tests/evaluation/unit/fixtures/scale_hash.golden`; any change to anchors or scales fails until the golden file is deliberately updated (US4 scenario 3)

---

## Phase 7: User Story 5 - Back up, restore and export (Priority: P2)

**Goal**: protect annotation work and hand results to the report feature.

**Independent Test**: export, back up, reset, restore, export again → identical annotation rows.

- [ ] T044 [US5] Implement `src/tts_bench/evaluation/export.py`: fetch annotations through `lsclient`, join with the mapping, write `annotations.jsonl`, `annotations.csv`, `quality.json` and `MANIFEST.json` (the manifest also records Python and numpy versions, OS, the Label Studio version and the exact export command line, per Constitution V) to `results/human/` (or `--out`) per `contracts/export-format.md`; pseudonymous `annotator_id` only, derived exclusively from emails matching `^a[0-9]{2,}@eval\.invalid$` (any other email format aborts the export with an error naming the user id, never the email), no audio or reference files, QC rows included with `role`, rows sorted by `(project, item_id, annotator_id)`; fail if any row lacks engine(s), voice(s), sentence_id or corpus_version
- [ ] T045 [US5] Add `export` and `quality` subcommands to `src/tts_bench/evaluation/__main__.py` and `make eval-export [OUT=dir]` to `Makefile`
- [ ] T046 [US5] Implement `make eval-backup`: stop `label-studio`, archive the `ls-data` volume and `output/evaluation/` (served, private, `batch.json`) into `backups/evaluation/<UTC>.tar.gz` using the Label Studio image's own `tar`, add `MANIFEST.json` (batch_id, LS version, member sha256), restart; implement `make eval-restore FILE=…` (refuse when data exists unless confirmed, verify manifest checksums, extract, start); put the logic in `evaluation/scripts/backup.sh` and `evaluation/scripts/restore.sh`
- [ ] T047 [US5] Implement annotator management: `annotator` subcommand and `make eval-annotator ID=a01` creating a user with email `a01@eval.invalid`, no names, generated password printed once; `provision` creates no annotators automatically
- [ ] T048 [P] [US5] Unit/integration tests `tests/evaluation/integration/test_export.py` with the fake Label Studio and scripted annotations: every row traces to engine, voice, sentence, corpus version (SC-006), no emails or file paths in output, two exports of the same state are byte-identical, CMOS rows resolve A/B back to engines via the mapping
- [ ] T049 [P] [US5] Test `tests/evaluation/integration/test_backup_scripts.py`: with a temp dir standing in for volume and output, archive then restore yields identical trees and a corrupted archive is rejected
- [ ] T050 [US5] Docker test `tests/evaluation/docker/test_backup_restore.py` (`-m docker`): annotate via API, export, backup, reset, restore, export again, assert identical annotation rows (SC-003)

---

## Phase 8: Polish & Cross-Cutting

- [ ] T051 [P] Write `evaluation/README.md`: host requirements (Docker with Compose v2, port, disk), three-step quickstart, all `make eval-*` commands, loopback default and the explicit network-exposure option with security warning, loudness treatment and its limitation (RMS rather than LUFS), Community-Edition-only note and that annotators see all projects, troubleshooting (port in use, runtime not running, volume permissions, slow first build, upgrade of the pinned version)
- [ ] T052 [P] Write `docs/human-evaluation.md`: evaluation protocol (native Spanish speakers, headphones, scales and anchors, halo-effect note for the single MOS project), how to read the export and quality report, that annotators must be native Spanish speakers (attested by the organizer, not enforced by the tool), consent withdrawal via `eval-purge-voice`, Constitution IV and VI compliance notes
- [ ] T053 Add the upgrade-guard: `eval-up` compares the volume's recorded Label Studio version (marker file `output/evaluation/ls-version`, see data-model.md VersionMarker) with `LS_VERSION` and refuses with an explanation when they differ unless `EVAL_ALLOW_UPGRADE=1`; test in `tests/evaluation/integration/test_upgrade_guard.py`
- [ ] T054 [P] Add a short "Human evaluation" section to `README.md` linking to `evaluation/README.md` and `docs/human-evaluation.md`
- [ ] T055 Run the full quickstart in `specs/009-label-studio-evaluation/quickstart.md` (steps 1–8) including `pytest tests/evaluation -q` and `pytest -m docker tests/evaluation/docker`; record results and any deviations in `specs/009-label-studio-evaluation/quickstart.md` under "Validation run"
- [ ] T056 [P] Constitution compliance pass: confirm no secrets, audio, mapping or backups are tracked (`git status`/`git ls-files`), pseudonymous ids only in exports, Spanish-only annotator text; note result in the PR description

---

## Dependencies & Execution Order

- Phase 1 → Phase 2 → stories. T001 (verification against 1.23.2) gates T011, T020 and T028.
- **US1** (Phase 3) needs only Phase 1–2 and can start in parallel with US2 code (different files); `compose.yaml` (T020) calls the CLI built in US2, so T032 closes that loop.
- **US2** depends on Phase 2; **US3** depends on US2 task generation (T026–T027); **US4** depends on `batch.py`/`tasks.py` (US2); **US5** depends on US2 and on `lsclient` (T011); backup (T046) depends on US1 compose.
- Polish last.

### Story completion order
US1 → US2 → US3 → US4 → US5 (US1 and US2 can overlap; US4 and US5 can run in parallel after US3).

## Parallel Examples

- Phase 2: T005–T011 (separate modules) together; then T013–T015 tests together.
- US1: T017, T018, T019, T021 in parallel, then T020, T022.
- US3: T035, T036, T038 in parallel after T034/T037.
- US4/US5: T041, T042, T048, T049 in parallel with their implementation siblings once code exists.

## Implementation Strategy

**MVP = US1 + US2 + US3** (all P1): launch, auto-provision, blind and randomized. Validate with fakes first (unit + integration), then with the docker marker, then with real engine audio. Add US4 (quality) and US5 (backup/export) next; they are P2 but US5's export is required before any real collection starts. Do not begin real annotation until T001, T050 and T055 pass, because the scale hash freezes the batch.

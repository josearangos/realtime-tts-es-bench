# Implementation Plan: Label Studio Human Evaluation (Containerized)

**Branch**: `009-label-studio-evaluation` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/009-label-studio-evaluation/spec.md`

## Summary

Add `evaluation/` (container assets) and `src/tts_bench/evaluation/` (Python package, stdlib + numpy only) so that `cp evaluation/.env.example evaluation/.env && make eval-up` yields a loopback-only Label Studio with three provisioned Spanish projects: **MOS** (one audio, three 5-point ratings: naturalidad, pronunciación, prosodia), **CMOS** (A/B pair, 7-point comparison) and **SIM** (reference + clip, 5-point similarity, cloning subset only).

Compose runs two services: `label-studio` (image built from a Dockerfile that pins the Label Studio version, data in a named volume) and a one-shot `provisioner` (waits for the health check, then runs `prepare` and `provision`). `prepare` is deterministic from a seed: it selects items from existing synthesized audio, loudness-normalizes them, assigns **opaque ids**, randomizes order and A/B positions, injects repeats and attention checks, and writes the **private blind mapping** outside anything Label Studio can reach. `provision` creates the projects (by title) and imports only tasks whose opaque id is absent, so reruns never duplicate. `export` joins Label Studio annotations with the mapping and writes the files the results report will read. Backup/restore archive the data volume plus the private mapping. See [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/), [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.11 (same as the repo) for `tts_bench.evaluation`; Dockerfile + Compose v2 + GNU Make for the environment.

**Primary Dependencies**: Label Studio **1.23.2** (latest stable release as of 2026-11-04, released 2026-09-29; PyPI and Docker Hub tag `heartexlabs/label-studio:1.23.2` both verified to exist). Pinned in `evaluation/.env.example` and the Dockerfile `ARG`; both the container and local development/tests use this same version, see research R1; runtime of the provisioner image: `numpy` only, HTTP via stdlib `urllib`, WAV via stdlib `wave`. No Label Studio SDK, so the provisioner has no network dependency at run time.

**Storage**: Label Studio SQLite database and uploaded media in the named volume `ls-data` (survives restarts and image rebuilds). Staged audio and private mapping on the host under `output/evaluation/` (git-ignored). Backups in `backups/evaluation/` (git-ignored). Exports in `results/human/`.

**Testing**: pytest in `tests/evaluation/`: unit tests for selection, opaque ids, randomization, loudness, QC injection, label-config generation, export join and quality metrics; provisioning tests against an **in-process fake Label Studio HTTP server** and a **fake dataset** of synthetic sine WAVs (FR-018, no engines, no Docker). An opt-in `docker` marker runs the real stack (start, restart persistence, reset, backup/restore, offline start).

**Target Platform**: macOS/Linux hosts with Docker (Compose v2) as the only supported runtime (Podman not tested); annotators use any modern browser on the same host (or LAN when explicitly exposed).

**Project Type**: containerized service plus CLI tooling (no web code of our own; labeling UIs are Label Studio label configs).

**Performance Goals**: not a benchmark; provisioning of a default batch (about 300 tasks) completes in under 60 s after Label Studio is healthy.

**Constraints**: loopback binding by default; works offline once the image exists (no CDN, no pip/apt at run time, `docker compose up --no-build` path); no secrets committed; annotator-facing fields contain no engine, voice, sentence id or source filename.

**Licensing/Cost**: Label Studio **Community Edition** only (open source); no Enterprise-only features, no paid services, no external API keys or accounts. Every dependency (Label Studio, Docker Compose, Python, numpy, Make) is open source. The only secrets are the local admin password and the local Label Studio token in the git-ignored `.env`.

**Scale/Scope**: 2 to 5 annotators (each completes whole projects; no enforced assignment), up to ~6 engine-voice conditions, about 20 sentences per condition per project type.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | Human metrics are reported separately; TTFA is not touched. Streaming-vs-sentence audio is the same final WAV for human rating; stated in docs |
| II Spanish by Default | Pass | All UI text, instructions, anchors in Spanish; instructions require native Spanish speakers; accent label of each voice is kept in the mapping and exported |
| III Apples-to-apples | Pass | Same sentences for every engine in a project; same loudness treatment applied to all clips; same ordering seed for everyone |
| IV Deterministic vs human distinct | **Pass, core** | Blind (opaque ids, no names in task data), randomized (order and A/B), scale and anchors frozen before collection (checksum of label configs recorded in the batch; changing them requires a new batch) |
| V Honest, reproducible | Pass | Raw annotations exported unmodified with batch id, seed, corpus version, scale-definition hash, Label Studio version; summaries recomputable |
| VI Licensing/consent | **Pass, with care** | Pseudonymous annotator ids only; reference recordings are served only inside the local SIM project and never written to exports; audio/mapping/backups git-ignored; `purge-voice` removes a voice's audio and tasks. Cloned voices are treated as consented per the constitution's standing confirmation, no new consent questions |
| VII Modular | Pass | `tts_bench.evaluation` imports only `core` helpers and corpus loader; metrics, backend and frontend do not import it; it runs without the backend |
| VIII Verifiable | Pass | Every FR maps to a unit test, fake-LS provisioning test or docker-marked test (table in [quickstart.md](quickstart.md)) |

Post-design re-check: no violations. No changes to existing code are required; only `.gitignore` gains entries. Complexity Tracking not needed.

## Key Design Decisions

1. **Three projects, not five**: MOS is one project with three Rating questions on the same audio (fewer listens, same sentence for all three criteria); CMOS and SIM are separate. The halo-effect trade-off is documented in research R3.
2. **Blindness by construction**: task `data` contains only `item_id` (random 12-char token), `audio` URL `/data/local-files/?d=<item_id>.wav`, and Spanish text fields. The mapping `item_id → {engine, voice, accent, sentence_id, corpus_version, role}` lives in `output/evaluation/private/mapping.jsonl`, which is never mounted into Label Studio.
3. **Idempotent by key**: a project is identified by its fixed title; a task by `item_id`. Provisioning lists existing tasks and imports only the missing ones.
4. **Frozen batch**: `prepare` is a pure function of `(batch.toml, source audio manifest, corpus version, seed)`; if `batch.json` exists it is reused. A new batch requires `make eval-new-batch`, so scales and tasks cannot drift mid-collection.
5. **Quality control**: ~10% repeated items (same audio, new `item_id`, mapping `qc_role=repeat_of`) and ~5% attention checks: (a) instructed-response ("seleccione «Mala» en esta pregunta") over a generated tone clip, (b) degraded anchor (a real clip mixed with noise at 0 dB SNR, expected ≤ 2). Marked only in the mapping.
6. **Loudness**: every staged clip is RMS-normalized to −23 dBFS with a −1 dBFS peak limiter (numpy), same treatment for all engines; documented, original audio untouched.
7. **Operations through Make** (`eval-up`, `eval-down`, `eval-reset`, `eval-backup`, `eval-restore`, `eval-export`, `eval-new-batch`, `eval-annotator`, `eval-purge-voice`), each calling a preflight check first (runtime present and running, port free, `.env` present).
8. **Network**: published port bound to `${LS_BIND:-127.0.0.1}`; sign-up disabled; annotators created by the organizer with pseudonymous ids (`a01`, `a02`, …).

## Project Structure

### Documentation (this feature)

```text
specs/009-label-studio-evaluation/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── commands.md
│   ├── task-schema.md
│   ├── labeling-interfaces.md
│   ├── environment.md
│   └── export-format.md
└── tasks.md             # /speckit-tasks (not created here)
```

### Source Code (repository root)

```text
evaluation/
├── Dockerfile                 # FROM pinned Label Studio image
├── provisioner.Dockerfile     # python:3.11-slim + numpy + package
├── compose.yaml               # label-studio + provisioner, volumes, healthcheck
├── .env.example               # no secrets; LS_VERSION, LS_PORT, LS_BIND, admin vars
├── batch.toml                 # seed, sentences per condition, QC rates, conditions
├── scripts/preflight.sh       # runtime/port/.env checks with actionable messages
└── README.md                  # host requirements, troubleshooting, security warning
Makefile                       # eval-* targets
src/tts_bench/evaluation/
├── __init__.py
├── __main__.py                # prepare | provision | export | quality | purge-voice | annotator
├── config.py                  # batch.toml loader, validation
├── sources.py                 # discover synthesized audio -> SourceClip list
├── loudness.py                # RMS normalization + peak limit
├── batch.py                   # prepare: frozen batch.json, orchestrates selection
├── tasks.py                   # builds MOS/CMOS/SIM tasks, stages served audio
├── blind.py                   # opaque ids, seeded shuffle, A/B assignment, mapping I/O
├── qc.py                      # repeats, attention checks, degraded anchors
├── scales.py                  # frozen scale definitions + hash
├── labelconfig.py             # Spanish label configs for MOS/CMOS/SIM
├── lsclient.py                # minimal stdlib REST client (health, projects, tasks, users, export)
├── provision.py               # idempotent project/task creation
├── export.py                  # join annotations + mapping, write results/human/
├── quality.py                 # per-annotator consistency, failed checks
└── fakes.py                   # synthetic sine dataset + fake Label Studio server (tests)
tests/evaluation/
├── unit/  integration/  docker/
output/evaluation/              # git-ignored: served/ (opaque wavs), private/, batch.json
backups/evaluation/             # git-ignored
results/human/                  # export output (tracked: no audio, pseudonymous ids only)
```

**Structure Decision**: container assets in a top-level `evaluation/` folder (mirrors `frontend/`); logic in a new `tts_bench.evaluation` package so it stays unit-testable and independent of backend/frontend (Principle VII).

## Complexity Tracking

No constitution violations to justify.

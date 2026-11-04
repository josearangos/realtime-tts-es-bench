# Quickstart: Validation Guide

Prerequisite: Docker (Compose v2) running; free port 8080 (or set `LS_PORT`).

## 1. Fresh start (SC-001, US1)
```
cp evaluation/.env.example evaluation/.env   # set LS_ADMIN_PASSWORD
make eval-up
```
Expect: preflight OK, image built/pulled with progress, Label Studio at `http://127.0.0.1:8080`, three projects (MOS, CMOS, SIM) populated. Two commands.

## 2. Spanish UI and blindness (US2, US3, SC-004)
Open a task in each project; all instructions/anchors are Spanish. `make eval-inspect` dumps annotator-visible task data; grep it for engine/voice names, sentence ids and `.wav` names other than `<12hex>.wav` → none.

## 3. Idempotency (SC-005)
`make eval-up` again (or `python -m tts_bench.evaluation provision`) → "0 projects created, 0 tasks imported".

## 4. Persistence (SC-002)
Annotate a few tasks, `make eval-down && make eval-up`; counts of projects, tasks, annotations unchanged.

## 5. Backup / reset / restore (SC-003, US5)
```
make eval-export                 # results/human/ before
make eval-backup                 # backups/evaluation/<ts>.tar.gz
make eval-reset                  # type RESET
make eval-restore FILE=backups/evaluation/<ts>.tar.gz
make eval-export OUT=results/human-after
```
Expect annotation rows byte-identical between the two exports.

## 6. Export and quality (SC-006, US4)
`results/human/annotations.jsonl` rows all have engine, voice, sentence_id, corpus_version; `quality.json` lists repeat consistency and failed checks per annotator.

## 7. Offline (SC-007)
Disconnect network, `make eval-down && make eval-up` → works.

## 8. Without Docker or real audio (FR-018)
`pytest tests/evaluation -q` uses a fake dataset and fake Label Studio server; no engines, no Docker. `pytest -m docker tests/evaluation/docker` runs steps 1, 3, 4, 5 against the real stack.

## Requirement coverage
| Req | Check |
|---|---|
| FR-001/003 | docker test: files exist, volume survives `down` and rebuild |
| FR-002 | `make help` lists all actions; commands tested |
| FR-004/005/013 | fake-LS provisioning test; docker test |
| FR-006 | label-config unit tests assert Spanish strings/anchors; scale hash test |
| FR-007/008 | blind/unit tests (no names in task data, seeded shuffle, A/B balance) |
| FR-009 | qc unit tests (rates, mapping flags) |
| FR-010 | loudness unit test (RMS target, no clipping) |
| FR-011/012 | preflight test: placeholder password refused on non-loopback; compose config assertion |
| FR-014 | docker test with network disabled |
| FR-015/016 | export unit tests (join, no emails, no reference files) |
| FR-017 | README review checklist |
| FR-018 | fakes |

## Validation run
Recorded 2026-11-04 on macOS (Darwin 25.2), Python 3.11.13, numpy 2.4.6.

| Step | Result |
|---|---|
| 8. `pytest tests/evaluation -q` (fake dataset + fake Label Studio, no Docker) | **91 passed**; the full suite `pytest tests -q` gives 691 passed, 14 skipped |
| `prepare` on the real repository audio (written to a scratch directory) | OK: 4 conditions, MOS 120, CMOS 120, SIM 60, repeats 30, attention 15; voice consent for `human_evaluation` enforced through the voice library |
| 1–3. `make eval-up`, provisioning, audio playback, idempotent re-run | OK on a real Label Studio (reported by the operator): 3 projects with 138 / 138 / 69 tasks; audio plays after fixing the local-files layout (below) |
| 4. Annotation as `a01` in the browser | OK (Spanish interface, ratings saved) |
| 5. Export (`make eval-export`) | OK: row for a CMOS annotation had `annotator_id=a01`, `cmos=-3`, engine/voice of A and B resolved from the private mapping, corpus version and scale hash, no email or file path |
| `down` / `up` persistence | OK (reported by the operator) |
| `pytest -m docker tests/evaluation/docker` | reported OK by the operator (output not captured here) |
| Offline start with the network disabled (SC-007) | not separately recorded; `eval-up` takes the `--no-build` path when the images exist |

Deviations found only on the real stack (all fixed, with tests where possible):
- the provisioner resolved the corpus under `/opt/corpus`; it now uses `corpus/` of the working directory first;
- `docker compose run` has no `--no-build`; the Makefile builds the image only when missing (`REBUILD=1` forces it);
- the local-files storage path must be strictly inside `LOCAL_FILES_DOCUMENT_ROOT`; audio is served from `/label-studio/files/served`, URLs `?d=served/<id>.wav`;
- `GET /api/projects/{id}/tasks/` returns 404 for an empty project; the client uses `GET /api/tasks?project=ID`;
- `POST /api/users/` requires `username` and ignores `password`; the password is set through Django inside the container;
- Community Edition has no roles: every user can delete tasks (documented in `evaluation/README.md`, accepted).

Other points:
- T001 was verified by reading the `label-studio==1.23.2` sdist, not a running container (see research R14). Response shapes (project list pagination, `completed_by` in the JSON export, `alias` in choice results) are parsed defensively and must be confirmed by the docker tests.
- (superseded by the list above) Local files serving needs a per-project Local files storage (R14); `provision` registers it. The `d=` URLs are relative to `LABEL_STUDIO_LOCAL_FILES_DOCUMENT_ROOT=/label-studio/files` (audio mounted at `/label-studio/files/served`, URLs `?d=served/<id>.wav`).
- The docker backup/restore test annotates through the API passing `completed_by`; the operator reported the docker tests as passing.
- The provisioner mounts the voice library read-only (needed to cut SIM reference clips), which the compose contract did not list.

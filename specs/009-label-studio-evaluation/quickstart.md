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

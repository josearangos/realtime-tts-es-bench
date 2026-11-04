# Contract: Operator Commands

All targets run `evaluation/scripts/preflight.sh` first. Failure messages name the missing piece (runtime absent/stopped, port in use with hint `LS_PORT=…`, `.env` missing, placeholder password).

| Target | Effect |
|---|---|
| `make eval-up` | build/pull if needed, start Label Studio, wait healthy, run `prepare` + `provision` |
| `make eval-down` | stop containers, keep volumes |
| `make eval-reset` | after typing `RESET`: remove volume and `output/evaluation/` |
| `make eval-backup` | produce `backups/evaluation/<UTC>.tar.gz` (brief stop for consistency) |
| `make eval-restore FILE=…` | restore into a clean environment, refuse if data exists unless confirmed |
| `make eval-export [OUT=dir]` | write export + quality report (default `results/human/`) |
| `make eval-new-batch` | archive current batch dir, prepare and provision a new batch |
| `make eval-annotator ID=a01` | create pseudonymous annotator, print credentials once |
| `make eval-purge-voice VOICE=…` | delete that voice's served audio, tasks and mapping rows (consent withdrawal) |
| `make eval-inspect` | print annotator-visible task data |

Python CLI (`python -m tts_bench.evaluation`): `prepare`, `provision --url --token`, `export`, `quality`, `purge-voice`, `annotator`. Exit codes: 0 ok, 2 usage/config error, 3 Label Studio unreachable/timeout, 4 scale-hash mismatch.

Label Studio REST endpoints used (to be verified against the pinned tag): health, list/create projects, list/import tasks, delete tasks, list/create users, export annotations (JSON).

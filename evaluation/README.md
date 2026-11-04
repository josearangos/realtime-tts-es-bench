# Human evaluation with Label Studio (containerized)

A loopback-only [Label Studio](https://labelstud.io) **Community Edition 1.23.2** with three Spanish projects built from the audio already synthesized by the benchmark:

| Project | What annotators do |
|---|---|
| **MOS – Evaluación de voz** | one audio, three 1–5 ratings: naturalidad, pronunciación, prosodia |
| **CMOS – Comparación A/B** | two audios, 7-point comparison of B against A |
| **SIM – Parecido de voz** | reference + clip of a cloned voice, 1–5 voice similarity |

Annotators never see an engine, voice, accent or sentence id. The mapping from opaque ids to conditions stays in `output/evaluation/private/` and is never mounted into the container.

## Host requirements

- Docker with **Compose v2** (`docker compose version`), the daemon running. Podman is not tested.
- A free port (default `8080`), about 2 GB of disk for the image and staged audio.
- `make` and Python 3.11 with `numpy` (the repository's core venv) to run the CLI targets (`export`, `annotator`, `inspect`, `purge-voice`).
- Synthesized audio from the earlier features (`output/speaker/*`, `output/intelligibility/*`) or a `--source-manifest` JSONL.

## Quickstart

```bash
cp evaluation/.env.example evaluation/.env     # 1. edit the password and token
make eval-up                                   # 2. build, start, prepare and provision
open http://127.0.0.1:8080                     # 3. log in with LS_ADMIN_USER / LS_ADMIN_PASSWORD
make eval-annotator ID=a01                     #    create each annotator; the password is shown once
```

The first start builds the images and needs the network. Afterwards `make eval-up` detects the images and starts with `--no-build`, so it works offline.

## Commands (`make help`)

| Target | Effect |
|---|---|
| `make eval-up` | start Label Studio, wait until healthy, run `prepare` + `provision` (skip with `EVAL_PROVISION=0`) |
| `make eval-down` | stop containers, keep data |
| `make eval-reset` | delete the data volume and `output/evaluation/` after typing `RESET` |
| `make eval-backup` | archive the volume and `output/evaluation/` to `backups/evaluation/<UTC>.tar.gz` (Label Studio stops briefly) |
| `make eval-restore FILE=…` | restore a backup; verifies checksums first; refuses to overwrite data without `CONFIRM=RESTORE` |
| `make eval-export [OUT=dir]` | write `annotations.jsonl/.csv`, `quality.json`, `MANIFEST.json` (default `results/human/`) |
| `make eval-new-batch` | archive the current batch and prepare a new one (change `seed` in `batch.toml` first) |
| `make eval-annotator ID=a01` | create a pseudonymous annotator (`a01@eval.invalid`) |
| `make eval-purge-voice VOICE=…` | remove one voice's audio, tasks and mapping rows (consent withdrawal) |
| `make eval-inspect` | print exactly what annotators can see |

Every target runs `evaluation/scripts/preflight.sh` first.

## Configuration

`evaluation/batch.toml` defines the seed, sentences per condition, repeat and attention rates, loudness and quality thresholds. It is frozen once `batch.json` exists: changing it (or the corpus) requires `make eval-new-batch`.

`evaluation/.env` (git-ignored): `LS_VERSION`, `LS_BIND`, `LS_PORT`, `LS_ADMIN_USER`, `LS_ADMIN_PASSWORD`, `LS_API_TOKEN`, `EVAL_PROVISION`. These are local credentials, not vendor API keys.

## Security

- The port is bound to `127.0.0.1` by default; sign-up is disabled and telemetry and update checks are off.
- To let annotators on your network connect, set `LS_BIND=0.0.0.0` (or an address) **and** replace the placeholder password and token: preflight refuses `change-me` values on a non-loopback bind. Traffic is **plain HTTP**: use a trusted network or put a TLS reverse proxy in front.
- Label Studio Community Edition has no per-project assignment: every annotator can open every project, and the organizer asks each person to complete whole projects. Only Community Edition features are used.
- Community Edition also has no roles: every logged-in user has all permissions, including deleting tasks. Give accounts only to trusted annotators, back up with `make eval-backup`, and export regularly. `make eval-up` re-imports deleted tasks, but their annotations are lost.

## Loudness

Every staged clip, including SIM reference clips, is RMS-normalized to −23 dBFS with a −1 dBFS peak limiter (same treatment for all engines; originals untouched). This is RMS, not ITU-R BS.1770 LUFS, to keep the provisioner dependency-free. A very peaky clip ends below −23 dBFS because the limiter wins.

## Troubleshooting

| Symptom | Fix |
|---|---|
| `port 8080 is already in use` | set `LS_PORT=8081` in `evaluation/.env` |
| `the Docker daemon is not running` | start Docker, retry |
| `evaluation/.env not found` | `cp evaluation/.env.example evaluation/.env` |
| first `eval-up` is slow | it builds two images; later starts reuse them |
| files not readable | `chmod -R u+rwX,go+rX output/evaluation` |
| `the data volume was created with Label Studio X` | you changed `LS_VERSION`. Back up (`make eval-backup`), then retry with `EVAL_ALLOW_UPGRADE=1`, or restore the old version in `.env` |
| `scale definitions differ` (exit 4) | scales or anchors changed after the batch was frozen; revert, or start a new batch deliberately |

Exit codes of `python -m tts_bench.evaluation`: 0 ok, 2 usage/config error, 3 Label Studio unreachable, 4 scale-hash mismatch.

## Tests

`pytest tests/evaluation -q` runs with a fake dataset and an in-process fake Label Studio (no engines, no Docker). `pytest -m docker tests/evaluation/docker` runs against the real stack.

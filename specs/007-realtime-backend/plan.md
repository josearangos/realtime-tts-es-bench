# Implementation Plan: Real-Time Synthesis Backend

**Branch**: `007-realtime-backend` | **Date**: 2026-11-03 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/007-realtime-backend/spec.md`

## Summary

Add a package `tts_bench.backend`: a local HTTP/WebSocket service that exposes every registered engine through one interface. A thin **gateway** process (the only one that listens on a port) never imports an engine. For each engine it lazily starts one **worker subprocess** running `python -m tts_bench.backend.worker ENGINE` with that engine's own virtual environment, so the existing rule "one engine per process" and per-engine dependency isolation hold unchanged. The worker wraps the existing adapter, streams chunks to the gateway over a framed stdio pipe, and measures TTFA, generation time, audio duration and RTF with the **same function the offline harness uses** (extracted from `metrics/runner.py` into a shared pure helper, then used by both). The gateway forwards chunks to the client as they arrive, serializes requests per engine (bounded queue), cancels on disconnect, and lists engines and voices with availability. Tests use the fake engine in-process through a worker entry that needs no venv and no weights (FR-011). See [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/) and [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: Python 3.11 (repo requires >=3.11)

**Primary Dependencies**: gateway only: `fastapi` + `uvicorn` (optional extra `backend = ["fastapi", "uvicorn"]`, test extra `httpx` for the ASGI client). Workers: the existing adapter code and the engine's own dependencies; no new dependency inside engine venvs. `numpy` (core) for PCM conversion.

**Storage**: no database. Request log as JSON Lines in `output/backend/requests.jsonl` (git-ignored; holds engine, voice name, text length and hash, timings, outcome; never the text by default and never audio). Engine venv locations from an optional git-ignored `backend.toml`; built-in defaults are an explicit map (`fake`→`.venv-core`, `phonon`→`.venv-phonon`, `pocket_tts`→`.venv-pocket`, `piper`→`.venv-piper`), and any other engine falls back to `.venv-<name>`.

**Testing**: pytest in `tests/backend/`: ASGI test client against the gateway with `FakeAdapter` workers started as in-process threads or `python -m tts_bench.backend.worker fake` subprocesses (known delays, controlled chunk count, `fail_after_chunks`, `load_delay_s`, granularity `none`). An `@pytest.mark.engine` test starts a real worker per engine. No test needs weights or network.

**Target Platform**: macOS (Apple Silicon) and Linux, CPU, one local machine

**Project Type**: web-service (backend only; frontend is a later feature) plus a small CLI to start it

**Performance Goals**: gateway overhead per chunk negligible next to chunk production: forwarding adds under 5 ms p95 on the fake engine (measured in a test, reported, not a benchmark result). No throughput target; one active synthesis per engine.

**Constraints**: local-first (binds to `127.0.0.1` by default; no network after setup); one engine per worker process; metric definitions identical to `docs/metrics.md`; reference audio, voice files and paths never leave the process (FR-010); input limit default 500 characters, lower if the engine's descriptor limit is lower; request timeout bounded.

**Scale/Scope**: a handful of engines, one tester at a time (a few concurrent clients at most); about 10 small modules.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | TTFA is first-class in every response; sentence-level engines show granularity next to TTFA; `none` engines report TTFA "not available" |
| II Spanish by Default | Pass | input is Spanish; each voice's accent label is listed and echoed in responses; no other language is advertised |
| III Apples-to-apples | **Pass, with care** | one worker per engine preserves one-engine-per-process; but live numbers come from a shared machine with a gateway and possibly other workers running, so every response and the log are labeled `interactive` and docs state they are not benchmark results and must not be compared with `results/perf/` figures. Queue wait is reported separately and never counted in TTFA |
| IV Deterministic vs human | Pass | only deterministic latency reported; no quality claim |
| V Honest reporting | Pass | each response carries engine version, model id, granularity, voice and accent; unavailable figures are "not available", never estimated; the log records the request |
| VI Licensing/consent | **Pass, with care** | all voices in the library are authorized (standing confirmation in Principle VI) and listed; resolved only through `LocalVoiceLibrary.resolve(..., use="internal_benchmarking")`; the listing exposes name, kind, cloned flag and accent label only: no path, hash, recording id or consent id. Non-commercial and copyleft flags are shown in the listing. No endpoint serves files from `cloned_voices/` or any voice material. Generated audio is returned to the requesting client only and is not stored |
| VII Modular | Pass | backend imports metrics helpers and adapters but metrics, corpus and voices never import the backend; engines stay behind adapters, no engine-specific code in the gateway |
| VIII Verifiable | Pass | each FR maps to a fake-engine test; timing parity test compares backend and offline harness on the same fake engine; definitions are in `docs/backend.md` |

Post-design re-check: no violations. Changes to existing code: (1) extracting the timing computation in `metrics/runner.py` into a shared pure function with unchanged behavior; (2) a load-free `check_ready()` hook on `BaseAdapter`, implemented by the three real adapters so availability and missing weights are reported without loading a model (FR-006). Existing metrics and adapter tests must still pass. Complexity Tracking not needed.

## Decisions to Confirm Before Task Generation

Proposed defaults (the maintainer may override; see [research.md](research.md)):

1. **Process model**: gateway plus one lazily started worker subprocess per engine, each in the engine's venv. Alternative (swap engines inside one process) rejected: it breaks the one-engine-per-process guard and mixes memory figures.
2. **Transport**: WebSocket `/v1/ws/synthesize` for streaming (binary PCM frames + JSON control/summary), plus `POST /v1/synthesize` returning one WAV with timings in a JSON header, for curl and non-streaming engines.
3. **Audio format on the wire**: 16-bit little-endian PCM mono at the engine's native sample rate (never resampled), announced in a start message.
4. **Concurrency**: one active synthesis per engine; up to 2 waiting; a further request is rejected immediately with 429 `engine_busy`. Queue wait is reported as `queue_wait_ms`.
5. **Input limit**: 500 characters default (`TTS_BACKEND_MAX_CHARS`), further limited by the engine descriptor; longer text is rejected (no silent splitting, because splitting changes TTFA meaning).
6. **Cancellation**: client disconnect or `cancel` message stops the stream at the next chunk boundary; for engines with granularity `none` or `sentence` this is the end of the current unit. Documented bound in `docs/backend.md`; a worker that does not finish within 30 s is killed and restarted.
7. **Idle workers**: kept alive until the service stops (no auto-unload in v1) so first-request load time is reported once as `load_ms` and later requests are warm.
8. **Binding and access**: `127.0.0.1` only by default; no authentication (out of scope, spec Assumptions).

## Project Structure

### Documentation (this feature)

```text
specs/007-realtime-backend/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   └── api.md
├── checklists/requirements.md
└── tasks.md              # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/tts_bench/
├── metrics/
│   └── timing.py          # NEW shared pure helper: timing_from_marks(...) used by runner.py and the worker
├── core/adapter.py        # CHANGED: BaseAdapter.check_ready() (load-free readiness check, default no-op)
├── adapters/              # CHANGED: phonon, pocket_tts, piper implement check_ready()
└── backend/
    ├── __init__.py
    ├── __main__.py        # CLI: python -m tts_bench.backend serve [--host --port --config]
    ├── app.py             # gateway: routes, WebSocket, error mapping
    ├── config.py          # limits, venv paths, queue size (env + optional backend.toml)
    ├── catalog.py         # engine listing: descriptors, availability + reason, public voices
    ├── supervisor.py      # per-engine worker lifecycle, queue, cancel, kill/restart
    ├── protocol.py        # framed messages between gateway and worker
    ├── worker.py          # python -m tts_bench.backend.worker ENGINE (wraps the adapter)
    ├── wav.py             # PCM16 conversion and WAV packaging
    └── requestlog.py      # JSONL request log (foundational)

tests/backend/
├── conftest.py            # fake-engine worker + ASGI client fixtures
├── test_streaming.py      # US1
├── test_errors.py         # US1
├── test_timing_helper.py  # shared timing helper
├── test_timing.py         # US2 (5% tolerance)
├── test_timing_parity.py  # US2 (parity with the offline harness)
├── test_load_time.py, test_timeout.py, test_requestlog.py  # US2
├── test_protocol.py, test_wav.py  # foundational
├── test_overhead.py       # gateway forwarding overhead
├── test_catalog.py        # US3
├── test_concurrency.py
├── test_cancel.py
├── test_limits.py
├── test_privacy.py        # no paths/hashes/files exposed
├── test_offline.py        # no sockets opened beyond loopback
└── test_engines_real.py   # @pytest.mark.engine

docs/backend.md            # run, endpoints, metric definitions, limits, cancellation bound
```

**Structure Decision**: single project, new subpackage `tts_bench.backend`, following the layout of `speaker/` and `intelligibility/`. The gateway is the only module that needs `fastapi`; `worker`, `protocol`, `wav` and `timing` use the standard library plus `numpy`.

## Complexity Tracking

No constitution violations; none to justify. The worker-per-engine process model is the simplest design that satisfies both FR-001 (every engine, one interface) and the existing one-engine-per-process rule, so it is not a deviation.

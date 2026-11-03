# Real-time synthesis backend

A local HTTP/WebSocket service that exposes every registered engine through one interface. It is for interactive testing of Spanish synthesis; it is **not** a benchmark.

## Install and start

```bash
.venv-core/bin/pip install -e ".[dev,backend]"        # fastapi, uvicorn (+ httpx for tests)
.venv-core/bin/python -m tts_bench.backend serve      # http://127.0.0.1:8000
```

Options: `--host` (default `127.0.0.1`), `--port`, `--config backend.toml`, `--voices-dir cloned_voices`, `--log-text`. A non-loopback `--host` prints a warning: the backend has no authentication; only expose it on trusted networks. Exit codes: 1 usage error, 2 when `fastapi`/`uvicorn` are missing.

The gateway never imports an engine. For each engine it lazily starts one worker subprocess (`python -m tts_bench.backend.worker ENGINE`) with that engine's own virtual environment, so the one-engine-per-process rule still holds. Workers stay alive until the service stops, so `load_ms` is reported once, by the request that triggered the load.

### Venv map and `backend.toml`

Defaults: `fake` → `.venv-core`, `phonon` → `.venv-phonon`, `pocket_tts` → `.venv-pocket`, `piper` → `.venv-piper`, any other engine `.venv-<name>`, each as `<repo>/<venv>/bin/python`. `backend.toml` (git-ignored, optional):

```toml
host = "127.0.0.1"
port = 8000
max_chars = 500
queue_waiting = 2
cancel_grace_s = 30
request_timeout_s = 60
voices_dir = "cloned_voices"
log_text = false

[venvs]
phonon = "/abs/path/to/.venv-phonon"
```

## Endpoints

| Endpoint | Purpose |
|----------|---------|
| `GET /v1/health` | `{status, version, limits: {max_chars, queue_waiting}}`; works with no engine installed |
| `GET /v1/engines`, `GET /v1/engines/{name}` | listing; never starts a loading worker |
| `POST /v1/engines/refresh` | re-probe availability |
| `POST /v1/engines/{name}/load` | load the engine now, returns `{load_ms}` |
| `WS /v1/ws/synthesize` | streaming: `start`, repeated `chunk` + binary PCM, `summary` or `error` |
| `POST /v1/synthesize` | one WAV; timings in header `X-TTS-Summary`; `X-TTS-Streaming: unavailable` for engines that do not stream |

Request body: `{"engine", "voice", "text", "options": {"request_id"}}`. Audio on the wire is 16-bit little-endian PCM mono at the engine's native sample rate (never resampled). Errors are `{error, message, available?, limit?, received?, queue_depth?}`; codes: `unknown_engine` (404), `unknown_voice` (400), `engine_unavailable` (409), `voice_not_permitted` (403), `text_empty`, `text_too_long` (400), `engine_busy` (429), `synthesis_failed`, `empty_audio`, `worker_crashed` (500), `worker_timeout` (504).

## Metric definitions

Identical to [metrics.md](metrics.md); computed by the same function (`metrics/timing.py`) as the offline harness.

| Metric | Start instant | End instant | Unit |
|--------|---------------|-------------|------|
| Generation time (`generation_ms`) | just before the synthesis call (`request_started_ns`) | last audio delivered (`finished_ns`) | ms |
| TTFA (`ttfa_ms`) | `request_started_ns` | first non-empty audio chunk delivered | ms |
| Audio duration (`audio_seconds`) | n/a | n/a | samples per channel / sample rate, never resampled |
| RTF (`rtf`) | n/a | n/a | generation time / audio duration |
| Chunk latency (`at_ms`, `gap_ms`) | `request_started_ns` | each chunk's delivery; gap = since previous chunk | ms |
| Queue wait (`queue_wait_ms`) | request accepted | engine slot acquired | ms, separate quantity |
| Load time (`load_ms`) | worker asked to load | `load()` returns | ms, separate quantity, only on the request that loaded the engine |

`total time` in the feature specification is `generation_ms` in the API. Queue wait and load time are never added to TTFA, generation time or RTF. TTFA is `"not available"` for engines with granularity `none`; for `sentence` granularity it equals the first sentence's latency and the granularity is echoed next to it.

**Interactive figures are not benchmark results.** Every summary carries `kind: "interactive"`. They come from a shared machine that also runs the gateway and possibly other workers, and MUST NOT be compared with the `results/perf/` figures (Constitution Principle III).

## Limits and policies

- **Input limit**: 500 characters by default (`TTS_BACKEND_MAX_CHARS` or `max_chars`), lowered to the engine's own limit when that is smaller. Longer text is rejected with `text_too_long` (`limit`, `received`); text is never split or truncated.
- **Concurrency**: one active synthesis per engine, up to 2 waiting; a further request gets `engine_busy` (`queue_depth`) immediately. Different engines run concurrently and `concurrent_engines` reports how many others were active when the request started.
- **Cancellation**: closing the WebSocket (or sending `{"cancel": true}`) stops the stream at the next chunk boundary; for `sentence` and `none` granularity that is the end of the current unit. A worker that is not idle within 30 s (`cancel_grace_s`) is killed and restarted; the next request reloads and reports a new `load_ms`.
- **Timeout**: `request_timeout_s` (60 s) bounds a request; the outcome is `worker_timeout`.

## Listing fields and availability

Each engine listing has `name`, `engine_version`, `model_id`, `license_code`, `license_model`, `license_flags` (`non-commercial`, `copyleft` are shown), `language`, `spanish_variant`, `supports_cloning`, `voice_kind`, `streaming.granularity`, `input_limit_chars`, `voices`, `availability`, `state`, `queue_depth`. `availability` is `{status: available}` or `{status: unavailable, reason: venv_missing | not_installed | weights_missing | error, hint}`; availability is probed with a load-free check (`--describe`), and a load that fails at request time flips it to unavailable with the same reason. `engine_version` reads `unknown (read at load)` until the worker loads.

`spanish_variant` at engine level is indicative; the voice's `accent_label` is the accent to report (for `piper` it follows the selected voice).

## Voices and consent

Voices come from `LocalVoiceLibrary`, resolved with `use="internal_benchmarking"`. All voices in the library are authorized (standing confirmation, Constitution Principle VI) and are listed. A voice object exposes only `name`, `kind`, `cloned`, `accent_label`. No route returns a voice file, reference audio, hash, recording id, consent id or filesystem path; error messages and log lines have absolute paths replaced by `<path>`. Generated audio goes only to the requesting client and is never stored. The service makes no network connection.

## Request log

`output/backend/requests.jsonl` (git-ignored, rotated at 5 MiB, 3 files kept): one JSON line per request with `ts`, `request_id`, `engine`, `engine_version`, `model_id`, `voice`, `text_chars`, `text_sha256`, `status` (`ok`, `failed`, `invalid`, `cancelled`, `rejected`), `error`, `summary`, `concurrent_engines`. The text itself only with `--log-text`; never audio.

## Deviations

Quickstart run (fake engine and the real `phonon`, `pocket_tts`, `piper` venvs with cached weights): health, listing, POST with `piper` (WAV, `granularity: sentence`, TTFA equals generation time), unknown-engine error with `available`, request log and clean shutdown of workers all behaved as specified. `pocket_tts` was listed `available` because its weights are cached on that machine; without the cache it is listed `unavailable` with `weights_missing` and nothing is downloaded (covered by `tests/unit/test_check_ready.py`).

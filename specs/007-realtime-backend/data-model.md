# Data Model: Real-Time Synthesis Backend

All types are plain JSON; field names are the wire names (see [contracts/api.md](contracts/api.md)).

## SynthesisRequest

| Field | Type | Rules |
|-------|------|-------|
| `engine` | string | must be a registered engine and available; else error listing available engines |
| `voice` | string | must belong to the engine and be permitted for live testing; else error listing the engine's voices |
| `text` | string | Spanish; non-empty after trim; length <= min(config limit, engine `max_chars`) |
| `options.stream` | bool | default true; ignored (with a notice) for granularity `none` |
| `options.request_id` | string, optional | client-chosen id echoed back; generated if absent |

## EngineListing

| Field | Notes |
|-------|-------|
| `name`, `engine_version`, `model_id` | version may read "unknown (read at load)" until the worker loads |
| `license_code`, `license_model`, `license_flags` | flags such as `non-commercial`, `copyleft` shown prominently |
| `language`, `spanish_variant` | accent of the engine/voices |
| `supports_cloning`, `voice_kind` | |
| `streaming.granularity` | `chunk` \| `sentence` \| `none` |
| `input_limit_chars` | effective limit for this engine |
| `voices[]` | `{name, kind, cloned, accent_label}` only |
| `availability` | `{status: available \| unavailable, reason: venv_missing \| not_installed \| weights_missing \| error, hint}` |
| `state` | `not_started` \| `loading` \| `ready` \| `busy`; `queue_depth` |

State transitions: `not_started` -> `loading` (first request or explicit load) -> `ready` <-> `busy`; any state -> `not_started` after a worker kill/crash (next request reloads and reports a new `load_ms`).

## AudioStream (WebSocket)

Messages, in order:

1. `start` (JSON): `request_id`, `engine`, `engine_version`, `model_id`, `spanish_variant`, `voice`, `accent_label`, `granularity`, `sample_rate`, `channels`, `sample_format: "s16le"`, `streaming: true|false`, `queue_wait_ms`, `load_ms` (only when this request triggered the load), `concurrent_engines`.
2. `audio` (binary frame, repeated): PCM s16le; preceded by a small JSON `chunk` message `{index, at_ms, gap_ms, samples}` where `at_ms` is measured from request start by the worker (same as `ChunkTiming` in feature 004).
3. `summary` (JSON, last): `TimingSummary` below, or `error` instead.

For `streaming: false` (granularity `none`), one audio frame carries the complete audio and `start` includes `streaming_available: false` with a notice.

## TimingSummary

| Field | Definition |
|-------|------------|
| `ttfa_ms` | request start to first non-empty chunk; `"not available"` for granularity `none` |
| `generation_ms` | request start to last audio delivered by the engine |
| `audio_seconds` | samples per channel / sample rate, no resampling |
| `rtf` | `generation_ms / 1000 / audio_seconds`; absent for zero audio (status `invalid`) |
| `chunks` | count |
| `queue_wait_ms` | time waiting for the engine; never included above |
| `load_ms` | present only when this request loaded the engine |
| `granularity` | echoed next to TTFA |
| `kind` | always `"interactive"` (not a benchmark result) |

Definitions are those of `docs/metrics.md`, computed by `metrics/timing.py`.

## ErrorBody

`{error: code, message, available?: [...], limit?: n, received?: n, queue_depth?: n}` with codes: `unknown_engine`, `unknown_voice`, `engine_unavailable`, `voice_not_permitted`, `text_empty`, `text_too_long`, `engine_busy`, `synthesis_failed`, `empty_audio`, `worker_timeout`, `load_failed`, `cancelled`. Messages never contain filesystem paths.

## RequestLogEntry

`ts`, `request_id`, `engine`, `engine_version`, `model_id`, `voice`, `text_chars`, `text_sha256`, `status` (`ok|failed|invalid|cancelled|rejected`), `error?`, `summary?`, `concurrent_engines`. Text only with `--log-text`.

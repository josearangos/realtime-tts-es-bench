# Data Model: Real-Time Testing Frontend

In-memory, per page session. Field names for backend data are the wire names from [007 data-model](../007-realtime-backend/data-model.md). Nothing here is persisted.

## EngineOption (from `GET /v1/engines`)

| Field | Use |
|-------|-----|
| `name`, `engine_version`, `model_id` | shown in the selector and on panels |
| `license_code`, `license_model`, `license_flags` | license line and warning banner (FR-008) |
| `streaming.granularity` | `chunk` \| `sentence` \| `none`; shown beside TTFA (FR-011) |
| `supports_cloning` | badge (FR-001) |
| `input_limit_chars` | counter and Play gating |
| `voices[]` | `{name, kind, cloned, accent_label}` only; accent shown (FR-012) |
| `availability` | `status`, `reason`, `hint`; unavailable engines are disabled with reason (FR-001) |
| `state`, `queue_depth` | informational |

Derived: `restrictive = license_flags` contains `non-commercial` or `copyleft`, or any unknown flag.

## CorpusEntry (from `GET /v1/corpus`)

`{id, text, campaign, scenario, tags}`; `text` is the spoken form. Response also carries `corpus_version`. Choosing one copies `text` into the input in one action (scenario 3.3).

## ComparisonSession

| Field | Notes |
|-------|-------|
| `text` | the single text sent to every selected engine (the same string for all panels) |
| `panels[]` | ordered `EnginePanel`s, one per selected engine, order = run order |
| `state` | `idle` -> `running` -> `finished` \| `stopped` |
| `current` | index of the running panel, or none |

A single-engine request is a session with one panel. Starting a new session replaces the previous one (its stored audio is discarded).

## EnginePanel

| Field | Notes |
|-------|-------|
| `engine`, `voice` | chosen by the tester per panel |
| `state` | `waiting` -> `connecting` -> `streaming` -> `playing` -> `done`; or `failed`, `cancelled`, `not_run` |
| `start` | the backend `start` message (sample rate, accent, granularity, `streaming_available`, `queue_wait_ms`, `load_ms`) |
| `chunks[]` | received PCM as `Int16Array`, with the backend `chunk` metadata `{index, at_ms, gap_ms, samples}` |
| `summary` | the backend `summary` message, unmodified |
| `error` | backend `error` body (`error`, `message`, `available?`, ...) or `backend_unreachable` |
| `browser` | `{sent_at, first_chunk_at, first_audio_scheduled_at, ended_at}` browser clock readings; `heard_after_ms = first_audio_scheduled_at - sent_at` |
| `underruns` | count of chunks that arrived after their scheduled play time |
| `audio_blocked` | true while the audio context is suspended |

State transitions:

```text
waiting -> connecting -> streaming -> playing -> done
              |             |           |
              +-> failed ---+-----------+      (backend error or unreachable)
any running state -> cancelled                  (Stop)
waiting -> not_run                              (Stop before this panel started)
done -> playing -> done                         (Replay, no request)
```

Rules:

- Exactly one panel is in `connecting`/`streaming`/`playing` at a time during a session (sequential rule, FR-005); the next panel moves from `waiting` to `connecting` only after the previous reaches `done`, `failed` or `cancelled`.
- A `failed` panel does not stop the session; remaining panels still run.
- `summary` values are displayed as received. `ttfa_ms` equal to `"not available"` renders the explanation (FR-004).

## CorpusPicker

Filterable list over `CorpusEntry` (by campaign or free text); one activation copies the entry's `text` to the input. Holds no other state.

## Derived display values

| Display | Source | Rule |
|---------|--------|------|
| TTFA | `summary.ttfa_ms` | number -> "N ms"; `"not available"` -> label + explanation |
| Total time | `summary.generation_ms` | "N ms" |
| Audio duration | `summary.audio_seconds` | "N s" |
| RTF | `summary.rtf` | as sent; absent -> "not available" |
| Granularity | `summary.granularity` | next to TTFA |
| Queue wait / load | `summary.queue_wait_ms`, `load_ms` | separate lines; "includes model load" tag when `first_request_after_load` |
| Heard after | `browser` | labelled "browser-side, not a benchmark number" |

Rounding for display keeps the precision the backend sent (no recomputation), so shown values equal reported values (SC-002).

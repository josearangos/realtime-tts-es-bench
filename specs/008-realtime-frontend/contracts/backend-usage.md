# Contract: What the Page Consumes from the 007 Backend

The authoritative API is [007 contracts/api.md](../../007-realtime-backend/contracts/api.md). This file lists only what the page relies on, so a backend change that breaks the page is visible.

Base URL: `http://127.0.0.1:8000` by default; the page takes an editable "Backend URL" field (stored only in memory).

## Calls

| Purpose | Call | Fields used |
|---------|------|-------------|
| Reachability, limits | `GET /v1/health` | `status`, `limits.max_chars` |
| Engine and voice list | `GET /v1/engines` | see EngineOption in [data-model.md](../data-model.md) |
| Re-probe availability | `POST /v1/engines/refresh` | same body as the list; triggered by a "Refresh" button |
| Corpus sentences | `GET /v1/corpus` | new, see [backend-additions.md](backend-additions.md) |
| Synthesis | `WS /v1/ws/synthesize` | below |

The page does **not** call `POST /v1/synthesize` or `POST /v1/engines/{name}/load`.

## WebSocket exchange

Client sends one JSON message after the socket opens:

```json
{"engine":"fake","voice":"<voice name>","text":"<Spanish text>","options":{"request_id":"<page-generated>"}}
```

Server messages the page handles, in order:

| Message | Page behavior |
|---------|---------------|
| `{"type":"start", ...}` | store on panel; create player at `sample_rate`; show accent, granularity, `queue_wait_ms`, `load_ms`; if `streaming_available === false` show the notice |
| `{"type":"chunk","index","at_ms","gap_ms","samples"}` followed by one binary frame | pair the metadata with the next binary frame; convert s16le (little endian, `channels` = 1) and schedule; first one starts playback |
| `{"type":"summary", ...}` | store unmodified; render metrics; mark audio complete |
| `{"type":"error","error","message", ...}` | mark panel `failed`; show backend message; for `unknown_engine`/`unknown_voice` list `available` |

Client sends `{"cancel":true}` then closes the socket on Stop.

If the socket closes before `start` without an `error` message, or the connection cannot be opened, the panel is `failed` with `backend_unreachable` and the page shows a banner with the start command (`python -m tts_bench.backend serve`).

## Assumptions the page makes (verified by tests)

1. A `chunk` metadata message always precedes its binary frame.
2. `sample_format` is `s16le`, `channels` is 1; any other value is shown as an error, not played.
3. `summary` is the last message of a successful request.
4. `ttfa_ms` is a number or the exact string `"not available"`.
5. The engine listing never contains a path, hash, recording id or consent id; the page renders only the fields in EngineOption, and a test fails if the listing includes unexpected voice fields that the page would display.

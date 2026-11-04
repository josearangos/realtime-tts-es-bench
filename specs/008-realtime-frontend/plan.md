# Implementation Plan: Real-Time Testing Frontend

**Branch**: `008-realtime-frontend` | **Date**: 2026-11-04 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/008-realtime-frontend/spec.md`

## Summary

Add `frontend/`: a static, no-build web page (plain HTML, CSS and ES modules, zero npm runtime dependencies) that talks to the 007 backend. It lists engines and voices from `GET /v1/engines`, streams audio over `WS /v1/ws/synthesize`, plays PCM chunks through the Web Audio API as they arrive (first chunk starts playback), and displays the backend's `summary` values verbatim. A comparison runs the selected engines **sequentially** (clarification 2026-11-04), one panel per engine, each storing its audio for replay without a new request. The page is served by a trivial loopback static server (`python -m http.server` on `127.0.0.1:5173`), separate from the gateway.

The backend needs two small additions (see [contracts/backend-additions.md](contracts/backend-additions.md)): a read-only `GET /v1/corpus` endpoint for the corpus picker, and opt-in CORS for the loopback frontend origin. Neither exposes voice material. See [research.md](research.md), [data-model.md](data-model.md), [contracts/](contracts/) and [quickstart.md](quickstart.md).

## Technical Context

**Language/Version**: JavaScript (ES2022 modules, no transpile) for the page; Python 3.11 for the two backend additions.

**Primary Dependencies**: browser built-ins only (`fetch`, `WebSocket`, Web Audio API). No bundler, framework or CDN, so the page works fully offline (FR-009). Node (already installed, used only for tests) runs `node --test`; no `package.json` dependencies.

**Storage**: none persistent. Session results (PCM chunks plus summary per panel) live in memory and are lost on reload (spec Assumptions).

**Testing**: `node --test` for pure logic modules (message parsing, PCM conversion, sequential run controller, license-warning rules, formatting of "not available", view model) against a scripted fake WebSocket; one Node end-to-end script that drives the real gateway with the **fake engine** (known delays) and asserts first audio arrives before `summary` and displayed values equal the summary (SC-001, SC-002); pytest in `tests/backend/` for `/v1/corpus`, CORS and privacy of the new endpoint. No test needs weights, a browser or network.

**Target Platform**: current desktop Chrome, Safari and Firefox on macOS and Linux, against a gateway on the same machine.

**Project Type**: web application, frontend only (backend exists from 007).

**Performance Goals**: playback begins within one animation frame plus one audio-scheduling quantum (a few ms) of the first chunk's arrival; measured in the Node end-to-end test as "first chunk handed to playback before `summary` received" and reported, not a benchmark result.

**Constraints**: no external network (no CDN fonts or scripts); binds to loopback only; shows the backend's numbers unmodified (SC-002); never requests or renders voice paths, hashes or files (FR-010); engines run one at a time (FR-005).

**Scale/Scope**: one tester, up to all registered engines in one comparison (a handful), about 8 small modules and one page.

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | TTFA is shown first; granularity is shown next to it (FR-011); `not available` is explained, never estimated |
| II Spanish by Default | Pass | UI text and corpus are Spanish-oriented; each voice shows its accent label (FR-012) |
| III Apples-to-apples | **Pass, with care** | Sequential comparison keeps engines from competing for CPU. Every result panel carries the backend's `interactive` label and a note that live figures are not benchmark results. Queue wait and load time are shown separately from TTFA. A cold first request is flagged ("includes load") using the backend's `first_request_after_load` |
| IV Deterministic vs human | Pass | only latency numbers; "sound" is judged by listening, no quality score is computed or stored |
| V Honest reporting | Pass | engine version, model id, voice, accent and granularity from the backend are shown on each panel; numbers are copied, not recomputed |
| VI Licensing/consent | **Pass, with care** | the listing exposes only name, kind, cloned flag and accent label; the page requests nothing else. License code, model license and flags are shown per engine with a prominent banner for `non-commercial` or `copyleft`. No upload, no recording, no file URLs. `/v1/corpus` serves `sentences.jsonl` text only, never `cloning.jsonl` (which holds reference texts for cloning) |
| VII Modular | Pass | `frontend/` imports nothing from Python; metrics, corpus and voices never import it. Backend gets two additive, opt-in changes and keeps its "no static serving" guarantee |
| VIII Verifiable | Pass | each FR maps to a logic test or the fake-engine end-to-end check (table in [quickstart.md](quickstart.md)) |

Post-design re-check: no violations. Changes to existing code: (1) `GET /v1/corpus` added to `backend/app.py` reading the corpus through `tts_bench.corpus.loader` (backend → corpus is the permitted direction); (2) CORS allowlist for configured origins, default the two loopback frontend origins. Existing 007 tests must still pass. Complexity Tracking not needed.

## Decisions to Confirm Before Task Generation

Proposed defaults (the maintainer may override; rationale in [research.md](research.md)):

1. **No framework, no build step**: plain ES modules served statically. Keeps the page offline-safe and trivially auditable; the UI is small (one form, N panels).
2. **Separate static server on 127.0.0.1:5173**, not mounted in the gateway, so 007's guarantee "no static file serving" stays true. Cost: CORS on the gateway for that origin.
3. **Transport**: `WS /v1/ws/synthesize` for every request (streaming and not); `POST /v1/synthesize` is not used by the page.
4. **Playback**: Web Audio; each PCM chunk becomes an `AudioBuffer` at the engine's native sample rate (the browser resamples at output), scheduled back to back from the first chunk with a small safety lead. Each panel keeps its chunks to replay without a request.
5. **Comparison**: strictly sequential; the next engine starts when the previous one's synthesis **and** playback have ended, so the tester hears panels in order without overlap. Stop cancels the running request and skips the rest.
6. **Text source for the corpus picker**: the sentence's spoken form (`spoken` if present, else `text`), matching what the offline benchmark synthesizes.
7. **Autoplay blocked**: the audio context is created/resumed on the tester's first click on Play; if it is still suspended, a visible "Enable audio" button is shown and the panel's audio is kept for replay.
8. **Limit display**: show `input_limit_chars` per engine with a live character counter; Play is disabled above the smallest limit among the selected engines, and the page names the engine that sets it.
9. **Interface language**: English labels and messages (FR-004 requires the literal "not available"); synthesized text and corpus stay Spanish. `index.html` uses `lang="en"`.
10. **Testable rendering**: all rendering decisions (which fields are shown, warnings, busy state, limit gating) live in a pure `view-model.js`; `view.js` only maps the model to DOM.
11. **Fake-engine configuration for tests**: the e2e script starts the gateway with `TTS_FAKE_FIRST_CHUNK_S`, `TTS_FAKE_CHUNK_INTERVAL_S`, `TTS_FAKE_CHUNKS`, `TTS_FAKE_AUDIO_S` and `TTS_FAKE_GRANULARITY` (existing 007 test hooks in `backend/worker.py`).

## Project Structure

### Documentation (this feature)

```text
specs/008-realtime-frontend/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── backend-usage.md       # what the page consumes from the 007 API
│   └── backend-additions.md   # the two small 007 additions
├── checklists/requirements.md
└── tasks.md                   # created by /speckit-tasks
```

### Source Code (repository root)

```text
frontend/
├── index.html
├── styles.css
├── src/
│   ├── main.js            # wiring: loads engines/corpus, handles form events
│   ├── api.js             # fetch engines/corpus; typed errors; backend-unavailable detection
│   ├── stream.js          # WebSocket client: start/chunk/audio/summary/error/cancel -> events
│   ├── pcm.js             # s16le ArrayBuffer -> Float32Array; duration from samples
│   ├── player.js          # Web Audio scheduling, replay, stop, autoplay-blocked state
│   ├── session.js         # sequential run controller (Comparison Session, Engine Panels)
│   ├── license.js         # warning rules from license_flags
│   ├── format.js          # "not available" + explanations, unit formatting (no recomputation)
│   ├── view-model.js      # pure: what each panel/selector shows (fields, warnings, busy state, limit gating)
│   └── view.js            # DOM rendering of the view model
└── tests/
    ├── fake-ws.js         # scripted WebSocket double
    ├── pcm.test.js, stream.test.js, session.test.js, license.test.js, format.test.js, view-model.test.js
    └── e2e-fake-engine.mjs  # drives the real gateway with the fake engine

src/tts_bench/backend/
├── app.py                 # CHANGED: GET /v1/corpus, CORS middleware
└── config.py              # CHANGED: cors_origins setting (env + backend.toml)

tests/backend/
├── test_corpus_endpoint.py   # NEW
└── test_cors.py              # NEW

docs/frontend.md           # run, what is shown, limits, "not a benchmark" note
```

**Structure Decision**: web-application layout but with the existing backend left where it is (`src/tts_bench/backend`); a new top-level `frontend/` directory holds the static page. No `package.json` runtime deps; tests use the Node built-in runner.

## Complexity Tracking

No constitution violations; none to justify.

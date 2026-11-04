# Quickstart: Real-Time Testing Frontend

Validation guide; no implementation code. Endpoint and message details: [contracts/](contracts/).

## Prerequisites

- Feature 007 installed: `pip install -e '.[backend,dev]'`.
- Node 20+ (tests only; the page itself needs no Node).
- Real engines are optional: every check below runs with the `fake` engine.

## Run

```bash
# terminal 1: backend (fake engine needs no weights)
python -m tts_bench.backend serve

# terminal 2: static server for the page, loopback only
python -m http.server 5173 --bind 127.0.0.1 --directory frontend
```

Open `http://127.0.0.1:5173`. No request leaves the machine (FR-009); to confirm, load the page with the network disabled.

## Automated checks

```bash
node --test frontend/tests/                 # logic modules, no browser, no backend
python -m pytest tests/backend/test_corpus_endpoint.py tests/backend/test_cors.py
node frontend/tests/e2e-fake-engine.mjs     # starts the gateway with the fake engine, asserts SC-001 and SC-002
```

## Manual scenarios

| # | Do | Expect | Covers |
|---|----|--------|--------|
| 1 | Open the page with the backend running | engines and voices listed; unavailable engines disabled with reason; cloning badge, accent, license shown | US1-1, FR-001, FR-008, FR-012 |
| 2 | Pick `fake`, type text, Play | audio starts while the fake engine is still producing chunks (the panel shows state `streaming`/`playing` before the summary appears) | US1-2, FR-002, SC-001 |
| 3 | Press Stop during playback | sound stops; panel `cancelled`; backend log shows `cancelled` | US1-3, FR-007 |
| 4 | After a request | TTFA, total time, audio duration, RTF equal the `summary` message values (compare with the browser network inspector or the e2e output) | US2-1, FR-003, SC-002 |
| 5 | Restart the backend with `TTS_FAKE_GRANULARITY=none` and use the fake engine | TTFA shows "not available" with the explanation; granularity shown | US2-2, FR-004, FR-011 |
| 6 | Select two engines, submit one text | panels fill one after another, no overlap; same text in each; second starts after the first has finished playing | US3-1, FR-005 |
| 7 | Press Replay on a finished panel | audio replays; backend log shows no new request | US3-2 |
| 8 | Choose a sentence in the corpus picker | it appears in the input with a single click | US3-3, FR-006 |
| 9 | Select a `non-commercial` or `copyleft` engine | prominent banner on the selector and its panel | FR-008, SC-004 |
| 10 | Stop the backend, press Play | clear "backend not reachable" message and the start command | edge case |
| 11 | Type text above the engine limit | limit and counter shown; Play disabled | edge case |
| 12 | Use a browser profile that blocks autoplay | "Enable audio" button; clicking it plays the stored audio | edge case |
| 13 | Compare two engines with different sample rates | both play at correct pitch and speed | edge case |
| 14 | Inspect page source and network tab | no voice paths, hashes or files requested or shown | FR-010 |
| 15 | With both engines already loaded (run each once first), time a two-engine comparison of one corpus sentence of 5 s of audio or less | under one minute | SC-003 |
| 16 | Select two engines with different limits (for example `TTS_FAKE_MAX_CHARS=50` on one) and type 60 characters | counter shows the smaller limit and names the engine that sets it; Play disabled | edge case |
| 17 | Send a request while the engine's queue is full | the panel shows the queue depth and a Retry button | edge case |

## Expected outcome

All automated checks pass and manual rows 1-17 behave as listed. Displayed timings are labelled interactive and are not benchmark results (see `docs/frontend.md`, written during implementation).

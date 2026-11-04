# Research: Real-Time Testing Frontend

No `NEEDS CLARIFICATION` items remained in the Technical Context. The decisions below record what was chosen and why.

## R1 - UI technology

- **Decision**: plain HTML, CSS and ES modules; no framework, bundler or runtime npm dependency.
- **Rationale**: the UI is one form plus N result panels. A build step and a dependency tree add maintenance and supply-chain surface for little gain, and FR-009 (no external network) is satisfied by construction when nothing is fetched from a CDN. Logic lives in small pure modules that Node can test without a browser.
- **Alternatives**: React/Vite (rejected: build tooling and node_modules for a small page); a Python-rendered UI such as Gradio (rejected: hides the streaming/playback behavior we must control and adds a heavy dependency).

## R2 - How the page is served

- **Decision**: a separate static server on loopback (`python -m http.server 5173 --bind 127.0.0.1 --directory frontend`), plus an opt-in CORS allowlist on the gateway.
- **Rationale**: 007 explicitly guarantees that no static file serving is mounted (protects `cloned_voices/`). Keeping that guarantee untouched is worth one small CORS setting.
- **Alternatives**: mount `frontend/` in the gateway (rejected: weakens the guarantee and couples release of the two); open `index.html` from `file://` (rejected: origin `null` makes CORS and WebSocket origin handling awkward).

## R3 - Audio playback of streamed PCM

- **Decision**: Web Audio API. Convert each s16le chunk to Float32, wrap it in an `AudioBuffer` with the engine's own `sample_rate`, and schedule buffers back to back with `AudioBufferSourceNode.start(t)`; the first buffer starts after a small lead (target 20 ms) so later chunks can be scheduled without gaps.
- **Rationale**: handles different sample rates per engine natively (the browser resamples at output), needs no decoder, and gives precise start times. Playback begins on the first chunk, satisfying FR-002.
- **Alternatives**: `<audio>` with MediaSource (rejected: PCM is not a supported container, would need re-encoding); AudioWorklet ring buffer (rejected: more code; revisit only if scheduling gaps are observed with real engines).
- **Known risk**: chunks that arrive later than their scheduled time cause an audible gap. The player records underrun count per panel and displays it (information for the tester, not a metric).

## R4 - Replay without a new request

- **Decision**: each panel keeps its received PCM chunks (`Int16Array` list) and summary in memory; Replay rebuilds buffers from them.
- **Rationale**: satisfies scenario 3.2 exactly; memory cost is small (seconds of mono audio per panel).
- **Alternatives**: re-request (rejected by the spec); store WAV in IndexedDB (rejected: persistence is out of scope).

## R5 - Sequential comparison and playback

- **Decision**: the run controller processes panels in order; the next request is sent only after the previous request's `summary` or `error` and after its playback finished. Stop sends `{"cancel":true}` to the running request, closes its socket, and marks unstarted panels "not run".
- **Rationale**: clarification 2026-11-04 (no overlap of engine load) plus a natural listening order. Waiting for playback to end also means the browser's own audio work never overlaps a later engine's synthesis.
- **Alternatives**: start next on `summary` while earlier audio is still playing (rejected: simultaneous playback of two engines is hard to listen to, and the next engine would start while the page is still busy decoding).

## R6 - Displaying timings so they equal the backend's

- **Decision**: render `ttfa_ms`, `generation_ms` (labelled "total time"), `audio_seconds` and `rtf` straight from the `summary` message; the page performs formatting only (rounding for display to the digits the backend sent, plus unit labels). The page may additionally show **"heard after"**: the browser's own time from sending the request to the first chunk handed to playback, labelled as a browser-side observation, never mixed with the backend TTFA.
- **Rationale**: SC-002; Constitution V (definitions live in `docs/metrics.md`, computed once in `metrics/timing.py`). The browser-side figure helps verify SC-001 and shows transport/scheduling overhead but is clearly a separate number.
- **Alternatives**: recompute RTF client-side (rejected: duplicates the definition and risks drift).

## R7 - "Not available" handling

- **Decision**: when `ttfa_ms` equals the string `"not available"`, or `start.streaming_available === false`, show "not available" with the explanation "This engine produces the whole audio at once, so there is no time to first audio." Granularity (`chunk`, `sentence`, `none`) is always shown beside TTFA, with a one-line meaning of each (FR-011).
- **Rationale**: FR-004, Constitution III and the streaming-granularity constraint.

## R8 - License warnings

- **Decision**: from the engine listing's `license_flags`: any of `non-commercial` or `copyleft` produces a prominent colored banner on the engine's selector and on every panel, naming the flag and showing `license_code` and `license_model`. An engine with no flags shows its license text without a banner. Unknown flag values are shown as a generic "restrictive license" warning (fail loud).
- **Rationale**: FR-008, SC-004, Constitution VI ("flagged prominently, verified per checkpoint").

## R9 - Corpus access

- **Decision**: new read-only `GET /v1/corpus` on the gateway returning `[{id, text, campaign, scenario, tags}]` for the `main` subset of `sentences.jsonl`, where `text` is the sentence's spoken form. It never reads `cloning.jsonl`.
- **Rationale**: the page must not bundle a copy of the corpus (it would drift from `corpus/VERSION.json`) and cannot read the repo through a static server pointed at `frontend/`. The endpoint also returns the corpus version so the panel can say which corpus text came from.
- **Alternatives**: copy `sentences.jsonl` into `frontend/` at build time (rejected: drift, extra step); let the user paste text only (rejected: FR-006).

## R10 - Backend unavailable and error mapping

- **Decision**: the page distinguishes (a) the gateway not reachable (fetch fails or WebSocket closes before `start` with no `error` message) -> banner "Backend not reachable at <url>; start it with ..."; and (b) backend `error` messages -> shown on the affected panel using the backend's `error` code and message, with `available` options for `unknown_*` codes. `engine_busy` shows the queue state and a Retry. Nothing fails silently.
- **Rationale**: spec edge cases; 007 error codes are stable (`contracts/api.md`).

## R11 - Testing without a browser

- **Decision**: all logic is in DOM-free modules (`stream`, `pcm`, `session`, `license`, `format`, `api`) so `node --test` can exercise them with a scripted WebSocket double. `player.js` and `view.js` are thin and checked manually via the quickstart. One Node script uses Node's global `WebSocket` against the real gateway running the fake engine.
- **Rationale**: Constitution VIII (no weights, deterministic fake engine); avoids a headless-browser dependency.
- **Alternatives**: Playwright (rejected for now: large download, and audio output cannot be asserted anyway).

## R12 - Autoplay policy

- **Decision**: create or resume the `AudioContext` inside the Play click handler. If `audioContext.state` is not `running` when the first chunk arrives, show an "Enable audio" button that resumes it and starts playing the stored chunks, and keep the audio in the panel for replay.
- **Rationale**: browsers allow audio only after a user gesture; the click on Play normally suffices, the button covers stricter policies (spec edge case).

---

description: "Task list for the Real-Time Testing Frontend"
---

# Tasks: Real-Time Testing Frontend

**Input**: Design documents from `/specs/008-realtime-frontend/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/ (backend-usage.md, backend-additions.md), quickstart.md. Feature 007 backend is already implemented.

**Tests**: Included. Constitution VIII requires every functional requirement to be verifiable with the fake engine, and plan.md specifies `node --test` logic tests, a fake-engine end-to-end script and two pytest files. No test needs weights, a browser or network.

**Organization**: Tasks are grouped by user story so each can be implemented and tested independently.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel (different files, no dependencies on incomplete tasks)
- **[Story]**: US1, US2, US3 (maps to spec.md user stories)
- Paths are repository-relative. Frontend code is plain ES modules in `frontend/src/`, no dependencies and no build step.

## Path Conventions

- Page: `frontend/index.html`, `frontend/styles.css`, `frontend/src/*.js`
- Frontend tests: `frontend/tests/*.test.js` (run with `node --test frontend/tests/`)
- Backend additions: `src/tts_bench/backend/`, tests in `tests/backend/`
- Docs: `docs/frontend.md`

---

## Phase 1: Setup (Shared Infrastructure)

**Purpose**: Create the `frontend/` skeleton.

- [X] T001 Create the directory layout from plan.md: `frontend/`, `frontend/src/`, `frontend/tests/`, with `frontend/index.html` (empty page that loads `src/main.js` as a module, `lang="en"` (interface text is English; synthesized text and corpus are Spanish), no external scripts, fonts or CDN links) and an empty `frontend/styles.css`
- [X] T002 [P] Add `frontend/tests/fake-ws.js`: a scripted `WebSocket` double that records sent messages, lets a test push JSON text frames and binary frames in order, and can simulate close and open failure
- [X] T003 [P] Confirm `.gitignore` does not exclude `frontend/` and that no `package.json` with runtime dependencies is added (the page is dependency-free); note the `node --test frontend/tests/` command in `frontend/README.md` (3 lines)

---

## Phase 2: Foundational (Blocking Prerequisites)

**Purpose**: Backend CORS (needed by every story) and the DOM-free modules every story uses.

**⚠️ CRITICAL**: No user story work can begin until this phase is complete.

- [X] T004 Add the `cors_origins` setting in `src/tts_bench/backend/config.py`: env `TTS_BACKEND_CORS_ORIGINS` (comma separated) and `backend.toml` key `cors_origins`; default `http://127.0.0.1:5173` and `http://localhost:5173`; empty list disables browser access; never `*`
- [X] T005 Add CORS middleware in `src/tts_bench/backend/app.py` using the setting from T004 (methods `GET, POST`, no credentials) and make `ws_synthesize` close with an `error` message before reading the request when a browser `Origin` header is present and not allowed; a request with no `Origin` header is still accepted (depends on T004)
- [X] T006 [P] Write `tests/backend/test_cors.py`: allowed origin gets `access-control-allow-origin` on `GET /v1/engines`; a disallowed origin does not; WebSocket with a bad `Origin` is rejected; WebSocket without `Origin` (test client) still works; empty list disables access; existing `tests/backend/test_privacy.py` still passes
- [X] T007 [P] Implement `frontend/src/pcm.js`: `s16leToFloat32(arrayBuffer)` (little-endian, channels = 1, output in [-1, 1)) and `durationSeconds(samples, sampleRate)`; reject any `sample_format` other than `s16le` or `channels` other than 1 with a typed error (contract assumption 2)
- [X] T008 [P] Write `frontend/tests/pcm.test.js`: known sample values convert exactly (0, 32767, -32768), odd byte length is rejected, non-`s16le` and stereo are rejected
- [X] T009 Implement `frontend/src/api.js`: `getHealth(baseUrl)`, `getEngines(baseUrl)`, `refreshEngines(baseUrl)`; a fetch failure or non-JSON response raises `BackendUnreachable` (R10) carrying the URL and the start command `python -m tts_bench.backend serve`; backend JSON error bodies raise `BackendError` with `error`, `message`, `available?`
- [X] T010 Implement `frontend/src/stream.js`: `openSynthesis(baseUrl, request, handlers, WebSocketImpl = WebSocket)` that sends the one JSON request on open, pairs each `chunk` metadata message with the next binary frame, and calls `onStart`, `onChunk(meta, int16)`, `onSummary`, `onError`, `onClose`; `cancel()` sends `{"cancel":true}` then closes; a close before `start` with no `error` message is reported as `backend_unreachable`; a binary frame with no pending `chunk` metadata is a protocol error (depends on T007)
- [X] T011 Write `frontend/tests/stream.test.js` with `fake-ws.js`: full happy path order; chunk/binary pairing; `error` message before audio; close before `start`; cancel sends the cancel message and closes; protocol error on an unpaired binary frame (depends on T002, T010)
- [X] T012 [P] Implement `frontend/src/license.js`: `licenseWarning(engine)` returns `{restrictive, flags, text}` where any of `non-commercial` or `copyleft` is restrictive and any unknown flag is also restrictive with generic text (R8); engines with no flags return no warning but still expose `license_code` and `license_model`
- [X] T013 [P] Write `frontend/tests/license.test.js`: `non-commercial`, `copyleft`, both, an unknown flag, and no flags
- [X] T014 [P] Implement `frontend/src/format.js`: display helpers that never recompute metrics: `fmtMs(value)`, `fmtSeconds(value)`, `fmtRtf(value)` keep the digits the backend sent; the exact string `"not available"` (or an absent `rtf`) renders "not available" plus an explanation chosen by granularity (`none`: whole audio produced at once, so no time to first audio); `granularityNote(granularity)` gives the one-line meaning of `chunk`, `sentence`, `none` (R6, R7, FR-011)
- [X] T015 [P] Write `frontend/tests/format.test.js`: numbers display unchanged, `"not available"` for TTFA with granularity `none`, absent `rtf`, granularity notes for all three values

**Checkpoint**: `node --test frontend/tests/` passes the foundational tests and `pytest tests/backend/test_cors.py` passes.

---

## Phase 3: User Story 1 - Type text and hear it live (Priority: P1) 🎯 MVP

**Goal**: Pick an engine and voice, type Spanish text, press Play, hear audio from the first chunk, and stop it.

**Independent Test**: With the fake engine, playback starts when the first chunk arrives, before the summary (quickstart rows 1-3, 10-13).

### Tests for User Story 1

- [X] T016 [P] [US1] Write `frontend/tests/session.test.js` (single panel): panel states `connecting` -> `streaming` -> `playing` -> `done`; the first chunk calls the player's `start` before `summary` arrives; Stop sends cancel and the panel becomes `cancelled`; a backend `error` makes the panel `failed` and keeps the message and `available` list; `backend_unreachable` is reported distinctly
- [X] T017 [P] [US1] Write `frontend/tests/e2e-fake-engine.mjs`: start the gateway as a subprocess with the fake engine configured through the existing test variables `TTS_FAKE_FIRST_CHUNK_S`, `TTS_FAKE_CHUNK_INTERVAL_S`, `TTS_FAKE_CHUNKS`, `TTS_FAKE_AUDIO_S` (see `src/tts_bench/backend/worker.py`) so chunk delays are known, open a synthesis with Node's global `WebSocket` and the real `stream.js`, record timestamps, and assert (a) the first chunk is delivered before `summary` (SC-001) and (b) the values the page would display equal the `summary` fields exactly (SC-002); exit non-zero on failure; print the measured "first chunk before summary" gap

### Implementation for User Story 1

- [X] T018 [US1] Implement `frontend/src/player.js`: Web Audio playback (R3); `createPlayer(AudioContextImpl)` with `start(sampleRate)`, `push(float32)` scheduling `AudioBufferSourceNode`s back to back from a ~20 ms lead, `finish()`, `stop()`, an `onEnded` callback, an `underruns` counter, and `state` (`running` or `suspended`); each player uses the engine's own `sample_rate` so different engines play at correct pitch and speed; `resume()` for autoplay-blocked handling (R12)
- [X] T019 [US1] Implement `frontend/src/session.js` for one panel: `EnginePanel` state machine from data-model.md (`waiting`, `connecting`, `streaming`, `playing`, `done`, `failed`, `cancelled`), storing `start`, `chunks[]`, `summary` unmodified, `error`, and browser-side `{sent_at, first_chunk_at, first_audio_scheduled_at, ended_at}`; `run(panel)` drives `stream.js` and `player.js`; `stop()` cancels the request and the player; a `suspended` audio context sets `audio_blocked` without losing stored chunks (depends on T010, T018)
- [X] T019a [US1] Implement `frontend/src/view-model.js` (pure, no DOM) and `frontend/tests/view-model.test.js`: functions that decide what is shown: `engineOptionModel(engine)` (only `name`, `kind`, `cloned`, `accent_label` per voice, any other voice field is dropped; availability, reason/hint, cloning badge, license line and restrictive warning via `license.js`), `limitModel(selectedEngines, textLength)` (limit = smallest `input_limit_chars` among the selected engines, names the engine that sets it, `playDisabled` above it), `busyModel(error)` (for `engine_busy`: `queue_depth` and `canRetry: true`), `panelModel(panel)` (header and metrics fields, filled out further in US2 and US3)
- [X] T020 [US1] Implement `frontend/src/view.js` (US1 part) as a thin DOM mapping of the view model from T019a: render backend-unreachable banner with the start command; engine selector listing every engine with availability (unavailable ones disabled with `reason` and `hint`), cloning badge, license line and the restrictive-license banner from `license.js` (FR-001, FR-008); voice selector per engine showing `name` and `accent_label` only (FR-012, FR-010); text input with a live character counter against the limit from `limitModel` and Play disabled above it (limit shown before sending); on `engine_busy` show the queue depth and a Retry button (`busyModel`); Play and Stop buttons; "Enable audio" button when `audio_blocked`
- [X] T021 [US1] Implement `frontend/src/main.js`: editable Backend URL field (in memory only), load `getEngines`, a Refresh button calling `refreshEngines`, create the audio context inside the Play click handler (R12), wire Play and Stop to `session.js`, show `BackendUnreachable` and `BackendError` messages without failing silently (depends on T009, T019, T020)
- [X] T022 [US1] Add layout and states to `frontend/styles.css` for the selector, input, counter, warning banner, disabled engines and the "Enable audio" button; no external fonts or images
- [X] T023 [US1] Run `node --test frontend/tests/` and `node frontend/tests/e2e-fake-engine.mjs`; then walk quickstart rows 1, 2, 3, 10, 11, 12 and 13 against the fake engine and record deviations in the task notes _Walked manually by the maintainer in the browser 2026-11-04 (offline, 2+ engines, limit, backend down, unavailable engine, autoplay, corpus, replay display); Stop shows cancelled and Replay sends no new request, both confirmed._

**Checkpoint**: A tester can type text, hear it stream from the first chunk, and stop it. MVP complete.

---

## Phase 4: User Story 2 - See latency and speed for each request (Priority: P1)

**Goal**: After each request the panel shows TTFA, total time, audio duration and RTF exactly as the backend reported them, with honest "not available" handling.

**Independent Test**: After a fake-engine request, displayed values equal the `summary` message; with granularity `none`, TTFA shows "not available" with the explanation (quickstart rows 4-5).

### Tests for User Story 2

- [X] T024 [P] [US2] Extend `frontend/tests/format.test.js` with panel-level rendering inputs: a full `summary` (chunk granularity), a `summary` with `ttfa_ms: "not available"` and `start.streaming_available: false`, `load_ms` with `first_request_after_load`, and `queue_wait_ms`; assert every displayed number string equals the source value (SC-002)
- [X] T025 [US2] Extend `frontend/tests/e2e-fake-engine.mjs` with a second run starting the gateway with `TTS_FAKE_GRANULARITY=none`; assert TTFA renders as "not available" with the explanation and granularity `none` is shown

### Implementation for User Story 2

- [X] T026 [US2] Add the metrics block to `frontend/src/view.js`: TTFA (with granularity and its note beside it), total time (`generation_ms`), audio duration (`audio_seconds`), RTF, each rendered through `format.js`; queue wait and load time on separate lines with an "includes model load" tag when `first_request_after_load`; the backend `kind: "interactive"` label and the note "live figures are not benchmark results"; the browser-side "heard after" figure labelled as browser-side and never combined with TTFA (R6); the underrun count
- [X] T027 [US2] Show on the panel header the engine version, model id, voice, accent label, license line and restrictive-license banner taken from the `start` message and the engine listing (Constitution V, FR-008) in `frontend/src/view.js`
- [X] T028 [US2] Style the metrics block and the "not available" explanation in `frontend/styles.css`
- [X] T029 [US2] Run the tests and walk quickstart rows 4 and 5; compare displayed values with the `summary` message in the browser network inspector _Walked manually by the maintainer in the browser 2026-11-04 (offline, 2+ engines, limit, backend down, unavailable engine, autoplay, corpus, replay display); Stop shows cancelled and Replay sends no new request, both confirmed._

**Checkpoint**: Every request shows its numbers; US1 and US2 both work.

---

## Phase 5: User Story 3 - Compare engines side by side with the same text (Priority: P2)

**Goal**: Send one text to several engines, run them one at a time, show one panel per engine, replay without a new request, and pick text from the corpus.

**Independent Test**: One submission produces one panel per selected engine with the same text, engines never overlapping (quickstart rows 6-8).

### Tests for User Story 3

- [X] T030 [P] [US3] Write `tests/backend/test_corpus_endpoint.py`: `GET /v1/corpus` returns `corpus_version`, `count` and sentences with only `id`, `text`, `campaign`, `scenario`, `tags`; `text` equals the sentence's spoken form when `spoken` exists; only the `main` subset appears; `cloning.jsonl` content never appears; a missing or malformed corpus directory returns 503 `corpus_unavailable` with no filesystem path while `/v1/health` still works
- [X] T031 [P] [US3] Extend `frontend/tests/session.test.js` for comparison: with 3 panels the second does not reach `connecting` until the first reaches `done`, and not until its playback has ended; a `failed` panel does not stop later panels; Stop during panel 2 cancels it, leaves panel 3 as `not_run` and keeps panel 1's stored audio; all panels receive the identical text string; Replay on a `done` panel plays stored chunks and sends no new message on any socket
- [X] T032 [P] [US3] Write `frontend/tests/corpus.test.js`: filter by campaign and free text, and activating an entry returns its `text` unchanged

### Implementation for User Story 3

- [X] T033 [US3] Add `GET /v1/corpus` to `src/tts_bench/backend/app.py` per contracts/backend-additions.md: read `corpus/sentences.jsonl` through `tts_bench.corpus.loader`, `main` subset, `Sentence.speak_text` as `text`, version from `read_version`; never read `cloning.jsonl`; on `CorpusError` or missing directory return 503 `corpus_unavailable` without a path (depends on T030)
- [X] T034 [US3] Add `getCorpus(baseUrl)` to `frontend/src/api.js` and `frontend/src/corpus.js` with the filter logic (campaign, free text) used by the picker
- [X] T035 [US3] Extend `frontend/src/session.js` to `ComparisonSession`: ordered panels, strictly sequential run (the next panel starts only after the previous reaches `done`, `failed` or `cancelled` and its playback ended, per clarification 2026-11-04 and plan decision 5), `waiting` and `not_run` states, Stop cancels the running request and marks unstarted panels `not_run`, one shared text for all panels, starting a new session discards the previous one; add `replay(panel)` that rebuilds buffers from stored `chunks` without opening a socket (depends on T019)
- [X] T036 [US3] Extend `frontend/src/view.js` and `frontend/src/main.js`: multi-engine selection (checkbox per engine, voice chosen per panel), one result panel per selected engine in run order with a "waiting" state, per-panel Replay button, a session-level Stop, and a corpus picker (filter box, list, one click copies `text` into the input) (FR-005, FR-006); the counter and Play gating use `limitModel` over all selected engines (smallest limit wins and the engine that sets it is named)
- [X] T037 [US3] Style the side-by-side panel grid, the waiting and not-run states and the corpus picker in `frontend/styles.css`
- [X] T038 [US3] Run all automated checks and walk quickstart rows 6, 7, 8, 9 and 15; confirm in the backend request log that Replay produced no new request _Walked manually by the maintainer in the browser 2026-11-04 (offline, 2+ engines, limit, backend down, unavailable engine, autoplay, corpus, replay display); Stop shows cancelled and Replay sends no new request, both confirmed._

**Checkpoint**: All three user stories work independently and together.

---

## Phase 6: Polish & Cross-Cutting Concerns

- [X] T039 [P] Write `docs/frontend.md`: the SC-003 condition (engines already loaded, sentence of 5 s of audio or less; a cold first request adds its load time), the English interface language, how to run (two commands from quickstart), what each panel shows and where each number comes from, that live numbers are `interactive` and not benchmark results (Constitution III), the sequential comparison rule, the corpus and CORS additions, limits, and that no voice material is exposed
- [X] T040 [P] Add a privacy test `frontend/tests/privacy.test.js`: feed `engineOptionModel` and `panelModel` from `view-model.js` an engine listing containing unexpected extra voice fields (`path`, `sha256`, `consent_id`) and assert none appears anywhere in the resulting models (FR-010, contract assumption 5)
- [X] T041 [P] Verify offline behavior (FR-009): grep `frontend/` for `http://` and `https://` references other than the configurable backend URL default and fail on any CDN or font link; then load the page with the network disabled and confirm engines, playback and corpus work _Walked manually by the maintainer in the browser 2026-11-04 (offline, 2+ engines, limit, backend down, unavailable engine, autoplay, corpus, replay display); Stop shows cancelled and Replay sends no new request, both confirmed._
- [X] T042 Add a short "Frontend" section to `README.md` linking `docs/frontend.md` and the run commands; confirm with a statement that the page is a live-testing aid, not a benchmark
- [X] T043 Run the complete validation: `node --test frontend/tests/`, `node frontend/tests/e2e-fake-engine.mjs`, `python -m pytest tests/backend` (existing 007 tests included) and all 17 rows of quickstart.md; list any failures honestly in the final notes _Walked manually by the maintainer in the browser 2026-11-04 (offline, 2+ engines, limit, backend down, unavailable engine, autoplay, corpus, replay display); Stop shows cancelled and Replay sends no new request, both confirmed._
- [X] T044 Check Constitution Principle VI compliance for the PR description: no voice file, path, hash or recording id appears in the page, its requests or the new endpoint; no cloned voice material was added to the repository

---

## Dependencies & Execution Order

### Phase Dependencies

- **Setup (Phase 1)**: no dependencies.
- **Foundational (Phase 2)**: after Setup; blocks all user stories.
- **US1 (Phase 3)**: after Foundational. MVP.
- **US2 (Phase 4)**: after Foundational; its panel code builds on `view.js` and `session.js` from US1, so run after US1 in practice.
- **US3 (Phase 5)**: after Foundational; `session.js` and `view.js` extensions build on US1. The backend corpus endpoint (T030, T033, T034) is independent and can start any time after Foundational.
- **Polish (Phase 6)**: after the stories you intend to ship.

### Task Dependencies Inside Phases

- T005 depends on T004; T006 can be written in parallel with T005.
- T010 depends on T007; T011 depends on T002 and T010.
- T019 depends on T010 and T018; T021 depends on T009, T019 and T020.
- T035 depends on T019; T033 depends on T030 (test first).

### Parallel Opportunities

- Setup: T002 and T003.
- Foundational: T006, T007, T008, T012-T015 are mutually independent files; T009 and T010 can run alongside them.
- US1: T016 and T017 in parallel; T018 can proceed alongside T016/T017.
- US3: T030, T031 and T032 in parallel; the backend endpoint (T033) in parallel with frontend session work (T035).
- Polish: T039, T040 and T041.

### Parallel Example: Foundational

```text
Task: "Implement frontend/src/pcm.js"          (T007)
Task: "Implement frontend/src/license.js"      (T012)
Task: "Implement frontend/src/format.js"       (T014)
Task: "Write tests/backend/test_cors.py"       (T006)
```

---

## Implementation Strategy

### MVP First (User Story 1)

1. Complete Phase 1 and Phase 2.
2. Complete Phase 3 (US1) and stop to validate with the fake engine: audio starts at the first chunk, Stop cancels.
3. Demo to the maintainer.

### Incremental Delivery

1. Foundation -> US1: live streaming playback.
2. Add US2: numbers and honest "not available" handling.
3. Add US3: sequential comparison, replay and corpus picker.
4. Polish: docs, privacy and offline checks.

## Notes

- Never commit; the maintainer makes all commits.
- Timings shown are copied from the backend `summary`; no metric is recomputed in the page.
- The sequential rule (next engine starts after the previous one's playback ends) is final; a "Skip" button was considered and not adopted.
- Cloned-voice consent is settled by the constitution; do not add consent prompts or questions.

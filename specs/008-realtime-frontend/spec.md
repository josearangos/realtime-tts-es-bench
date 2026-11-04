# Feature Specification: Real-Time Testing Frontend

**Feature Branch**: `008-realtime-frontend`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "A web interface for trying the TTS engines live: type Spanish text, pick engine and voice, hear audio as it streams, see latency in real time, and compare engines side by side."

## Clarifications

### Session 2026-11-04

- Q: When a tester sends one text to several engines, should the engines run one after another or all at once? → A: One after another; each engine runs alone and its panel fills in as it finishes.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Type text and hear it live (Priority: P1)

A tester types Spanish text, picks an engine and voice, and starts hearing speech as soon as the first audio arrives.

**Why this priority**: The core interactive experience that shows real-time behavior.

**Independent Test**: Against the fake backend engine, playback starts when the first chunk arrives, not when synthesis ends.

**Acceptance Scenarios**:

1. **Given** the engine list from the backend, **When** the tester opens the interface, **Then** engines and their voices are selectable.
2. **Given** text and a selected engine, **When** the tester presses play, **Then** audio begins as soon as the first chunk arrives.
3. **Given** playback is in progress, **When** the tester stops it, **Then** playback and synthesis are cancelled.

---

### User Story 2 - See latency and speed for each request (Priority: P1)

A tester wants to see how responsive the engine is, in numbers, right after each request.

**Why this priority**: Makes the real-time characteristics visible without leaving the interface.

**Independent Test**: After a request on the fake engine, displayed values match what the backend reported.

**Acceptance Scenarios**:

1. **Given** a completed request, **When** it finishes, **Then** time to first audio (TTFA), total time, audio duration, and real-time factor (RTF) are displayed.
2. **Given** a non-streaming engine, **When** it is used, **Then** the interface labels TTFA as not available and explains why.

---

### User Story 3 - Compare engines side by side with the same text (Priority: P2)

A tester sends the same text to several engines and compares speed and sound.

**Why this priority**: Direct comparison is the purpose of the project.

**Independent Test**: One submission produces one result panel per selected engine, with the same text.

**Acceptance Scenarios**:

1. **Given** two or more selected engines, **When** the tester submits one text, **Then** the engines run one at a time, never overlapping, and each engine's audio and timing appear in its own panel as that engine finishes.
2. **Given** a panel, **When** the tester replays it, **Then** audio is replayed from the stored result without a new request.
3. **Given** corpus sentences, **When** the tester chooses one, **Then** it can be used as input with a single action.

---

### Edge Cases

- Backend unavailable: a clear message is shown, with no silent failure.
- Browser blocks autoplay: the interface prompts the tester to enable audio.
- Engine unavailable: shown disabled with the reason.
- Very long text: the interface shows the backend's limit before sending; in a comparison the smallest limit among the selected engines applies.
- Engine busy: the interface shows the queue state and offers a retry.
- Different sample rates between engines: playback handles each correctly.
- One engine in a comparison fails: its panel shows the error while the other panels still complete.
- Stop pressed during a comparison: the running request is cancelled and engines not yet started are not run.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The interface MUST list engines and voices from the backend, including availability and cloning support.
- **FR-002**: The interface MUST start playback as soon as the first audio chunk arrives for streaming engines.
- **FR-003**: The interface MUST display TTFA, total time, audio duration, and RTF for each request.
- **FR-004**: The interface MUST label unavailable metrics as "not available" with an explanation, and MUST NOT estimate them.
- **FR-005**: The interface MUST support sending the same text to several engines and showing results side by side. Engines MUST run sequentially, one at a time, so that one engine's load does not affect another's displayed timings. Panels of engines not yet run show a "waiting" state.
- **FR-006**: The interface MUST allow choosing a sentence from the corpus.
- **FR-007**: The interface MUST allow stopping a request, cancelling synthesis.
- **FR-008**: The interface MUST show each engine's license and a prominent non-commercial or copyleft warning when applicable.
- **FR-009**: The interface MUST work against a locally running backend with no external network access.
- **FR-010**: The interface MUST NOT expose reference recordings or derived voice files.
- **FR-011**: The interface MUST show each engine's streaming granularity (audio chunks or sentence-level) next to its TTFA, since it changes what TTFA means.
- **FR-012**: The interface MUST state the accent or variant of each voice where the backend provides it.

### Key Entities

- **Engine Panel**: Selected engine, voice, audio result, and timing.
- **Comparison Session**: One text sent to several engines with their results.
- **Corpus Picker**: Selection of corpus sentences.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With a streaming engine, playback starts before synthesis completes.
- **SC-002**: Displayed timing values equal backend-reported values.
- **SC-003**: With both engines already loaded and a sentence of 5 seconds of audio or less, a tester compares two engines on the same sentence in under one minute, with the engines run sequentially. A first request to an engine that still has to load adds that engine's load time, which is shown separately.
- **SC-004**: Every engine with a restrictive license shows a visible warning.

## Assumptions

- Testers are project members using the interface on the same machine (or local network) as the backend; no user accounts or authentication are needed.
- The interface is a live-testing aid only. Rigorous benchmark figures come from the deterministic metric scripts; timings shown here include browser and local-transport effects and are not substituted for them.
- The interface text (labels, messages, explanations) is in English; the text being synthesized and the corpus stay in Spanish.
- This feature depends on two small additions to the 007 backend: a read-only corpus list and browser access for the local frontend origin (see the plan).
- Timing values shown are those reported by the real-time backend (007); the interface does not recompute or estimate them.
- Engine list, voices, licenses, streaming granularity, text-length limit, and corpus sentences are all supplied by the backend; the interface hard-codes none of them.
- Results stored for replay live only for the current session; persisting history across sessions is out of scope.
- Voice cloning from newly uploaded recordings is out of scope; only voices already in the voice library are selectable. Consent for those voices is settled per the constitution.
- Human evaluation (blind rating) is out of scope; it belongs to separate tooling.

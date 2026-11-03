# Feature Specification: Real-Time Synthesis Backend

**Feature Branch**: `007-realtime-backend`
**Created**: 2026-10-29
**Status**: Draft
**Input**: User description: "A backend service that exposes the TTS engines for live testing: choose engine and voice, send text, and receive audio streamed as it is generated, with latency measured server-side."

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Stream synthesized audio from any engine (Priority: P1)

A tester sends Spanish text and an engine choice and starts receiving audio before synthesis finishes, when the engine supports it.

**Why this priority**: This is the foundation for interactive real-time testing.

**Independent Test**: With the fake engine, a request returns audio chunks incrementally; the first chunk arrives before the last is produced.

**Acceptance Scenarios**:

1. **Given** a streaming engine, **When** a request is made, **Then** audio is delivered incrementally as chunks are produced.
2. **Given** a non-streaming engine, **When** a request is made, **Then** complete audio is returned and the response states that streaming is not available.
3. **Given** an unknown engine or voice, **When** a request is made, **Then** a clear error lists the available options.

---

### User Story 2 - Report latency with every response (Priority: P1)

A tester wants to see how long each request took without running a separate benchmark.

**Why this priority**: Interactive tests are only meaningful if the system reports what it measured.

**Independent Test**: With the fake engine of known delay, reported latency matches within tolerance.

**Acceptance Scenarios**:

1. **Given** a completed request, **When** the response finishes, **Then** it includes TTFA, total generation time, audio duration, and RTF measured server-side.
2. **Given** the same metric definitions as the offline scripts, **When** both measure the same engine, **Then** the definitions match.
3. **Given** an engine that is loaded on first use, **When** the first request is made, **Then** load time is reported separately from synthesis time.

---

### User Story 3 - Discover engines, voices, and their properties (Priority: P2)

A client wants to list available engines, their voices, streaming capability, license, and whether they clone voices.

**Why this priority**: Lets the frontend and other clients adapt without hardcoding.

**Independent Test**: The listing returns the descriptor fields for each registered engine.

**Acceptance Scenarios**:

1. **Given** registered engines, **When** the listing is requested, **Then** each includes name, version, license, voices, streaming granularity, and cloning support.
2. **Given** an engine whose dependencies are missing, **When** the listing is requested, **Then** it is shown as unavailable with the reason.

---

### Edge Cases

- Concurrent requests to a single-instance engine: handled predictably (queued or rejected with a clear message) and recorded.
- Client disconnects mid-stream: synthesis is cancelled and resources released.
- Very long input: rejected or split with a clear limit message.
- Engines loaded lazily: first-request delay is reported as load time, separate from synthesis.
- Voices derived from a consented reference are never exposed for download.
- Empty or whitespace-only text: rejected with a clear message.
- Request for an engine listed as unavailable: rejected with the unavailability reason, not a generic failure.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The backend MUST expose synthesis for every registered engine through one interface.
- **FR-002**: The backend MUST stream audio incrementally for engines that support it.
- **FR-003**: The backend MUST accept engine, voice, and Spanish text as input.
- **FR-004**: The backend MUST return TTFA, total time, audio duration, and RTF with each response, using the same definitions as the offline metrics.
- **FR-005**: The backend MUST list engines, voices, streaming granularity, cloning support, and licenses.
- **FR-006**: The backend MUST report unavailable engines with the reason.
- **FR-007**: The backend MUST cancel synthesis on client disconnect.
- **FR-008**: The backend MUST enforce a documented input length limit.
- **FR-009**: The backend MUST run locally and offline after setup.
- **FR-010**: The backend MUST NOT expose reference recordings or derived voice files.
- **FR-011**: The backend MUST be testable with the fake engine and no model weights.
- **FR-012**: For non-streaming engines, the backend MUST return complete audio and state explicitly that streaming is not available; metrics that depend on streaming (such as TTFA) MUST be reported as "not available", never estimated.
- **FR-013**: The backend MUST report model load time separately from synthesis time.
- **FR-014**: When a request names an unknown or unavailable engine or voice, or invalid input, the backend MUST return an error that lists the valid options or the reason.
- **FR-015**: The backend MUST handle concurrent requests to a single-instance engine in a documented, predictable way (queue or reject with a clear message) and record the outcome.

### Key Entities

- **Synthesis Request**: Engine, voice, text, and options.
- **Audio Stream**: Chunks with timestamps and the final timing summary.
- **Engine Listing**: Descriptor fields and availability.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With a streaming engine, the first audio chunk is delivered before synthesis completes.
- **SC-002**: Server-reported latency on the fake engine matches the configured delay within 5%.
- **SC-003**: All registered engines appear in the listing with complete descriptor fields.
- **SC-004**: The service starts and serves requests with no network access once cached.
- **SC-005**: After a client disconnects mid-stream, synthesis for that request stops and the engine is free for the next request within a bounded, documented time.
- **SC-006**: The full behavior of this feature can be verified by an automated test run that uses only the fake engine and downloads no model weights.

## Assumptions

- Users are the project's own testers and a companion frontend, running on one local machine; no authentication, multi-tenancy, or remote exposure is in scope.
- "Registered engines" are the engine adapters defined in feature 001; the fake engine is the one already provided there for tests.
- Latency metric definitions (TTFA, total time, audio duration, RTF) are those of feature 004, reused rather than redefined.
- Voices and cloned-voice consent rules come from feature 003; only voice identifiers and descriptive metadata are exposed, never audio files.
- One engine per process remains the rule for benchmark results (constitution III); live-testing numbers from this backend are interactive indications, not benchmark results, and are labeled as such.
- The input length limit has a documented default chosen during planning, suited to conversational utterances.
- Input text is Spanish; no language detection or translation is performed.
- The frontend itself is out of scope.

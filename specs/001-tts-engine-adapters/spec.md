# Feature Specification: TTS Engine Adapters

**Feature Branch**: `001-tts-engine-adapters`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Provide a common interface to run Phonon (baseline), Pocket TTS, and Piper in Spanish, exposing streaming capability, so metrics, backend, and frontend treat every engine the same way."

## Clarifications

### Session 2026-10-29

- Q: Which Spanish variant should the voices of all three engines target? → A: Colombian Spanish for every engine, using a cloned reference voice where an engine has no native Colombian voice.
- Q: What should an adapter return when an engine fails partway through synthesis? → A: The run is reported as failed with a clear error and excluded from latency statistics; partial audio kept only for diagnosis.
- Q: Should each engine run in its own process? → A: Yes; only one engine may be loaded per process, and loading a second is refused.
- Q: For sentence-level streaming engines, what does time to first audio mean? → A: The moment the first playable audio is produced, whatever the granularity, always reported together with the engine's declared granularity.
- Q: Which text inputs must every adapter handle? → A: Plain Spanish text passed through unchanged; each engine's input limits are declared in its descriptor, and exceeding them is a reported failure.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Run all three engines through one interface (Priority: P1)

A developer selects an engine by name and gets Spanish audio and its sample rate, without dealing with each engine's own API.

**Why this priority**: Every other feature depends on a uniform way to call the engines (Constitution Principles III and VII).

**Independent Test**: For each engine, synthesize one short Spanish sentence and receive playable audio with a recorded sample rate.

**Acceptance Scenarios**:

1. **Given** Phonon with the Spanish model is installed, **When** it is selected, **Then** Spanish audio is produced with the configured voice.
2. **Given** Pocket TTS is installed, **When** it is selected with a reference voice, **Then** Spanish audio is produced in the cloned voice.
3. **Given** Piper is installed with a Spanish voice, **When** it is selected, **Then** Spanish audio is produced with that fixed voice.

---

### User Story 2 - Declare streaming capability and granularity honestly (Priority: P1)

A developer needs to know, per engine, whether audio arrives incrementally and at what granularity, because it determines how time to first audio is measured.

**Why this priority**: TTFA is the key real-time metric; faking it would violate honest reporting.

**Independent Test**: A fake engine with chunk streaming reports chunk granularity; a fake engine returning only complete audio reports "not available".

**Acceptance Scenarios**:

1. **Given** an engine emits audio chunks, **When** it is queried, **Then** it reports chunk-level streaming and exposes each chunk as it is produced.
2. **Given** an engine synthesizes per sentence or fragment, **When** it is queried, **Then** it reports sentence-level granularity.
3. **Given** an engine returns only complete audio, **When** it is queried, **Then** it reports no streaming.

---

### User Story 3 - Add another engine with minimal code (Priority: P2)

A contributor adds a new Spanish-capable engine by writing one small adapter.

**Why this priority**: Keeps the benchmark useful as new engines appear without growing complex.

**Independent Test**: Register an adapter for the fake engine and run it with no other changes.

**Acceptance Scenarios**:

1. **Given** a new adapter implementing the interface, **When** it is registered by name, **Then** it can be used by metrics, backend, and frontend unchanged.
2. **Given** an engine's dependencies or weights are missing, **When** it is selected, **Then** a clear message says what to install or download.

---

### Edge Cases

- A voice parameter means different things per engine (stored voice file, reference audio, fixed voice name): each adapter documents it.
- Engines return different sample rates: the rate is returned with the audio and never converted silently.
- Engine dependencies conflict: each adapter is installable and runnable in isolation.
- A second engine is requested in a process that already has one loaded: the request is refused with a clear message.
- An engine has no native Colombian voice and cannot clone (for example, a fixed-voice engine): the adapter's descriptor states the closest accent used, and results for it are labeled accordingly rather than presented as Colombian.
- An engine fails partway through synthesis: the run is reported as failed with a clear error and excluded from latency statistics; any partial audio is kept only for diagnosis.
- Weights are gated or non-commercially licensed: the adapter's descriptor states how to obtain them and the license.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST define a common adapter interface: load the engine, synthesize text to audio with its sample rate, and report streaming capability and granularity.
- **FR-002**: The system MUST include adapters for Phonon (Spanish), Pocket TTS (Spanish), and Piper (Spanish).
- **FR-003**: Adapters MUST target Colombian Spanish and document the voice they use and how its Colombian accent is obtained (native voice or cloned reference voice).
- **FR-004**: Streaming adapters MUST expose audio incrementally with the moment each chunk is produced.
- **FR-005**: Non-streaming adapters MUST report that time to first audio is not available.
- **FR-006**: Adapters MUST NOT alter or resample audio silently.
- **FR-007**: Each adapter MUST carry a descriptor with engine name, version, model identifier, license, voice type, and cloning support.
- **FR-008**: Missing dependencies or weights MUST produce an actionable message.
- **FR-009**: Adapters MUST be installable independently of one another.
- **FR-010**: The system MUST include a fake engine with configurable delay and audio length for testing without weights.
- **FR-011**: Adapters MUST obtain voices by name from the local voice library defined in the voice preparation feature (003), instead of hardcoded file paths.
- **FR-012**: A failure during synthesis MUST be reported as a failed run with a clear error, never as a successful result, and MUST be excluded from latency statistics.
- **FR-013**: The system MUST allow only one engine to be loaded per process and MUST refuse to load a second engine in the same process, so resource measurements are not contaminated.
- **FR-014**: For streaming adapters, time to first audio is the moment the first playable audio is produced at the engine's declared granularity (chunk or sentence), and MUST always be reported together with that granularity.
- **FR-015**: Adapters MUST pass input text to the engine unchanged (no rewriting or normalization), and each descriptor MUST declare the engine's input limits (such as maximum text length); exceeding a limit MUST be reported as a failed run.

### Key Entities

- **Engine Adapter**: Thin wrapper exposing the common interface for one engine.
- **Engine Descriptor**: Metadata including version, license, languages, cloning support, and input limits.
- **Voice Reference**: The engine-specific voice input (file, audio, or name).

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: All three engines produce playable Spanish audio through the interface.
- **SC-002**: Adding a fourth engine requires only a new adapter and one registration.
- **SC-003**: For every engine, streaming capability and granularity are declared, never inferred.
- **SC-004**: The fake engine lets all measurement code be tested with no model downloaded.

## Assumptions

- Phonon is the baseline engine; Pocket TTS and Piper are compared against it.
- Model weights and voices are obtained by users from official sources and are never redistributed by this repository (Constitution Principle VI).
- Colombian voice assets are provided locally by the project owner in `cloned_voices/` (a Phonon stored voice file and two Colombian Spanish reference recordings for Pocket TTS) and are never committed. The project owner has confirmed these voices are authorized for use (consent, Constitution Principle VI); Piper uses a Latin American voice.
- The voice library from feature 003 provides voices by name; until it exists, the fake engine can be exercised without it.
- Streaming capability and granularity are declared by each adapter's author based on the engine's documented behavior, not detected at runtime.
- Consumers (metrics, backend, frontend) are out of scope here; this feature only provides the interface they consume.

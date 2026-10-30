# Feature Specification: Real-Time Performance Metrics

**Feature Branch**: `004-realtime-performance-metrics`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Scripts that measure, for each engine and the same Spanish corpus, time to first audio (p50/p95), real-time factor, throughput, load time, and resource use (RAM, CPU, VRAM when applicable), in cold and warm conditions."

## Clarifications

### Session 2026-10-30

- Q: How should throughput be defined? → A: Audio seconds produced per wall-clock second, per repetition excluding warm-up, summarized as the median over repetitions (the inverse of overall RTF).
- Q: What counts as "different hardware" for refusing to merge results? → A: Any difference in CPU model, core count, RAM size, GPU model, or OS name and major version.
- Q: What is the TTFA end instant for a streaming engine? → A: The first non-empty audio chunk delivered, measured from the synthesis request; leading silence is kept in the raw data.
- Q: Should a run stop after repeated failures? → A: No, always finish the corpus; flag the summary as unreliable when more than 10% of sentences fail or are invalid.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Measure latency and speed for one engine (Priority: P1)

A developer runs one script for one engine and receives per-sentence and summary values for time to first audio (TTFA), real-time factor (RTF), and throughput.

**Why this priority**: These are the central real-time metrics (Constitution Principle I).

**Independent Test**: Using the fake engine with known delay and audio length, reported TTFA, RTF, and throughput match the known values within tolerance.

**Acceptance Scenarios**:

1. **Given** an engine and the corpus, **When** the script runs, **Then** it reports for each sentence audio duration, generation time, RTF, and TTFA (or "not available").
2. **Given** several repetitions, **When** results are summarized, **Then** TTFA and RTF are reported as median (p50) and 95th percentile (p95).
3. **Given** a streaming engine, **When** it runs, **Then** per-chunk latency is also recorded in addition to global RTF.

---

### User Story 2 - Separate cold, warm, and load time (Priority: P1)

A developer wants to know how long the engine takes to start and how it behaves after warming up.

**Why this priority**: Conversational systems feel both the first-request delay and the steady-state speed.

**Independent Test**: Run cold and warm modes on the fake engine with a known load delay; load time and first-request penalty are reported separately.

**Acceptance Scenarios**:

1. **Given** a fresh process, **When** the cold run executes, **Then** model load time and first-request time are reported separately from steady-state results.
2. **Given** a warm-up has completed, **When** the warm run executes, **Then** warm-up requests are excluded from the figures.

---

### User Story 3 - Record resource use and environment (Priority: P2)

A developer wants to know what hardware an engine needs and under what conditions the numbers were obtained.

**Why this priority**: Results are only comparable on documented, identical hardware.

**Independent Test**: A results file contains peak RAM, CPU use, and the full environment metadata.

**Acceptance Scenarios**:

1. **Given** a run, **When** it completes, **Then** peak RAM, CPU utilization, and (if a GPU is used) peak VRAM are recorded.
2. **Given** a results file, **When** it is opened, **Then** it includes CPU, RAM, OS, thread settings, library and model versions, corpus version, and the exact command.
3. **Given** results from different hardware, **When** a comparison is requested, **Then** the system refuses to merge them into one table without an explicit override.

---

### Edge Cases

- Engines without streaming: TTFA is "not available"; sentence-level engines record granularity so TTFA is interpreted correctly.
- A sentence fails: the failure is recorded and the run continues.
- Memory measurement differs by operating system: the method and unit are recorded.
- Background load is detected above a threshold: a warning is stored in the results.
- Empty audio output: flagged invalid, never counted as infinitely fast.
- Results from a remote engine: each results file records its locality (local or remote), and local and remote results are never merged in one comparison (Constitution Principle III). Measuring network time is out of scope for this feature.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST run one engine per process.
- **FR-002**: The system MUST measure TTFA, RTF, and throughput per sentence and per repetition, with each metric's start and end instants documented. Throughput is audio seconds produced per wall-clock second within one repetition (first measured request start to last measured request finish, warm-up excluded); the run value is the median over repetitions. TTFA runs from the synthesis request to delivery of the first non-empty audio chunk.
- **FR-003**: The system MUST report p50 and p95 for TTFA and RTF.
- **FR-004**: The system MUST report model load time separately from synthesis time.
- **FR-005**: The system MUST support cold and warm modes and exclude warm-up from measured figures.
- **FR-006**: The system MUST record peak RAM and CPU use, and peak VRAM when a GPU is used.
- **FR-007**: The system MUST store raw per-sentence measurements and environment metadata in a machine-readable file. Environment metadata comprises CPU, RAM, OS, thread settings, library and model versions, corpus version, and the exact command.
- **FR-008**: The system MUST record the streaming granularity of the engine.
- **FR-009**: The system MUST refuse to combine results from different hardware without an explicit override. Hardware differs when CPU model, core count, RAM size, GPU model, or OS name and major version differ; other environment differences (library versions, thread settings) are shown but do not trigger refusal.
- **FR-010**: Metric computation MUST be testable with the fake engine and no model weights.
- **FR-011**: The system MUST report a metric as "not available" when an engine cannot support it, and MUST NOT estimate it.
- **FR-012**: The system MUST record per-chunk latency for streaming engines in addition to per-sentence figures.
- **FR-013**: The system MUST record failed sentences and flag empty audio output as invalid, excluding both from summary statistics while keeping them in the raw data. The run always continues through the whole corpus, and the Run Summary MUST be flagged unreliable when more than 10% of sentences fail or are invalid.
- **FR-014**: The system MUST record the memory-measurement method and unit, and store a warning when background load exceeds a threshold.
- **FR-015**: The system MUST use the same corpus, in the same order, for every engine.

### Key Entities

- **Measurement**: Raw figures for one sentence in one repetition (audio duration, generation time, TTFA, RTF, chunk latencies, status).
- **Run Summary**: p50, p95, and means derived from measurements, for one engine, one mode (cold or warm), and one machine.
- **Environment Record**: Hardware, OS, versions, configuration, and command.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: With the fake engine, reported TTFA, RTF, and throughput match known values within 5%.
- **SC-002**: Repeating a warm run on the same machine yields a median RTF within 10% of the first run.
- **SC-003**: 100% of results files include every environment field listed in FR-007.
- **SC-004**: A benchmark runs with no network access after dependencies and weights are cached.
- **SC-005**: 100% of attempts to merge results from different hardware are refused unless the override is given.

## Assumptions

- The Spanish corpus comes from feature 002 and engines are accessed through the adapters from feature 001; this feature adds no engine-specific logic.
- Cloning-capable engines use voices from the voice library of feature 003.
- The number of repetitions, warm-up requests, and the background-load threshold are configurable, with documented defaults.
- Comparison of results is limited to a single machine configuration; cross-hardware merging requires an explicit override.
- Quality metrics (WER/CER, speaker similarity) and human evaluation are out of scope.
- A "cold" run is the first run in a freshly started process after model files are already cached on disk.
- Default settings are 5 repetitions, 3 warm-up requests, and a background-load threshold of 0.25 (load average per logical core); all are configurable.
- The main corpus subset is measured by default; the cloning subset can be selected explicitly.
- Remote engines are out of scope for this feature; results only reserve a locality field so local and remote results are never mixed.
- Background load is checked with the system load average, which lags by about a minute, so the warning is indicative only.
- On machines with unified memory (Apple Silicon), GPU memory is part of RAM; VRAM is reported as "not available" with a note.

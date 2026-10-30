# Feature Specification: Voice Preparation and Consent

**Feature Branch**: `003-voice-preparation-consent`

**Created**: 2026-10-29

**Status**: Implemented

**Input**: User description: "Prepare voices for cloning-capable engines (Phonon, Pocket TTS) from the same Spanish reference recording, assign a fixed voice to Piper, register prepared voice files (for example Phonon voice files) in a local voice library resolved by name, enforce speaker consent, and keep voice material out of the repository."

## Clarifications

### Session 2026-10-29

- Q: When a voice is removed, should removal also delete generated audio and flag existing results? → A: Yes. Delete generated audio made with that voice and mark result files that used it as "voice withdrawn", keeping the numbers.
- Q: What happens when a voice is requested for a use or content kind its consent record doesn't permit? → A: The library refuses to resolve the voice and explains why.
- Q: What is the minimum reference length below which a "too short" warning is raised? → A: 10 seconds of speech.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One reference recording for every cloning-capable engine (Priority: P1)

A developer has a clean Spanish recording from a consenting speaker and wants Phonon and Pocket TTS to use that exact recording so output differences come from the engines.

**Why this priority**: Fair comparison of naturalness and speaker similarity requires identical voice input (Constitution Principle III).

**Independent Test**: Provide one reference recording and confirm each cloning-capable engine's voice is derived from it, with the source recorded.

**Acceptance Scenarios**:

1. **Given** a reference recording and a consent record, **When** voices are prepared, **Then** an engine-specific voice is produced for each cloning-capable engine from that recording.
2. **Given** an engine needs an external or manual step to create its voice, **When** preparation runs, **Then** the required step is documented and the resulting file is registered with the same source recording.
3. **Given** Piper does not clone, **When** preparation runs, **Then** a documented fixed Spanish voice is assigned and recorded.

---

### User Story 2 - Register existing voice files in a local voice library (Priority: P1)

An engineer who already has a prepared voice file (for example a Phonon voice file created from a reference recording) wants to register it once and then use it by name in every feature, without touching engine-specific code.

**Why this priority**: Prepared voice files are the input cloning-capable engines need; without a registry, each script hardcodes paths and loses the link to consent and source.

**Independent Test**: Register a sample voice file for the fake engine, then resolve it by name and obtain its location, engine, and metadata.

**Acceptance Scenarios**:

1. **Given** a prepared voice file and its consent record, **When** it is registered with a name, **Then** the library stores the name, engine, file location, checksum, source recording reference, and consent reference.
2. **Given** a registered voice name, **When** an adapter, the backend, or a script requests it, **Then** the library resolves it to the engine-specific file or reference without exposing the file to clients.
3. **Given** a voice file registered for one engine, **When** it is requested for another engine, **Then** the request is refused with an explanation.
4. **Given** a registered file is modified or missing, **When** it is resolved, **Then** the checksum mismatch or missing file is reported.

---

### User Story 3 - Block cloning without consent (Priority: P1)

A maintainer wants assurance that no voice is cloned without the speaker's explicit permission.

**Why this priority**: Required by Constitution Principle VI (non-negotiable).

**Independent Test**: Attempt preparation without a consent record; it refuses and explains why.

**Acceptance Scenarios**:

1. **Given** a recording with no consent record, **When** preparation is requested, **Then** it stops and states that consent is required.
2. **Given** a consent record, **When** preparation runs, **Then** the record is stored with the voice metadata.

---

### User Story 4 - Keep voice material out of version control (Priority: P2)

A maintainer wants to publish the repository without leaking anyone's voice.

**Why this priority**: Protects speakers and keeps the project compliant.

**Independent Test**: Stage changes with voice files present; reference audio and derived voices are excluded.

**Acceptance Scenarios**:

1. **Given** voice files in the working directory, **When** changes are staged, **Then** reference audio and derived voices are excluded by default.
2. **Given** an attempt to commit a recording, **When** repository checks run, **Then** it is flagged.

---

### Edge Cases

- Recording too short, noisy, or with music: a warning is recorded.
- Accent differs from the engine's primary Spanish variant: the mismatch is noted.
- Different engines use different reference lengths: the exact segment used per engine is recorded.
- Consent withdrawn: the voice and all derived files (including generated audio) are removed, existing results that used it are marked "voice withdrawn", and it is excluded from new reports.
- Voice files are engine-specific and never reused across engines.
- A voice name is registered twice: the second registration is refused unless the first is removed.
- The library index is deleted or corrupted: voices are reported as unregistered; no voice is silently substituted.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST require a consent record before preparing any cloned voice.
- **FR-002**: A consent record MUST include speaker alias, date, permitted uses, and the kinds of test content the speaker allows.
- **FR-003**: The Phonon voice and the Pocket TTS voice used for cross-engine comparison MUST be derived from the same reference recording (speaker `valentina`; library names `valentina-phonon` and `valentina-pocket`). Pocket TTS MAY also have a voice from a second recording (speaker `emiliano`, library name `emiliano-pocket`); that voice is Pocket-only and is not part of cross-engine comparisons.
- **FR-004**: The system MUST document per engine how the voice is created, including any external service or manual step.
- **FR-005**: The system MUST record the reference segment (start and length) used per engine.
- **FR-006**: The system MUST warn when the recording contains less than 10 seconds of speech or is noisy.
- **FR-007**: Reference audio and derived voice files MUST be excluded from version control by default.
- **FR-008**: Voice metadata (source, engine, date, consent reference) MUST be stored with each prepared voice.
- **FR-009**: The system MUST support removing a voice and all derived files, meaning the prepared voice files, its metadata, its library entry, and all generated audio made with that voice. Result files that used the voice MUST be marked "voice withdrawn" while keeping their measurements.
- **FR-010**: Piper MUST be configured with a documented fixed Spanish voice and MUST NOT be penalized for lacking cloning.
- **FR-011**: The system MUST provide a local voice library that registers prepared voice files by name with engine, file location, checksum, source recording reference, and consent reference.
- **FR-012**: The system MUST resolve registered voices by name for adapters, the backend, and scripts, so no feature hardcodes voice file paths.
- **FR-013**: The system MUST refuse to use a voice file with an engine other than the one it was prepared for.
- **FR-014**: The system MUST detect missing or modified voice files through their checksum.
- **FR-015**: Voice files and consent records MUST stay outside tracked files; any committed library index MUST contain only non-sensitive fields.
- **FR-016**: When a caller declares a use or test-content kind that the voice's consent record does not permit, the library MUST refuse to resolve the voice and explain which permission is missing.

### Key Entities

- **Reference Recording**: Clean Spanish speech from a consenting speaker.
- **Consent Record**: Permission with alias, date, and permitted uses.
- **Prepared Voice**: Engine-specific voice input with metadata.
- **Voice Library**: Local registry that maps voice names to prepared voice files and their metadata.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: 100% of cloned voices have a linked consent record (fixed voices such as Piper's are not cloned and need none).
- **SC-002**: In every cross-engine comparison in a report, Phonon and Pocket TTS used voices from the same recording.
- **SC-003**: No reference audio or derived voice appears in repository history.
- **SC-004**: A voice and its derived files can be removed with one documented action.
- **SC-005**: Any registered voice can be used by name in the metrics, backend, and frontend, with no hardcoded path anywhere.

## Assumptions

- The speaker alias is a pseudonym; no real names or contact details are stored (Constitution Principle VI).
- Phonon and Pocket TTS are the only cloning-capable engines in scope; the fake engine is used for testing the library without model weights.
- Voices in scope: speaker `valentina` for Phonon and Pocket TTS, speaker `emiliano` for Pocket TTS only; Piper two fixed voices (`es_MX-claude-high`, `es_AR-daniela-high`). Library names are unique across engines, so the registered names are `valentina-phonon`, `valentina-pocket` and `emiliano-pocket`; Piper voices keep their voice id.
- The owner granted consent for both speakers (2025) for all permitted uses and all test-content kinds; the consent date is recorded as the year `2025` because no full date is available.
- The Phonon voice file is created in the hosted Gradium studio (studio.gradium.ai) by cloning the voice and downloading the `.safetensors` file; the reference audio therefore leaves the machine for that step, which the consent covers.
- Some engines (for example Phonon) may require an external or manual step to create the voice file; this feature registers the result rather than automating the external service.
- Voice material lives in a local, git-ignored location; only non-sensitive index fields (voice name, engine, checksum) may be committed.
- Callers (scripts, metrics, backend, frontend) resolve voices by name through the library and pass the result to the existing adapters (feature 001), which do not change; the smoke tool switches to the library.

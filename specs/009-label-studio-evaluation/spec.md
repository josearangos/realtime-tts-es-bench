# Feature Specification: Label Studio Human Evaluation (Containerized)

**Feature Branch**: `009-label-studio-evaluation`
**Created**: 2026-10-29
**Status**: Draft
**Input**: User description: "Everything needed to run blind human evaluation of Spanish call center TTS in Label Studio, delivered as code in this repository: a containerized Label Studio environment (image definition and orchestration) with projects provisioned automatically, MOS for naturalness, pronunciation, and prosody, CMOS pairwise comparison, speaker similarity, randomized and anonymized audio, quality controls, and export."

## Clarifications

### Session 2026-11-04

- Q: ¿Las tres dimensiones del MOS se califican juntas en un solo proyecto o en proyectos separados? → A: Un solo proyecto MOS con tres calificaciones (1–5) sobre el mismo audio; el posible efecto halo se documenta en el reporte.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Launch the whole evaluation environment with one command (Priority: P1)

An organizer clones the repository and starts a ready-to-use Label Studio from a container, without installing Label Studio on the host or configuring anything in its interface.

**Why this priority**: Without a reproducible environment, no human evaluation can be run or repeated; the user wants everything centralized in this repository.

**Independent Test**: On a machine with only the container runtime installed, a fresh clone reaches a working Label Studio with provisioned projects using the documented commands.

**Acceptance Scenarios**:

1. **Given** a fresh clone and the container runtime, **When** the organizer runs the documented start command, **Then** Label Studio is reachable locally and the evaluation projects are already created.
2. **Given** the environment is running, **When** it is stopped and started again, **Then** projects, tasks, and annotations are preserved.
3. **Given** the organizer wants a clean start, **When** the documented reset command runs and is confirmed, **Then** all evaluation data is removed and the environment returns to its initial provisioned state.
4. **Given** the container image has been built or pulled once, **When** the environment starts without network access, **Then** it still works.

---

### User Story 2 - Create evaluation projects automatically (Priority: P1)

An organizer runs a script that creates the projects, labeling interfaces, and tasks from the synthesized audio, so no manual configuration is needed.

**Why this priority**: Makes human evaluation reproducible and quick to launch.

**Independent Test**: With sample audio for two engines, the provisioning creates the projects and tasks; counts match expectations.

**Acceptance Scenarios**:

1. **Given** synthesized audio from several engines, **When** provisioning runs, **Then** it creates a MOS project (three ratings per audio: naturalness, pronunciation, prosody), a CMOS project (pairwise), and a speaker similarity project (cloning subset).
2. **Given** a project, **When** an annotator opens a task, **Then** the instructions, audio, rating scale, and question are shown in Spanish.
3. **Given** provisioning runs twice, **When** it completes, **Then** no duplicate projects or tasks exist.
4. **Given** the environment starts, **When** provisioning is enabled, **Then** it runs automatically after Label Studio is healthy.

---

### User Story 3 - Keep the evaluation blind and randomized (Priority: P1)

An organizer wants annotators to judge sound only, without knowing which engine produced each audio.

**Why this priority**: Required by Constitution Principle IV for credible human results.

**Independent Test**: Inspect task data visible to annotators: no engine name or identifying filename; order is randomized.

**Acceptance Scenarios**:

1. **Given** generated tasks, **When** they are inspected from the annotator's view, **Then** audio is identified only by an opaque identifier.
2. **Given** pairwise tasks, **When** they are created, **Then** the position of each engine (A or B) is randomized and recorded privately.
3. **Given** the private mapping, **When** results are exported, **Then** each rating traces back to its engine, voice, sentence, and corpus version.

---

### User Story 4 - Control annotation quality (Priority: P2)

An organizer wants confidence that annotators are consistent and attentive.

**Why this priority**: Protects the validity of the MOS and CMOS results.

**Independent Test**: Repeated and attention-check items appear in each batch and are flagged in the export.

**Acceptance Scenarios**:

1. **Given** a batch of tasks, **When** it is created, **Then** it includes repeated items and attention checks, marked privately.
2. **Given** exported annotations, **When** quality is reviewed, **Then** per-annotator consistency and failed checks are reported.
3. **Given** a rating scale, **When** a project is created, **Then** the scale definition and anchor descriptions were fixed before annotation began.

---

### User Story 5 - Back up, restore, and export annotation data (Priority: P2)

An organizer wants to protect annotation work and hand results to the report feature.

**Why this priority**: Human annotation is costly and cannot be regenerated automatically.

**Independent Test**: Back up, reset, restore, and confirm annotations are identical.

**Acceptance Scenarios**:

1. **Given** a running environment, **When** the backup command runs, **Then** a restorable archive of annotation data is produced outside the repository's tracked files.
2. **Given** a backup, **When** the restore command runs on a clean environment, **Then** projects and annotations are identical to the original.
3. **Given** completed annotations, **When** the export command runs, **Then** it writes the files that the results report feature consumes.

---

### Edge Cases

- The default port is already in use: the start command reports it and allows configuring another port.
- The container runtime is not installed or not running: a clear message explains what is missing.
- First start is slow because the image must be built or pulled: progress is shown and the readiness check waits.
- Volume permissions differ across operating systems: setup documents and handles them, or fails with an actionable message.
- Remote annotators need access: the environment listens only on the local machine by default; exposing it to a network is an explicit, documented option with a security warning.
- Upgrading the pinned Label Studio version: existing data is preserved or the upgrade refuses with an explanation.
- Reset requested by mistake: requires explicit confirmation.
- Annotator data stores only a pseudonymous id; audio of cloned voices is removable if consent is withdrawn.
- Audio loudness differs between engines: consistent normalization is applied or its effect is documented.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The repository MUST contain the container image definition and orchestration file needed to run Label Studio, with the Label Studio version pinned.
- **FR-002**: The system MUST provide documented one-command actions to start, stop, reset, back up, restore, and export.
- **FR-003**: Annotation database and media MUST persist in volumes that survive restarts and image rebuilds.
- **FR-004**: The environment MUST provision the evaluation projects automatically on startup, idempotently.
- **FR-005**: The system MUST create three projects: one MOS project in which each audio receives three ratings (naturalness, pronunciation, prosody), one pairwise CMOS project, and one speaker similarity project.
- **FR-006**: Labeling interfaces and instructions MUST be in Spanish, with rating scales and anchors fixed before collection.
- **FR-007**: The system MUST generate tasks from synthesized audio and the corpus, with opaque audio identifiers, and MUST serve audio from a mounted location without exposing engine names.
- **FR-008**: The system MUST randomize task order and the A/B position in pairwise tasks, storing the mapping privately.
- **FR-009**: The system MUST include repeated items and attention checks in each batch.
- **FR-010**: The system MUST apply consistent loudness treatment or document its effect.
- **FR-011**: Administrator credentials and tokens MUST come from environment configuration; an example configuration file MAY be committed but real secrets MUST NOT.
- **FR-012**: The environment MUST listen only on the local machine by default; network exposure MUST require explicit configuration.
- **FR-013**: The environment MUST include a health check and provisioning MUST wait until Label Studio is ready.
- **FR-014**: The environment MUST work without network access once the image is available.
- **FR-015**: The export action MUST produce annotations with the private mapping to engine, voice, sentence, and corpus version, in the format consumed by the results report.
- **FR-016**: The system MUST store only pseudonymous annotator identifiers and MUST NOT include reference recordings or personal voice data in public exports.
- **FR-017**: The system MUST document host requirements (container runtime, ports, disk space) and provide troubleshooting guidance.
- **FR-018**: Provisioning logic MUST be testable against a fake or sample dataset without synthesized audio from real engines.

### Key Entities

- **Evaluation Environment**: The containerized Label Studio with its volumes and configuration.
- **Evaluation Project**: A Label Studio project of one evaluation type.
- **Task**: One audio or audio pair with its question.
- **Blind Mapping**: Private link between opaque identifiers and engine, voice, and sentence.
- **Quality Control Item**: A repeated item or attention check.
- **Backup Archive**: Restorable snapshot of annotation data.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: From a fresh clone, a working environment with all projects provisioned is reached with no more than three documented commands.
- **SC-002**: After stop and start, 100% of projects, tasks, and annotations remain.
- **SC-003**: Backup followed by restore on a clean environment reproduces identical annotations.
- **SC-004**: No engine name or identifying filename is visible in any annotator-facing field.
- **SC-005**: Running provisioning twice yields no duplicate projects or tasks.
- **SC-006**: Every export row traces to engine, voice, sentence, and corpus version.
- **SC-007**: The environment starts and works with no network access once the image is available.

## Assumptions

- Container delivery (image definition and orchestration) is an explicit user requirement, so it is treated as a product constraint rather than an implementation choice.
- Synthesized audio, the corpus (002), and cloned-voice consent records (003) are produced by earlier features and are inputs here; this feature does not synthesize audio.
- Speaker-similarity tasks cover only the cloning subset with consented voices.
- Annotators are a small trusted group (local or invited); large-scale crowdsourcing is out of scope.
- Rating scales follow common 1–5 conventions (MOS) and a 7-point comparison scale (CMOS); exact anchors are fixed in the plan before collection.
- Aggregated analysis and report generation belong to the results report feature; this feature only exports its inputs.
- Annotators are few (about 2 to 5), each completing whole projects; no enforced task assignment or overlap is needed.
- Default batch size is about 20 sentences per engine-voice condition, with roughly 10% repeated items and 5% attention checks; adjustable in the batch configuration.
- Docker with Compose v2 is the only supported container runtime; other runtimes are not tested.
- Backup archives are stored outside tracked files and are git-ignored.
- Only open-source functionality is used: Label Studio Community Edition and open-source tooling. No paid or Enterprise-only features, no paid services, and no external API keys or accounts are required. The only credentials are the local administrator login and the local Label Studio access token, both created and kept on the host.

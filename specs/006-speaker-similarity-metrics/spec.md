# Feature Specification: Speaker Similarity and Consistency Metrics

**Feature Branch**: `006-speaker-similarity-metrics`

**Created**: 2026-11-03

**Status**: Draft

**Input**: User description: "For cloning-capable engines, compare voice identity between the reference recording and synthesized audio using speaker embeddings and cosine similarity, optionally compute EER, and measure variability between repeated generations."

## Clarifications

### Session 2026-11-03

- Q: Which synthesized audio should the per-sentence similarity score use? → A: One designated run per sentence for the headline similarity; all repeated runs are used only for the consistency check.
- Q: Where do the labeled pairs for the optional EER check come from? → A: Built from the project's own audio: reference vs. its cloned outputs (same speaker) and vs. other voices' recordings or outputs (different speaker).
- Q: Is EER reported once per comparison or per engine? → A: Once per comparison, using pairs pooled across all cloning engines.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Score how close a cloned voice is to the reference (Priority: P1)

A developer wants a repeatable number showing how similar Phonon's and Pocket TTS's cloned voices are to the reference speaker.

**Why this priority**: Voice cloning fidelity is a key criterion for the project's engine comparison.

**Independent Test**: Two identical audio files score near the maximum similarity; clearly different speakers score lower, using fixed test fixtures.

**Acceptance Scenarios**:

1. **Given** a reference recording and synthesized audio, **When** the metric runs, **Then** it computes cosine similarity between their speaker embeddings.
2. **Given** all cloning engines in a comparison, **When** the metric runs, **Then** the same embedding model is used for every engine.
3. **Given** the cloning subset of the corpus, **When** similarity is computed, **Then** it is reported per sentence and as an average per engine.

---

### User Story 2 - Measure consistency across repeated generations (Priority: P2)

A developer wants to know how much an engine's output varies when the same text is generated several times.

**Why this priority**: Unstable pronunciation, duration, or voice hurts real-time products.

**Independent Test**: Using the fake engine with controlled variation, the coefficient of variation matches the expected value.

**Acceptance Scenarios**:

1. **Given** the same sentence generated several times, **When** consistency is computed, **Then** the coefficient of variation is reported for duration and for similarity score.
2. **Given** a metric with near-zero mean, **When** the coefficient is requested, **Then** the system declines to report it as unreliable.

---

### User Story 3 - Optionally verify with equal error rate (Priority: P3)

A researcher wants to validate that the embedding model separates the reference speaker from other speakers before trusting the similarity scores.

**Why this priority**: Gives confidence in the metric; useful but not required for every run.

**Independent Test**: With a labeled set of same-speaker and different-speaker pairs, EER is computed and reported.

**Acceptance Scenarios**:

1. **Given** labeled same-speaker and different-speaker pairs, **When** the check runs, **Then** it reports the equal error rate.
2. **Given** a high EER, **When** results are reported, **Then** a warning states that similarity scores should be interpreted cautiously.

---

### Edge Cases

- Cosine similarity close to 1 does not guarantee the voice sounds identical: reports state this limitation.
- Noise, language, and prosody affect embeddings: reference quality is recorded.
- Engines without cloning (Piper) are excluded from this metric and not penalized.
- Very short audio yields unreliable embeddings: flagged with a minimum duration.
- Silent or empty audio, or a sentence for which synthesis produced no audio: flagged and excluded from the similarity average, with the count of exclusions shown.
- Fewer than two repeated generations of a sentence: consistency is reported as not available, never estimated.
- Labeled pairs containing only one kind (all same-speaker or all different-speaker): EER is reported as not available.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST compute cosine similarity between speaker embeddings of the reference and each synthesized audio.
- **FR-002**: The system MUST use the same embedding model, version, and settings for all engines in a comparison, and MUST refuse to compare results where they differ, stating which one differs.
- **FR-003**: The system MUST report similarity per sentence, computed from one designated run per sentence (the same run for every engine), and averaged per engine.
- **FR-004**: The system MUST compute the coefficient of variation across all repeated generations of a sentence for duration and similarity; repeated runs feed only this consistency check, not the headline similarity.
- **FR-005**: The system MUST support an optional EER check from labeled same-speaker and different-speaker pairs built from the project's own audio: the reference against its cloned outputs (same speaker) and against other voices' recordings or outputs (different speaker). EER is reported once per comparison, pooled across all cloning engines.
- **FR-006**: The system MUST exclude non-cloning engines without penalty, listing them as "not applicable" rather than scored.
- **FR-007**: The system MUST warn when audio is shorter than the minimum duration for reliable embeddings.
- **FR-008**: The system MUST state in outputs that similarity scores are not a substitute for human judgment.
- **FR-009**: The system MUST record the embedding model identity and version in results.
- **FR-010**: Computation MUST be testable with fixed embeddings and no model weights.
- **FR-011**: The system MUST decline to report a coefficient of variation when the mean is near zero, marking it unreliable.
- **FR-012**: The system MUST record the reference recording's quality (for example duration and noise level) in the results.

### Key Entities

- **Speaker Embedding**: Vector representing voice identity for one audio.
- **Similarity Score**: Cosine similarity between two embeddings.
- **Consistency Record**: Variation statistics across repeated generations.
- **Labeled Pair Set**: Same-speaker and different-speaker audio pairs used for the optional EER check.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: Identical-audio pairs produce similarity within 0.01 of the maximum; test fixtures for different speakers score clearly lower.
- **SC-002**: 100% of cloning comparisons use the same embedding model for all engines.
- **SC-003**: Coefficient of variation on the fake engine matches expected values within 5%.
- **SC-004**: The report always includes the limitation statement from FR-008.
- **SC-005**: Re-running on the same audio and settings yields identical similarity scores.

## Assumptions

- Only cloning-capable engines (Phonon, Pocket TTS) are scored; Piper is reported as not applicable.
- Reference recordings and cloned-voice audio come from the voice preparation feature (003); consent is already documented there and the recordings remain git-ignored.
- Audio to score comes from the existing engine adapters (001) and the cloning subset of the Spanish corpus (002); repeated generations reuse the repetition mechanism of feature 004.
- The embedding model runs locally and is deterministic for identical audio and settings (needed for SC-005).
- The specific embedding model, the minimum duration for reliable embeddings, the near-zero-mean threshold, and the "high EER" threshold are decided during planning and documented; they apply equally to all engines.
- No public dataset is bundled; the EER check needs at least one other voice besides the reference, otherwise it is reported as not available.
- All reference and generated audio is Spanish (es-CO); the embedding model must be validated on Spanish audio before its scores are trusted, using the project's own Spanish pairs, and results record the audio language.
- "Clearly lower" for different-speaker similarity (SC-001) and for the Spanish validation means a separation of at least 0.20 between the mean same-speaker and mean different-speaker scores.
- Intelligibility (005), latency and resources (004), and naturalness (human evaluation) are out of scope.

# Feature Specification: Intelligibility Metrics (WER and CER)

**Feature Branch**: `005-intelligibility-metrics`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Transcribe synthesized audio with one fixed speech recognition system and compute word error rate and character error rate against the corpus text, with Spanish text normalization."

## Clarifications

### Session 2026-11-02

- Q: Should accent marks be kept or ignored when comparing reference and transcript? → A: Ignore accent marks on vowels (keep "ñ" distinct) for the primary WER and CER; also report the accent-sensitive WER and CER as a secondary figure.
- Q: Should the metric also transcribe the voice-cloning sentences? → A: No; main corpus only, cloning sentences are out of scope.
- Q: How should a sentence with no audio because synthesis failed count? → A: As a full failure (all reference words deleted, WER 100%), flagged, same as silent audio.
- Q: Should every repetition and run mode be transcribed, or one synthesis per sentence? → A: One synthesis per sentence per engine, from a single designated run.
- Q: What happens when results from different recognizers or settings are compared? → A: The comparison is refused, and the output states which recognizer identity, version, or setting differs.

## User Scenarios & Testing *(mandatory)*

### User Story 1 - Compute WER and CER per engine (Priority: P1)

A developer wants to know how often an engine's speech is misunderstood by a recognizer, as a proxy for pronunciation and intelligibility.

**Why this priority**: Gives an objective, repeatable intelligibility signal alongside human evaluation.

**Independent Test**: Feed known transcripts and known reference texts; computed WER and CER match hand-calculated values.

**Acceptance Scenarios**:

1. **Given** synthesized audio for the corpus, **When** the metric runs, **Then** each sentence is transcribed and WER and CER are computed against its reference text.
2. **Given** all engines in a comparison, **When** the metric runs, **Then** the same recognition system and settings are used for every engine.
3. **Given** the run completes, **When** results are shown, **Then** per-sentence, per-category, and overall WER and CER are reported.

---

### User Story 2 - Normalize Spanish text fairly (Priority: P1)

An evaluator wants errors counted for real mistakes, not for formatting differences such as "123" versus "ciento veintitrés".

**Why this priority**: Without normalization, number and acronym sentences produce misleading errors.

**Independent Test**: A reference with digits and a transcript with the same number in words yields zero error after normalization.

**Acceptance Scenarios**:

1. **Given** a reference with digits, currency, or dates, **When** normalization runs, **Then** it uses the normalized expected reading from the corpus.
2. **Given** differences in case, punctuation, or accents handling, **When** comparison runs, **Then** the normalization rules are applied identically to reference and transcript and are documented.

---

### User Story 3 - Identify where errors concentrate (Priority: P2)

A developer wants to see which categories and words an engine gets wrong.

**Why this priority**: Targeted diagnosis guides which engine suits which use case.

**Independent Test**: A run with known errors lists the exact words and categories involved.

**Acceptance Scenarios**:

1. **Given** completed results, **When** the error breakdown is requested, **Then** substitutions, deletions, and insertions are listed per sentence.
2. **Given** categories such as names, numbers, and acronyms, **When** results are summarized, **Then** error rates are reported per category.

---

### Edge Cases

- The recognizer itself makes errors: its identity and version are recorded, and the report states that WER reflects recognizer and engine together.
- Empty or silent audio, or a sentence for which synthesis produced no audio: counted as a full failure (every reference word a deletion, so WER 100%), flagged.
- Very short sentences: a single error weighs heavily; sample sizes are shown.
- Regional accent can raise recognizer errors: noted in the results metadata.
- A reference that normalizes to zero words: WER is undefined for that sentence; it is flagged and excluded from rate averages while remaining counted in the sample size.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The system MUST transcribe one synthesized audio per sentence per engine (from a single designated run) with one recognition system configured identically for all engines.
- **FR-002**: The system MUST compute WER as (substitutions + deletions + insertions) divided by reference word count.
- **FR-003**: The system MUST compute CER using characters instead of words.
- **FR-004**: The system MUST apply documented Spanish normalization identically to reference and transcript. The primary figures ignore accent marks on vowels while keeping "ñ" distinct; accent-sensitive WER and CER MUST also be reported as secondary figures.
- **FR-005**: The system MUST report results per sentence, per category, and overall.
- **FR-006**: The system MUST report substitutions, deletions, and insertions separately.
- **FR-007**: The system MUST record the recognizer identity, version, and settings in the results, and MUST refuse to compare results whose recognizer identity, version, or settings differ, stating which one differs.
- **FR-008**: The system MUST flag silent or empty audio, and sentences with no audio because synthesis failed, and count each as a full failure.
- **FR-009**: The system MUST state in outputs that WER measures intelligibility, not naturalness.
- **FR-010**: Computation MUST be testable with fixed transcripts and no recognizer.
- **FR-011**: The system MUST mark a results set as not reliable when more than 10% of its sentences are flagged (silent, failed, empty transcript, or undefined reference), and MUST show this in the summary.

### Key Entities

- **Transcript**: Recognizer output for one audio.
- **Error Breakdown**: Counts of substitutions, deletions, and insertions.
- **Normalization Ruleset**: Documented text normalization applied before comparison.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: WER and CER on known test pairs match hand-calculated values exactly.
- **SC-002**: 100% of comparisons use the same recognizer and settings for all engines.
- **SC-003**: Results are available per category for every category in the corpus.
- **SC-004**: Re-running on the same audio yields identical WER and CER.

## Assumptions

- A "category" is a corpus feature tag (names, numbers, amounts, dates, acronyms, questions, hard words, short, long) or a campaign. A sentence with several tags is counted in each tag group, so tag groups overlap; this is stated in reports.
- Audio to transcribe comes from the existing engine adapters (001) and the Spanish corpus (002); the reference text is the corpus sentence, using its normalized expected reading where one exists.
- Overall and per-category rates are computed by pooling error counts and reference lengths across sentences, not by averaging per-sentence rates.
- The recognizer runs locally, consistent with the project's local-engine scope, and is deterministic for identical audio and settings (needed for SC-004).
- Remaining normalization choices (case, punctuation, numbers) are decided during planning and documented in the ruleset; they apply equally to all engines.
- Only the main corpus is scored; the voice-cloning sentences and cloned-voice audio are out of scope for this feature.
- Naturalness, latency, and resource use are out of scope; they are covered by human evaluation and feature 004.

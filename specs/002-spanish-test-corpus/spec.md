# Feature Specification: Spanish Call Center Test Corpus

**Feature Branch**: `002-spanish-test-corpus`

**Created**: 2026-10-29

**Status**: Draft

**Input**: User description: "Create and version a corpus of Spanish sentences from call center scenarios: outbound sales campaigns for telephony products (plans, number portability, devices, internet), credit card collection campaigns (overdue installments, payment agreements), and inbound campaigns (customer service, billing, support), shared by every metric and evaluation."

## Clarifications

### Session 2026-10-29

- Q: What is the minimum number of sentences each required feature tag must have? → A: 10 per tag, the same for every tag

## User Scenarios & Testing *(mandatory)*

### User Story 1 - One shared, versioned corpus (Priority: P1)

A developer runs any metric or evaluation and knows every engine received exactly the same sentences.

**Why this priority**: Fair comparison depends on identical input (Constitution Principle III).

**Independent Test**: Load the corpus, confirm identifiers are unique and every result file references the same corpus version.

**Acceptance Scenarios**:

1. **Given** the corpus, **When** it is loaded, **Then** it contains at least 100 sentences, each with an identifier, text, campaign type, and feature tags.
2. **Given** a result file from any feature, **When** it is inspected, **Then** it records the corpus version.
3. **Given** the corpus changes, **When** a new version is released, **Then** the version identifier changes and the change is documented.

---

### User Story 2 - Represent real call center campaigns (Priority: P1)

An evaluator wants sentences that sound like what a synthetic agent would actually say in the intended business: selling, collecting, and answering calls.

**Why this priority**: Engines must be judged on the language of the target use case, not generic text.

**Independent Test**: Count sentences per campaign type and scenario and confirm each meets its minimum.

**Acceptance Scenarios**:

1. **Given** the corpus, **When** campaign types are counted, **Then** each of these has at least 25 sentences: outbound sales, collections, and inbound.
2. **Given** outbound sales sentences, **When** they are reviewed, **Then** they cover mobile plans (prepaid and postpaid), number portability, device and promotional offers, internet or fiber, upgrades, prices, and handling of customer objections.
3. **Given** collections sentences, **When** they are reviewed, **Then** they cover credit card balances, overdue installments, due dates, payment agreements, payment channels, and payment reminders.
4. **Given** inbound sentences, **When** they are reviewed, **Then** they cover greetings, identity verification, balance and invoice queries, complaints, technical support, plan changes, and call closing.
5. **Given** the whole corpus, **When** it is reviewed, **Then** it includes call-opening disclosures (for example, that the call is recorded) and short conversational responses.

---

### User Story 3 - Stress the hard parts of Spanish TTS (Priority: P1)

An evaluator wants sentences that expose real weaknesses, tagged so results can be broken down.

**Why this priority**: Call center language is dense in numbers, amounts, dates, and acronyms, which is where engines usually fail.

**Independent Test**: Count sentences per feature tag and confirm each required tag has its minimum.

**Acceptance Scenarios**:

1. **Given** the corpus, **When** feature tags are counted, **Then** each of these has at least 10 sentences: amounts in Colombian pesos, phone and account numbers, dates and times, acronyms, fictitious proper names, questions, long sentences, short utterances, and difficult words.
2. **Given** the intended use is Colombian Spanish, **When** the corpus is reviewed, **Then** it includes documented Colombian and Latin American expressions and forms of address.

---

### User Story 4 - Separate held-out sentences for cloning tests (Priority: P2)

An evaluator testing voice cloning needs sentences that do not appear in the reference recording.

**Why this priority**: Cloning quality is only meaningful on unseen text.

**Independent Test**: Verify no sentence in the cloning subset appears in any reference recording transcript.

**Acceptance Scenarios**:

1. **Given** a reference recording transcript, **When** the cloning subset is generated or checked, **Then** no sentence overlaps with the transcript.
2. **Given** the cloning subset, **When** it is used, **Then** it is stored as a separate, labeled subset covering all three campaign types.

---

### Edge Cases

- Duplicate or near-duplicate sentences: detected and reported.
- Numbers with ambiguous readings (phone numbers, amounts, years, account digits): the expected spoken reading is annotated for text normalization.
- Very long legal or disclosure sentences that exceed an engine's limit: recorded as engine limitations, never silently truncated.
- Sentences containing real personal data or real company names: excluded; all names, numbers, and companies are fictitious.
- Collection sentences with threatening, humiliating, or coercive wording: excluded; the tone is respectful and professional.
- Regional forms of address (usted, tú, vos): the form used is tagged.

## Requirements *(mandatory)*

### Functional Requirements

- **FR-001**: The corpus MUST contain at least 100 Spanish sentences, each with a unique identifier, text, campaign type, and feature tags.
- **FR-002**: The corpus MUST include at least 25 sentences for each campaign type: outbound sales, collections, and inbound.
- **FR-003**: Outbound sales sentences MUST cover mobile plans, number portability, devices and promotions, internet or fiber, upgrades, pricing, and objection handling.
- **FR-004**: Collections sentences MUST cover credit card balances, overdue installments, due dates, payment agreements, payment channels, and reminders.
- **FR-005**: Inbound sentences MUST cover greetings, identity verification, billing queries, complaints, technical support, plan changes, and call closing.
- **FR-006**: The corpus MUST include these feature tags with a minimum of 10 sentences each: amounts in pesos, phone and account numbers, dates and times, acronyms, fictitious proper names, questions, long sentences, short utterances, and difficult words.
- **FR-007**: The corpus MUST include documented Colombian and Latin American vocabulary and forms of address.
- **FR-008**: All names, numbers, amounts, and companies MUST be fictitious, and collection wording MUST be respectful and non-coercive.
- **FR-009**: Each sentence containing numbers, symbols, or acronyms MUST include its normalized expected spoken reading.
- **FR-010**: The corpus MUST carry a version identifier that every result file records.
- **FR-011**: The corpus MUST provide a separate cloning subset whose sentences do not occur in any reference recording and that covers all three campaign types.
- **FR-012**: The system MUST validate the corpus (unique ids, non-empty text, required fields, minimum counts, no duplicates) before use.
- **FR-013**: The corpus MUST be stored in a plain, diff-friendly format.
- **FR-014**: Every sentence MUST be something a voice agent would plausibly say in a real call of its campaign, in natural spoken register (not written or literary text), and MUST be reviewed against that standard by a native Colombian Spanish speaker before a version is released.
- **FR-015**: Every sentence MUST declare which difficulty it probes (for example, reading an amount, a phone number, a date, a long disclosure, a fast acknowledgment, or a regional expression), and the corpus MUST include several sentences per difficulty so a weak engine cannot pass by handling only easy text.

### Key Entities

- **Sentence**: Identifier, text, campaign type, scenario, feature tags, difficulty probed, form of address, normalized reading, review status, and subset membership.
- **Campaign Type**: Outbound sales, collections, or inbound.
- **Corpus Version**: Identifier and change notes.
- **Cloning Subset**: Sentences reserved for tests of cloned voices.

## Success Criteria *(mandatory)*

### Measurable Outcomes

- **SC-001**: The corpus has at least 100 validated sentences, with at least 25 per campaign type.
- **SC-002**: Every required feature tag has at least 10 sentences.
- **SC-003**: 100% of result files record the corpus version used.
- **SC-004**: Zero overlap between the cloning subset and any reference transcript.
- **SC-005**: Corpus validation runs in under one minute with no network access.
- **SC-006**: A native Colombian Spanish reviewer approves 100% of released sentences as natural for a real call center agent, and each sentence names the difficulty it probes.

## Assumptions

- The 10-sentence minimum per feature tag is a validation rule that can be adjusted in a later corpus version.
- Short utterances are sentences of 5 words or fewer; long sentences are 25 words or more.
- The default form of address is "usted", as is standard in Colombian call centers; at least 5 sentences use "tú" and at least 5 use "vos", each tagged.
- The cloning subset has about 20 sentences, at least 5 per campaign type.
- Reference transcripts are read from `cloned_voices/<voice>/transcript.txt` (git-ignored); until one exists, the overlap check is reported as "not run".
- The assistant drafts the sentences; a native Colombian Spanish reviewer (Jose Alberto) approves them, and release of version 1.0.0 is blocked until that review is done.
- Campaign scenario names (for example, portability, overdue installment, billing query) are a fixed, documented list used for the coverage checks.
- Reference recording transcripts are provided by the voice-cloning feature; this feature only checks the cloning subset against whatever transcripts are supplied.
- Result files from other features (engine adapters, metrics, evaluations) will record the corpus version; enforcing that in those features is out of scope here, and this feature only exposes the version.
- Sentences are the agent's side of the conversation (what the voice agent says); customer lines appear only as short responses the agent might echo.
- Corpus authoring is a one-time creation with later versioned revisions. No sentence-generation tooling is part of the repository; sentences are drafted by the assistant and reviewed by a person.
- Only Spanish text is in scope; audio is not part of the corpus.

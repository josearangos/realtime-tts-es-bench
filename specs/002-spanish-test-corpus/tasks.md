---

description: "Task list for Spanish Call Center Test Corpus"
---

# Tasks: Spanish Call Center Test Corpus

**Input**: Design documents from `/specs/002-spanish-test-corpus/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/corpus-interface.md, quickstart.md

**Tests**: Included. Constitution Principle VIII requires every requirement to map to a checkable scenario; validator rules are tested with small fixture corpora.

**Organization**: Grouped by user story. Paths follow plan.md (`corpus/`, `src/tts_bench/corpus/`, `tests/corpus/`). No new dependencies (standard library only).

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1 (one shared, versioned corpus), US2 (real call center campaigns), US3 (hard parts of Spanish TTS), US4 (cloning subset)

---

## Phase 1: Setup

- [X] T001 Create the layout from plan.md: `corpus/` (empty `sentences.jsonl`, `cloning.jsonl`), `src/tts_bench/corpus/__init__.py`, `tests/corpus/__init__.py`, `tests/corpus/fixtures/`
- [X] T002 [P] Verify `.gitignore` still ignores `cloned_voices/` and that `corpus/` is NOT ignored (transcripts must never be copied into `corpus/`)

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: data types and loader used by the validator and by other features

- [X] T003 [P] Define in `src/tts_bench/corpus/model.py` the enums `Campaign` (`outbound_sales`, `collections`, `inbound`), `Scenario` (outbound_sales: `mobile_prepaid`, `mobile_postpaid`, `portability`, `device_promo`, `internet_fiber`, `upgrade`, `pricing`, `objection`; collections: `card_balance`, `overdue_installment`, `due_date`, `payment_agreement`, `payment_channel`, `payment_reminder`; inbound: `greeting`, `identity_verification`, `billing_query`, `complaint`, `tech_support`, `plan_change`, `closing`; any campaign: `disclosure`, `short_response`), `Tag` (`amount_cop`, `number`, `datetime`, `acronym`, `proper_name`, `question`, `long`, `short`, `hard_word`), `Address` (`usted`, `tu`, `vos`, `none`), `Probe` (`amount`, `phone_or_account`, `datetime`, `acronym`, `name`, `long_disclosure`, `fast_ack`, `regionalism`, `prosody_question`, `hard_word`), `Subset` (`main`, `cloning`)
- [X] T004 Define frozen `Sentence` in `src/tts_bench/corpus/model.py` with fields `id` (unique; pattern `<prefix>-NNN`, prefixes `VEN`, `COB`, `ENT`, `CLO`), `text` (non-empty, no leading/trailing spaces), `campaign`, `scenario`, `tags` (list), `address` (default `usted`), `spoken` (required when text has digits, symbols, or acronyms; contains none of them), `probes` (required), `reviewed` (bool), `subset` (must match its file); and `CorpusVersion` (`version` MAJOR.MINOR.PATCH, `date` ISO, `counts`, `content_sha256`)
- [X] T005 Implement `src/tts_bench/corpus/loader.py`: read a `.jsonl` file into `Sentence` objects ordered by id, raise a clear error naming the file and line number for malformed records or unknown enum values, read `VERSION.json`, and compute SHA-256 over the contents of `sentences.jsonl` and `cloning.jsonl`
- [X] T006 Implement `load_corpus(path=None, subset="main") -> Corpus` in `src/tts_bench/corpus/__init__.py` per contracts/corpus-interface.md: `Corpus.version`, `Corpus.content_hash`, `Corpus.sentences` (tuple ordered by id), `by_campaign()`, `by_tag()`, `by_scenario()`
- [X] T007 [P] Unit tests for the loader in `tests/corpus/test_loader.py`: ordering by id, malformed line error includes the line number, unknown enum rejected, hash changes when text changes (fixtures in `tests/corpus/fixtures/`)

---

## Phase 3: User Story 1 - One shared, versioned corpus (P1)

**Goal**: every metric and evaluation loads the same sentences and can record the version.

**Independent Test**: load the corpus, unique ids, version present, hash matches; changing a sentence without a version bump fails validation.

- [X] T008 [US1] Create `corpus/VERSION.json` (`version` `0.1.0`, date, counts, `content_sha256`) and `corpus/CHANGELOG.md` with an entry per version; rule: adding sentences is MINOR, editing or removing text is MAJOR, fixing tags or readings is PATCH (research R2)
- [X] T009 [US1] Implement base rules in `src/tts_bench/corpus/validate.py`: unique ids, non-empty text, required fields present, enum values valid, `subset` matches file, total at least 100 main sentences, exact-duplicate and near-duplicate detection (normalized word-set Jaccard of 0.9 or more, reported), `VERSION.json` hash equals computed hash (warning while version is `0.x`, error from `1.0.0`), matching `CHANGELOG.md` heading for the version; probe/tag agreement per data-model.md ("Tags and probes"); result separates errors (block use) from warnings
- [X] T010 [US1] Implement `src/tts_bench/corpus/__main__.py`: `python -m tts_bench.corpus validate [--transcripts PATH ...] [--path DIR]` and `python -m tts_bench.corpus stamp` (recomputes counts and `content_sha256` in `corpus/VERSION.json`, research R11); prints counts per campaign, scenario, tag; exit 0 without errors, 1 with errors; no network access
- [X] T011 [P] [US1] Tests in `tests/corpus/test_validate.py`: duplicate id, empty text, missing field, fewer than 100 sentences, near-duplicate warning, hash mismatch, missing changelog heading each produce the matching error (FR-001, FR-010, FR-012)
- [X] T012 [P] [US1] Document in `corpus/CHANGELOG.md` and `specs/002-spanish-test-corpus/contracts/corpus-interface.md` that result files must record `corpus_version` and `corpus_hash` from `load_corpus()` (FR-010, SC-003); add `corpus_stamp(corpus) -> dict` in `src/tts_bench/corpus/__init__.py` returning those two keys for other features to embed, with a test in `tests/corpus/test_loader.py`; enforcing it in result files belongs to the other features (add a follow-up note to `specs/001-tts-engine-adapters/tasks.md` is out of scope here)

**Checkpoint**: tooling works against fixtures; the real data is authored in the next phases.

---

## Phase 4: User Story 2 - Represent real call center campaigns (P1)

**Goal**: sentences a synthetic agent would really say when selling, collecting, and answering, in natural spoken Colombian register, agent side.

**Independent Test**: validator reports at least 25 per campaign and at least 2 per scenario; disclosures and short responses at least 5 each.

Authoring rules for T013 to T015 (from FR-014, research R10): write as continuous call scripts per scenario (opening, offer or request, objection or reply, close); spoken register, not written text; fictitious people, companies, and numbers only (phone numbers `300 000 xxxx`-style); collections wording respectful and non-coercive; every sentence has `probes` and `reviewed` set to `false`; ids sorted, one JSON object per line with fixed key order, UTF-8 with accents unescaped.

- [X] T013 [US2] Author at least 35 outbound sales sentences (`VEN-001`...) in `corpus/sentences.jsonl` covering `mobile_prepaid`, `mobile_postpaid`, `portability`, `device_promo`, `internet_fiber`, `upgrade`, `pricing`, `objection`, at least 2 each, using a fictitious carrier name
- [X] T014 [US2] Author at least 35 collections sentences (`COB-001`...) in `corpus/sentences.jsonl` covering `card_balance`, `overdue_installment`, `due_date`, `payment_agreement`, `payment_channel`, `payment_reminder`, at least 2 each, using a fictitious bank; tone respectful, no threats, no shaming, no legal intimidation
- [X] T015 [US2] Author at least 35 inbound sentences (`ENT-001`...) in `corpus/sentences.jsonl` covering `greeting`, `identity_verification`, `billing_query`, `complaint`, `tech_support`, `plan_change`, `closing`, at least 2 each
- [X] T016 [US2] Add across the three campaigns at least 5 `disclosure` sentences (for example recording notice, data-handling notice, at least one of 25 words or more with `probes` `long_disclosure`) and at least 5 `short_response` sentences ("Claro que sí.", "Con gusto.", "Un momento, por favor."); these are in addition to the 2 per campaign scenario
- [X] T017 [US2] Add to `src/tts_bench/corpus/validate.py` the coverage rules: at least 25 sentences per campaign, at least 2 per scenario (research R7), at least 5 `disclosure`, at least 5 `short_response`, at least 5 per `probes` value (FR-002 to FR-005, FR-015); and a banned-phrase check for collections text (threat, legal intimidation, public shaming terms, list kept in `src/tts_bench/corpus/banned_phrases.txt`) (FR-008)
- [X] T018 [P] [US2] Tests in `tests/corpus/test_validate.py`: campaign below 25, scenario below 2, missing disclosure, banned phrase in a collections fixture each fail with the matching error

---

## Phase 5: User Story 3 - Stress the hard parts of Spanish TTS (P1)

**Goal**: sentences dense in the things engines get wrong, tagged so results can be broken down.

**Independent Test**: each of the nine tags has at least 10 sentences; every sentence with digits, symbols, or acronyms has a spoken reading; documented regionalisms exist.

- [X] T019 [US3] Review and extend the sentences in `corpus/sentences.jsonl` so each tag reaches at least 10: `amount_cop` (e.g. "$45.900", "$1.250.000"), `number` (phone and account numbers), `datetime` (dates, times, due dates), `acronym` (PQR, SMS, IVA, NIT, 4G, APP, CC), `proper_name` (fictitious), `question`, `long` (25 words or more), `short` (5 words or fewer), `hard_word` (for example "portabilidad", "refinanciación", "extemporáneo")
- [X] T020 [US3] Fill `spoken` for every sentence with digits, symbols, or acronyms, using Colombian conventions (research R5): amounts as "cuarenta y cinco mil novecientos pesos", phone numbers in digit groups, dates and times in words, acronyms either spelled or read as words per usage; no digits or symbols left in `spoken` (FR-009)
- [X] T021 [US3] Set `address` on every sentence; at least 5 sentences with `tu` and at least 5 with `vos`, the rest `usted` or `none`
- [X] T022 [US3] Write `corpus/REGIONALISMS.md`: a table of Colombian and Latin American expressions and forms of address used in the corpus (for example "con gusto", "a la orden", "regálame un momento", "listo", "plata", "celular", "cuota", "paz y salvo"), each with region, register, and the sentence ids using it; flag that a native Colombian reviewer must confirm it (FR-007)
- [X] T023 [US3] Add to `src/tts_bench/corpus/validate.py` the tag rules: each of the nine tags at least 10 in the main file; consistency checks (`long` needs 25 or more words, `short` 5 or fewer, `question` needs a question mark, `amount_cop` and `number` need digits, `acronym` needs an uppercase run of two or more letters); `spoken` required when text has digits, symbols, or acronyms and must not contain any; at least 5 `tu` and 5 `vos` sentences; every `REGIONALISMS.md` sentence id exists (FR-006, FR-009)
- [X] T024 [P] [US3] Tests in `tests/corpus/test_validate.py`: tag below 10, `long` tag on a short text, missing `spoken`, `spoken` containing a digit, unknown id in regionalisms each fail with the matching error

---

## Phase 6: User Story 4 - Cloning subset (P2)

**Goal**: held-out sentences never present in a reference recording.

**Independent Test**: cloning file covers all three campaigns and the overlap check against a transcript reports passed, failed, or not run.

- [X] T025 [US4] Author about 20 sentences in `corpus/cloning.jsonl` (`CLO-001`...), at least 5 per campaign, `subset` `cloning`, same schema and authoring rules as US2, disjoint from `corpus/sentences.jsonl`
- [X] T026 [US4] Add to `src/tts_bench/corpus/validate.py`: the cloning file covers all three campaigns with at least 5 each, ids and normalized texts disjoint from the main file, and the transcript overlap check (research R3, R4): split transcripts on sentence punctuation, normalize (lowercase, accents kept, punctuation and extra spaces removed), fail on exact match or word-set Jaccard 0.8 or more; transcripts default to `cloned_voices/<voice>/transcript.txt` when present; with none, report `not run`, never `passed` (FR-011, SC-004)
- [X] T027 [P] [US4] Tests in `tests/corpus/test_validate.py` with fixture transcripts: exact copy fails, near copy fails, unrelated passes, no transcripts reports `not run`, cloning sentence also in main file fails

---

## Phase 7: Polish and release

- [X] T028 Run `python -m tts_bench.corpus validate` and fix every error; confirm it finishes in under one minute offline (SC-005); manually confirm no real person, company, phone, or account appears in any sentence (FR-008)
- [X] T029 Native Colombian Spanish review by Jose Alberto (native reviewer): read every sentence for naturalness as agent speech, check collections tone, spoken readings, and `REGIONALISMS.md`; correct text, then set `reviewed` to `true` per approved sentence (FR-014, SC-006)
- [X] T030 Add a release rule to `src/tts_bench/corpus/validate.py` (`--release` flag): fail if any sentence has `reviewed` false; add a test in `tests/corpus/test_validate.py`
- [X] T031 [P] Add `tests/corpus/test_shipped_corpus.py` validating the real files with the thresholds of the spec (100 sentences, 25 per campaign, 10 per tag) and asserting that validation completes in under 60 seconds (SC-005)
- [X] T032 Release `1.0.0`: update `corpus/VERSION.json` (counts and hash) and add the `1.0.0` entry to `corpus/CHANGELOG.md`; run `validate --release`
- [X] T033 Run through `specs/002-spanish-test-corpus/quickstart.md` steps 1 to 5 and note any deviation in quickstart.md
- [X] T034 [P] Add a short note in the repository README (create the section if needed) on how to load the corpus and stamp results with the corpus version

---

## Dependencies and Order

- Phase 1, then Phase 2, then US1 tooling. US2 to US4 data authoring depends on the model (T003, T004) and the validator (T009) to check progress.
- US2 (T013 to T016) before US3 (US3 refines and extends the same sentences). US4 can start after T004, but its validation (T026) needs T009.
- T013 to T016 and T019 to T021 edit the same data file, so run them in sequence, not in parallel.
- Polish needs all stories; T029 (human review) blocks T030, T032.

### Parallel opportunities
- T003 with T002; T007 with T008 once T005 and T006 exist.
- Test tasks T011, T018, T024, T027 are in the same file but different cases and can be written together after their rules exist.
- T012, T034 are independent documentation tasks.

## Implementation Strategy

1. **MVP (US1)**: Phases 1 to 3. The loader, version stamp, and validator work against fixtures, so other features can already record `corpus_version`.
2. **Real content (US2, then US3)**: author and tag the corpus, keeping validation green at each step.
3. **Cloning (US4)**: add the held-out file and overlap check.
4. **Release**: review by a native Colombian speaker, set `reviewed`, publish `1.0.0`. Until Jose Alberto's review is done the corpus stays at `0.x` and is marked unreviewed.

---

description: "Task list for Intelligibility Metrics (WER and CER)"
---

# Tasks: Intelligibility Metrics (WER and CER)

**Input**: Design documents from `/specs/005-intelligibility-metrics/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/intelligibility-cli.md, contracts/results-file.md, quickstart.md

**Tests**: Included. Constitution Principle VIII and FR-010 require computation to be testable with fixed transcripts and no recognizer. All tests use fixed strings, the fake engine, synthetic WAV files and `FakeRecognizer`: no weights, no network. Only tasks marked `engine` need the real recognizer.

**Organization**: Grouped by user story. Paths follow plan.md (`src/tts_bench/intelligibility/`, `tests/intelligibility/`). Foundational holds the pure alignment, data types and a basic normalizer. US1 delivers the pipeline (synthesize, transcribe, score) with per-sentence, per-group and overall rates and the same-recognizer guard. US2 extends normalization to numbers, currency, times, acronyms and accent handling. US3 adds the error breakdown report and the per-group comparison tables.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1 (WER and CER per engine), US2 (Spanish normalization), US3 (where errors concentrate)

---

## Phase 1: Setup

- [X] T001 Create the package `src/tts_bench/intelligibility/__init__.py` (empty for now), the test package `tests/intelligibility/__init__.py`, and `results/intelligibility/.gitkeep`; confirm with `git check-ignore -v results/intelligibility/x.json` that results files are NOT ignored and with `git check-ignore -v output/intelligibility/x/a.wav` that audio IS ignored (Principle VI)
- [X] T002 [P] Add the optional dependency group `asr = ["faster-whisper"]` to `pyproject.toml` (do not add it to core `dependencies`); document in `README.md` how to create `.venv-asr` with `pip install -e ".[asr]"`

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: pure alignment, data types, a basic normalizer, test fixtures

- [X] T003 [P] Implement `src/tts_bench/intelligibility/align.py`: `align(reference: list[str], hypothesis: list[str]) -> Alignment` with unit-cost Levenshtein and a backtrace returning `ops` as a list of `{op: "match"|"sub"|"del"|"ins", ref, hyp}`. Quote in the docstring: "Backtrace tie-break is fixed: substitution, then deletion, then insertion." Add `ErrorBreakdown(substitutions, deletions, insertions, reference_length)` with `.errors`, and `.rate` = "(S + D + I) / reference_length", `None` when `reference_length == 0`, not capped at 100% (R5); `rate` is stored unrounded as a float computed from the integer counts; add `word_error_rate(ref, hyp)` (tokens split on whitespace) and `char_error_rate(ref, hyp)` (characters of the normalized string, single spaces counted) returning `ErrorBreakdown`
- [X] T004 [P] Implement `src/tts_bench/intelligibility/model.py` as frozen dataclasses with `to_dict()` / `from_dict()` per data-model.md: `ManifestItem`, `Manifest`, `Transcript`, `RecognizerRecord`, `NormalizationRecord`, `SentenceResult`, `GroupSummary`, `ResultsFile`. Quote constraints verbatim: manifest `status` is one of `ok` / `failed` / `silent`; transcript `status` is one of `ok` / `skipped_silent` / `skipped_failed`; `language` is forced `es`; sentence `flags` values are `silent_audio`, `synthesis_failed`, `empty_transcript`, `empty_reference`; group names are `overall`, `tag:<name>`, `campaign:<name>`, `untagged`; `low_sample` is true when "n_sentences < 10"; every file carries `schema_version` (integer, 1)
- [X] T005 [P] Implement the basic normalizer in `src/tts_bench/intelligibility/normalize.py`: `normalize(text, *, fold_accents=True) -> str` applying, in this order, NFC, lowercase, punctuation and symbol removal (`¿?¡!.,;:"'()-…`), accent folding of `á é í ó ú ü` only (never `ñ`) when `fold_accents`, and whitespace collapse (research R4 steps 1, 2, 4, 5, 6); expose `RULESET_VERSION = "1"` and `STEPS` (list of step names, used in the results file). Numerals, currency, times and the lexicon are added in US2
- [X] T006 [P] Create `tests/intelligibility/conftest.py` with: a `corpus` fixture (`load_corpus()` main subset), a `write_wav(path, samples, rate)` helper using the standard-library `wave` module, `tone_audio(seconds, rate)` and `silent_audio(seconds, rate)` generators (numpy), and a `fixed_transcripts(mapping)` helper that builds a `Transcripts` object with a valid `RecognizerRecord` for tests
- [X] T007 [P] Write `tests/intelligibility/test_align.py`: hand-calculated cases for SC-001, each with the expected S, D, I and rate written in the test as an exact `fractions.Fraction` compared with `Fraction(S + D + I, reference_length)` (the stored float must equal `float(Fraction)` with no rounding): identical strings (0 errors); one substitution; one deletion; one insertion; "el gato negro" vs "el perro" (1 sub + 1 del, WER 2/3); reference longer vs hypothesis empty (all deletions, rate 1.0); empty reference with non-empty hypothesis (`rate is None`); WER above 1.0 with many insertions (not capped); CER on "casa" vs "caza" (1/4) and with spaces counted; tie-break determinism (same input run twice gives identical `ops`)

**Checkpoint**: foundation ready, user stories can start

---

## Phase 3: User Story 1 - Compute WER and CER per engine (Priority: P1) 🎯 MVP

**Goal**: for one engine, synthesize the main corpus once, transcribe with one fixed recognizer, and score per sentence, per group and overall; refuse to compare results from different recognizers.

**Independent Test**: fixed transcripts and references give hand-calculated WER and CER; the fake engine plus `FakeRecognizer` run end to end; silent and failed audio count as 100%.

### Tests for User Story 1

- [X] T008 [P] [US1] Write `tests/intelligibility/test_audio_check.py`: zero samples is `silent`; digital silence is `silent`; peak 5e-5 is `silent`; peak 2e-4 is not; a tone is not; stereo and int16 input are handled (int16 scaled to float before the threshold)
- [X] T009 [P] [US1] Write `tests/intelligibility/test_scoring.py` with fixed transcripts and no recognizer: per-sentence WER and CER match hand-calculated values; overall rate equals pooled `sum(errors)/sum(reference units)` and NOT the mean of per-sentence rates (use two sentences of different length to show the difference); `empty_reference` sentences are flagged, excluded from pooled rates, counted in `n_sentences`; reference is the `spoken` text when present, else `text`; groups exist for `overall`, every campaign and every tag present in the corpus, and `untagged` when applicable (SC-003); a sentence with two tags is counted in both tag groups; `low_sample` is true for a group of 9 sentences and false for 10
- [X] T010 [P] [US1] Write `tests/intelligibility/test_failures.py`: a manifest item `failed`, one `silent`, and one with missing audio are each scored as full failure (every reference word a deletion so WER 1.0; every reference character a deletion so CER 1.0), flagged `synthesis_failed` or `silent_audio`, `counted_as_failure` true; a non-silent audio with an empty transcript is scored 100% deletions and flagged `empty_transcript`; `reliable` is false when more than 10% of sentences are flagged and true at exactly 10% (FR-011)
- [X] T011 [P] [US1] Write `tests/intelligibility/test_pipeline_fake.py`: using `FakeAdapter` (including `empty_texts` and `fail_texts` for two sentences) run `synthesize` on 6 sentences into `tmp_path`, `transcribe` with `FakeRecognizer` (scripted text per sentence id), and `score`; assert the manifest statuses `ok` / `failed` / `silent`, that the recognizer was never called for silent or failed items, that the results file has per-sentence, per-group and overall values, and that no `.wav` or voice material path is stored in the results file (Principle VI); also assert the results file contains the recognizer `name`, `checkpoint`, library versions and every setting (FR-007), the engine `spanish_variant` and the fixed `accent_note` (regional accent edge case), the `command` and `environment` blocks, and the FR-009 `notice` text
- [X] T012 [P] [US1] Write `tests/intelligibility/test_files_compare.py` (compare part): `compare` over two results files with identical recognizer record succeeds; differing `checkpoint`, library version, any `settings` value, `ruleset_version`, `corpus_hash`, `subset` or `limit` raises a refusal that names the differing field and the CLI exits 3 (SC-002); differing hardware does NOT block; unknown `schema_version` is refused; the output starts with the FR-009 notice
- [X] T013 [P] [US1] Write `tests/intelligibility/test_determinism.py`: `score` run twice on the same transcripts file produces identical `summary` and `sentences` JSON (SC-004); a transcript cache hit (same audio sha256 and `settings_hash`) returns the stored text without calling the recognizer, and a different `settings_hash` misses the cache

### Implementation for User Story 1

- [X] T014 [P] [US1] Implement `src/tts_bench/intelligibility/audio_check.py`: `inspect_wav(path) -> {duration_s, sample_rate, peak, silent}` using `wave` plus numpy; "a WAV is silent if it has zero samples or its peak absolute amplitude is below 1e-4 (float scale)" (R6)
- [X] T015 [P] [US1] Implement `src/tts_bench/intelligibility/files.py`: `write_manifest` / `read_manifest`, `write_transcripts` / `read_transcripts`, `write_results` / `read_results` with `schema_version` check (refuse unknown versions with a clear message), JSON UTF-8 with sorted stable key order, `sha256_file`, and a path sanitizer that stores paths relative to the repository root or as `<abs-path>` so no user name or home directory is stored (contracts/results-file.md rules)
- [X] T016 [US1] Implement `src/tts_bench/intelligibility/synth.py`: `synthesize_corpus(adapter, corpus, voice, out_dir, *, limit=None) -> Manifest` that loads the engine once, synthesizes each `main` sentence once in corpus order using the sentence `text` (what is sent to the engine), writes `<id>.wav` at the engine's own sample rate (PCM 16-bit from float), records `status` `ok` / `failed` (any `SynthesisError`, message stored, `file` null) / `silent` (via `inspect_wav`), `duration_s`, `sha256`; stores engine descriptor fields, voice name, kind and checksum, corpus version and hash, subset and limit, the `command` (`python -m tts_bench.intelligibility synthesize ...`, paths sanitized) and an `environment` block (Python, OS name and release, `tts_bench` version, git commit; no hostname or user name); only the `main` subset (R2); voices are resolved through `LocalVoiceLibrary.resolve` before synthesis, never from raw paths (depends on T014, T015)
- [X] T017 [P] [US1] Implement `src/tts_bench/intelligibility/recognizer.py`: `Recognizer` protocol (`record() -> RecognizerRecord`, `transcribe(path) -> str`), `FakeRecognizer(scripted: dict[str, str])` keyed by file stem (sentence id); the CLI value `--model fake` builds a `FakeRecognizer` that returns the expected reference text (`spoken` else `text`) of each sentence, giving WER 0, and `--script FILE.json` (a `{sentence_id: text}` map) overrides it for chosen sentences, and `FasterWhisperRecognizer` importing `faster_whisper` lazily with settings exactly: `language="es"`, `beam_size=1`, `temperature=0`, `vad_filter=False`, `condition_on_previous_text=False`, no `initial_prompt`, default `model="large-v3"`, `device="cpu"`, `compute_type="int8"`; raise an install-hint error mapped to exit 2 when the package or weights are missing; `settings_hash` is a sha256 over the sorted settings JSON; record library versions of `faster-whisper` and `ctranslate2`, the checkpoint name, its license (field `license`, flagged in the record if not a permissive license, verified per checkpoint, Principle VI) and the fixed `accent_note` (R9)
- [X] T018 [US1] Implement the transcription stage in `src/tts_bench/intelligibility/transcribe.py`: `transcribe_manifest(manifest, audio_dir, recognizer, cache_dir) -> Transcripts` that skips `silent` items (`skipped_silent`) and failed or missing files (`skipped_failed`) without calling the recognizer, caches text by `sha256(audio)` + `settings_hash`, and stores the raw (non-normalized) text, plus the `command` and `environment` block as for the manifest (Principle V); one recognizer instance and one settings set per invocation (FR-001); writes `<out>/<engine>-transcripts-<UTC timestamp>.json` and prints its path (depends on T015, T017)
- [X] T019 [US1] Implement `src/tts_bench/intelligibility/scoring.py`: `score_transcripts(transcripts, corpus, *, recognizer, engine) -> ResultsFile` building a `SentenceResult` per main sentence (reference = `spoken` if present, else `text`; both sides through `normalize`), primary (accents folded) and accent-sensitive breakdowns for word and char, full-failure handling and flags per T010, and pooled `GroupSummary` for `overall`, `campaign:*`, `tag:*` and `untagged` with `n_sentences`, `n_flagged`, `reference_words`, `reference_chars`, `low_sample`; `reliable` false when more than 10% flagged; includes the FR-009 `notice` text "WER and CER measure intelligibility as heard by one recognizer, not naturalness; results reflect the recognizer and the engine together."; `ops` stored for word level (depends on T003, T004, T005)
- [X] T020 [P] [US1] Implement `src/tts_bench/intelligibility/compare.py` (core part): `compare_results(files) -> str` refusing with `MixedResultsError(field)` when recognizer `name`, `checkpoint`, `library_versions`, any `settings` value, `ruleset_version`, `lexicon_version`, `corpus_hash`, `subset` or `limit` differ; hardware differences are listed but never block; Markdown starts with the notice and prints an overall table (engine, voice, WER, CER, S, D, I, accent-sensitive WER, n sentences, flagged, reliable). Per-group tables are added in US3
- [X] T021 [US1] Implement the CLI in `src/tts_bench/intelligibility/__main__.py` with subcommands `synthesize`, `transcribe` (including `--model fake` and `--script`), `score`, `compare` per contracts/intelligibility-cli.md (flags, defaults, exit codes 0 / 1 / 2 / 3; `ENGINE=fake` available; engine resolved through the existing registry as `tts_bench.metrics.__main__` does); `score` stores `command` as `python -m tts_bench.intelligibility <args>` with sanitized paths and an `environment` block (Python version, OS name and release, `tts_bench` version, git commit; no hostname or user name) (depends on T016, T018, T019, T020)
- [X] T022 [US1] Export `score_transcripts`, `normalize`, `word_error_rate`, `char_error_rate`, `compare_results` from `src/tts_bench/intelligibility/__init__.py`; run `tests/intelligibility` and the existing suites to confirm no regression

**Checkpoint**: US1 is a working MVP. Fake engine, fake recognizer and fixed transcripts reproduce hand-calculated values; the pipeline runs for any engine with the real recognizer.

---

## Phase 4: User Story 2 - Normalize Spanish text fairly (Priority: P1)

**Goal**: errors are counted for real mistakes, not for formatting such as "123" versus "ciento veintitrés"; the same ruleset is applied to reference and transcript and is documented.

**Independent Test**: a reference with digits and a transcript with the same number in words yields zero error; `normalize_pair(spoken, text)` returns identical strings for every corpus sentence with a `spoken` form.

### Tests for User Story 2

- [X] T023 [P] [US2] Write `tests/intelligibility/test_numbers.py`: cardinals 0, 1, 15, 21, 100, 101, 999, 1 000, 2 026, 69 900, 230 000, 1 847 300, 1 000 000 in Spanish words (e.g. "ciento veintitrés", "mil", "un millón ochocientos cuarenta y siete mil trescientos"); `$1.847.300` becomes "... pesos"; thousands separator `.` and decimal `,`; digit-by-digit reading of "4821" ("cuatro ocho dos uno") and of "0045 8832" ("cero cero cuatro cinco, ocho ocho tres dos" tokens without punctuation); times "3:00" ("tres") and "4:30" ("cuatro y media"); day "1" read as "primero" only when followed by " de " and a month name
- [X] T024 [P] [US2] Write `tests/intelligibility/test_normalize.py`: case and punctuation are ignored; with `fold_accents=True` "está" equals "esta" and "papá" equals "papa" while "año" differs from "ano" (`ñ` kept); with `fold_accents=False` "está" differs from "esta"; `normalize` gives the same output for the same text whether it is used as reference or transcript; lexicon: "PSE" and "pe ese e" normalize equally, likewise "SMS", "PQR", "TV", "4G", "20 GB" (to "veinte gigas"), and "NIT" / "IVA" equal "nit" / "iva"; reading selection through `normalize_pair`: reference "cuenta cuatro ocho dos uno" with transcript "cuenta 4821" selects `digits` and scores 0 errors, reference "cuatro mil ochocientos veintiuno" selects `cardinal`; a wrong word is still an error under both readings; the chosen reading is returned per numeral token
- [X] T025 [P] [US2] Write `tests/intelligibility/test_corpus_normalization.py`: for every sentence of `corpus/sentences.jsonl` and `corpus/cloning.jsonl` that has `spoken`, assert `normalize_pair(spoken, text)` returns identical reference and transcript strings under both accent settings (the written form is the "transcript" and the spoken form the "reference"); for sentences without `spoken`, assert `normalize(text)` equals the basic steps applied alone (case, punctuation, accents, whitespace), i.e. numerals, currency, times and lexicon rules change nothing because the text has none (the safeguard in research R4: the written-form rules cover the whole corpus with no recognizer)
- [X] T026 [P] [US2] Add to `tests/intelligibility/test_scoring.py` a case where the reference has digits (`text` only, no `spoken`) and the transcript has the same number in words, expecting zero errors, and a case where the corpus `spoken` reference and a digit transcript give zero errors (User Story 2 independent test); when a reference has digits and no `spoken` form, its numerals are read as cardinals (the default reading of `normalize`) and the transcript reading is selected against that; add a case showing the secondary accent-sensitive WER is higher than the primary when only an accent differs

### Implementation for User Story 2

- [X] T027 [P] [US2] Implement `src/tts_bench/intelligibility/numbers.py`: `cardinal_es(n) -> str` (0 to 999 999 999, "veintiuno", "ciento", "un millón", "mil" without "un" prefix), `digits_es(s) -> str` (per-digit with leading zeros), `expand_currency`, `expand_time`, `parse_numeral(token)` handling `.` thousands and `,` decimals; pure, no dependency (R4: no `num2words`)
- [X] T028 [P] [US2] Implement `src/tts_bench/intelligibility/lexicon.py` with `LEXICON_VERSION = "1"` and the eight entries drawn from the corpus: `pse`→`pe ese e`, `sms`→`ese eme ese`, `pqr`→`pe cu erre`, `tv`→`te ve`, `4g`→`cuatro ge`, `gb`→`gigas`, `nit`→`nit`, `iva`→`iva`; lookup is case-insensitive and applied identically to reference and transcript; adding entries requires bumping `LEXICON_VERSION`
- [X] T029 [US2] Extend `src/tts_bench/intelligibility/normalize.py` with research R4 step 3: expand currency, times, percent, numerals and the lexicon before punctuation removal; add `normalize_pair(reference, transcript, *, fold_accents=True) -> (ref_norm, hyp_norm, readings)` that, for each ambiguous numeric token in the transcript, produces the `cardinal` and `digits` readings and selects the one with the smaller word edit distance to the reference (ties go to `cardinal`), returning the per-token readings; update `STEPS` and bump nothing else; `normalize(text)` stays single-text and reads numerals as cardinals (so a reference without `spoken` is read as cardinals); apply the lexicon BEFORE numeral expansion and match it on whole tokens, so "4G" becomes "cuatro ge" and "20 GB" becomes "veinte gigas" (depends on T027, T028)
- [X] T030 [US2] Update `src/tts_bench/intelligibility/scoring.py` to use `normalize_pair`, store `number_readings` on each `SentenceResult`, and store the `NormalizationRecord` (`ruleset_version`, `lexicon_version`, `steps`, `accent_folding`) in the results file; `compare` already refuses a differing `ruleset_version` (T020) (depends on T029)
- [X] T031 [US2] Write `docs/intelligibility.md`: definitions of WER and CER (formulas from FR-002 and FR-003, pooling rule, no cap at 100%, alignment tie-break), the full normalization ruleset step by step with examples from the corpus, the reading-selection rule and why it cannot hide a word error, the accent policy (primary ignores vowel accents, `ñ` kept, accent-sensitive figures secondary), the lexicon, the recognizer settings, and the limitations (WER reflects recognizer plus engine; regional accent; recognizer may correct mispronunciations; one synthesis per sentence so sampling variance is not measured; short sentences weigh heavily); link it from `README.md`

**Checkpoint**: US1 and US2 together: fair scoring on number, currency, date and acronym sentences, documented and verified against the full corpus.

---

## Phase 5: User Story 3 - Identify where errors concentrate (Priority: P2)

**Goal**: show which categories and words an engine gets wrong.

**Independent Test**: a run with known errors lists the exact words and categories involved.

### Tests for User Story 3

- [X] T032 [P] [US3] Write `tests/intelligibility/test_errors_report.py`: with fixed transcripts containing one known substitution, one deletion and one insertion in different sentences, `errors` lists for each sentence S, D, I and the exact words involved (`ref` and `hyp` of each non-match op); `--sentence ID` shows one sentence; `--tag amount_cop` filters; `--worst N` orders by total errors descending with ties broken by sentence id; sentences with zero errors are omitted unless selected by id; the output of `errors` starts with the FR-009 notice
- [X] T033 [P] [US3] Add to `tests/intelligibility/test_files_compare.py` a case that `compare` prints one table per grouping (tags, campaigns) with `n sentences`, reference words and the `low_sample` marker, that groups are listed for every tag in the corpus (SC-003), and that a note states tag groups overlap

### Implementation for User Story 3

- [X] T034 [US3] Extend `src/tts_bench/intelligibility/compare.py` with per-tag and per-campaign tables (columns: group, n sentences, reference words, WER, CER, S, D, I, accent-sensitive WER, `low_sample` flag), keeping the notice at the top and the overlap note under the tag table
- [X] T035 [US3] Implement the `errors` report in `src/tts_bench/intelligibility/compare.py` (`error_report(results, *, sentence=None, tag=None, worst=None) -> str`) and wire the `errors` subcommand in `src/tts_bench/intelligibility/__main__.py`; each entry shows sentence id, campaign, tags, flags, the normalized reference and hypothesis, S/D/I counts and the list of substitutions (`ref → hyp`), deletions and insertions; the report starts with the notice (depends on T034)

**Checkpoint**: all three stories independently functional.

---

## Phase 6: Polish and cross-cutting

- [X] T036 [P] Write `tests/intelligibility/test_offline.py`: with socket creation patched to raise, run `synthesize` (fake engine), `transcribe` (`FakeRecognizer`), `score`, `compare` and `errors`; all succeed (Constitution "Local-first")
- [X] T037 [P] Add an `engine`-marked test `tests/intelligibility/test_recognizer_real.py` (run in `.venv-asr`): transcribe the same short WAV twice with the cache disabled (empty `--cache` directory each time, so the recognizer really runs twice) and assert identical text and the recorded settings equal the settings in T017 (SC-004 determinism of the recognizer); skip with a clear message if `faster-whisper` or weights are absent
- [X] T038 Pin and record the recognizer: download `large-v3` in `.venv-asr`, record the exact checkpoint revision and its license in `RecognizerRecord`, and flag prominently if the license is non-commercial or copyleft (Principle VI); note the outcome in `docs/intelligibility.md`
- [X] T039 Run the real pipeline for `piper`, `phonon` and `pocket_tts` with the same voices used in feature 004 (each engine in its own venv, `transcribe` in `.venv-asr` with identical settings, `score` in `.venv-core`); write results to `results/intelligibility/`, generate `results/intelligibility/comparison.md` with `compare`, and add a short reading of the results to `docs/intelligibility.md` labeling them as measured by this project
- [X] T040 Walk through `quickstart.md` sections 1 to 5, fix any command that does not work as written, and confirm the repository check from feature 003 reports no voice material or `.wav` files staged; do not commit (the maintainer commits)

---

## Dependencies and order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish. US2 depends on US1 (it extends `normalize` and `scoring`); US3 depends on US1 (`compare`) and uses the `ops` stored by US1 scoring.
- Within US1: T014, T015, T017 in parallel; T016 after T014 and T015; T018 after T015 and T017; T019 after T003 to T005; T021 last.
- Within US2: T027 and T028 in parallel, then T029, then T030.
- T038 must precede T039; T039 needs the three engine venvs from feature 001.

## Parallel examples

- Phase 2: T003, T004, T005, T006, T007 together.
- US1 tests: T008 to T013 together; US1 modules: T014, T015, T017, T020 together.
- US2: T023 to T026 together, then T027 and T028 together.

## Implementation strategy

1. **MVP**: Phases 1 to 3. Fixed transcripts and the fake pipeline prove FR-001 to FR-003, FR-005 to FR-010 and SC-001 to SC-004 (with the basic normalizer).
2. **Increment 1**: US2 for fair number, currency, date and acronym handling, which changes the numbers on about a third of the corpus; do not publish real-engine results before it is done.
3. **Increment 2**: US3 diagnosis tables and the `errors` report.
4. **Finish**: Phase 6 real runs for the three engines with one recognizer.

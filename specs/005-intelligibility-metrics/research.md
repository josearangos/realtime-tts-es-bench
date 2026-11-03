# Research: Intelligibility Metrics (WER and CER)

## R1. Stage separation and process model
- **Decision**: four stages joined by files: `synthesize` (engine venv, WAVs + manifest) → `transcribe` (recognizer venv, transcripts) → `score` (any venv, pure) → `compare`/`errors`.
- **Rationale**: the project forces one engine per process and isolates dependencies per engine (Principle VII); the recognizer is one more heavy dependency. Files between stages let `score` be tested with fixed transcripts (FR-010) and re-run without audio (SC-004).
- **Alternatives**: one command doing everything (rejected: would need engine and recognizer dependencies in one environment); reusing the performance run's audio (rejected: feature 004 does not keep audio and runs several repetitions).

## R2. Designated run
- **Decision**: `synthesize` loads the engine, synthesizes each main-corpus sentence once in corpus order with the same voice resolution as feature 004, and saves the WAV at the engine's own sample rate. No warm-up discard, no repetitions; load state is recorded.
- **Rationale**: matches the clarification (one synthesis per sentence per engine). Intelligibility does not depend on timing.
- **Risk**: engines with random sampling give slightly different audio per run, so WER varies between syntheses. The audio hash is stored and SC-004 applies to the same audio; a note in the report says sampling variance across syntheses is not measured.

## R3. Recognizer
- **Decision**: `faster-whisper`, multilingual Whisper checkpoint, `language="es"`, greedy decoding, `temperature=0`, `beam_size=1`, `vad_filter=False`, `condition_on_previous_text=False`, no initial prompt, CPU int8. Identity, checkpoint, library and CTranslate2 versions and every setting are stored. Transcripts are cached by `sha256(audio) + settings hash`.
- **Rationale**: local, runs on Apple Silicon CPU and Linux, near-deterministic with greedy decoding, strong Spanish quality. Greedy is faster and removes beam tie variation.
- **Alternatives**: `openai-whisper` (slower on CPU), `mlx-whisper` (macOS only, breaks portability), a cloud ASR (rejected: local-first), Vosk or wav2vec2 Spanish (considered lower quality; revisit if licensing blocks Whisper).
- **To verify when pinning**: exact checkpoint revision and its license (Principle VI); determinism of repeated runs on the same machine (SC-004), tested with an `engine`-marked test.
- **Known limitation, stated in outputs**: WER reflects recognizer and engine together; Whisper may be weaker on some regional accents and may "correct" mispronunciations toward likely words, hiding errors.

## R4. Normalization ruleset (identical on reference and transcript)
- **Reference text**: `spoken` when present, else `text` (clarified in User Story 2).
- **Steps, in order**: (1) Unicode NFC; (2) lowercase; (3) expand written forms: currency (`$1.847.300` → pesos), times (`3:00`, `4:30`), percent, ordinal-day `1` kept as cardinal, numerals, the lexicon; (4) remove punctuation and symbols (`¿?¡!.,;:"'()-…`); (5) fold accents on `á é í ó ú ü` (not `ñ`) for the primary figure, skipped for the accent-sensitive secondary figure; (6) collapse whitespace.
- **Numerals**: thousands separators `.`, decimal `,`. A digit run is read as a cardinal ("cuatro mil ochocientos veintiuno") or digit by digit ("cuatro ocho dos uno"; leading zeros and groups like "0045 8832" read per digit). When both are plausible the candidate with the smaller word edit distance to the reference is chosen and the choice is stored per sentence. Corpus evidence: account numbers are read per digit with a comma between groups; amounts and days are cardinals; "primero" is used for day 1 (lexicon/ordinal rule).
- **Why reference-guided choice**: the recognizer's choice of "4821" versus words is formatting, not intelligibility; selecting the closer reading is applied identically to every engine and cannot reduce a real word error (a wrong word still differs under both readings).
- **Safeguard**: `test_corpus_normalization` asserts that `normalize_pair(spoken, text)` returns identical reference and transcript strings for every main and cloning sentence that has `spoken`, and that `normalize(text)` leaves sentences without `spoken` unchanged beyond the basic steps, so the written-form rules provably cover the corpus without any recognizer.
- **Alternatives**: `num2words` or a text-normalization toolkit (rejected: extra dependency and unversioned behavior; the needed range is small); stripping all digits and compare only letters (rejected: hides number errors).

## R5. Alignment and error counting
- **Decision**: Levenshtein alignment with unit costs on word tokens (WER) and on characters of the normalized string including single spaces (CER). Backtrace tie-break is fixed (substitution, then deletion, then insertion) so counts S, D, I are reproducible. `rate = (S + D + I) / reference_length`. Rates can exceed 100% because of insertions; they are not capped.
- **Pooling**: per-category and overall rates are `sum(errors) / sum(reference units)`, not the mean of per-sentence rates. Per-sentence rates are also reported.
- **Zero-length reference**: rate undefined; flagged and excluded from rates, counted in `n`.

## R6. Silent, empty and failed audio
- **Decision**: a WAV is silent if it has zero samples or its peak absolute amplitude is below 1e-4 (float scale). `synthesize` marks `status: failed` (exception or no audio) or `silent`; `transcribe` skips silent audio. `score` counts `failed`, `silent` and missing audio as a full failure: every reference word a deletion (WER 100%), every reference character a deletion (CER 100%), `flag` set. A non-silent audio with an empty transcript is scored normally (100% deletions) and flagged `empty_transcript`.
- **Reliability**: results are stamped `reliable: false` when more than 10% of sentences are flagged (same rule as feature 004).

## R7. Per-category grouping
- **Decision**: groups are feature tags, campaigns, overall; also `probes` is stored per sentence for filtering but not summarized by default. A sentence in several tag groups is counted in each; overlap is noted in the report. Sentences with no tags appear in `untagged`.
- **Rationale**: SC-003 asks for every category in the corpus; tags are the categories the corpus defines (names, numbers, acronyms, amounts, dates).

## R8. Comparison rules
- **Decision**: `compare` refuses when recognizer identity, version, or any setting differs (exit 3, naming the field), and when corpus hash, subset, or `limit` differ. Hardware differences do not block (WER is not a timing metric) but are listed. Every output includes the intelligibility-not-naturalness notice (FR-009) and the recognizer-plus-engine caveat.

## R9. Metadata about accent
- **Decision**: the results store the voice's `spanish_variant` from the descriptor and a fixed note that recognizer accuracy varies with regional accent.

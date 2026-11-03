# Data Model: Intelligibility Metrics (WER and CER)

## Audio Manifest (`output/intelligibility/<engine>-<voice>/manifest.json`, not tracked)

| Field | Notes |
|-------|-------|
| schema_version | integer |
| engine | name, engine_version, model_id, spanish_variant, streaming_granularity, voice {name, kind, checksum or null} |
| corpus | corpus_version, corpus_hash, subset, limit |
| command, environment | invocation and environment, as in the results file |
| items[] | {sentence_id, file, status, error, sample_rate, duration_s, sha256} |

`status`: `ok` / `failed` (exception) / `silent` (zero samples or peak below 1e-4). `file` is null when `failed`.

## Transcript (one audio)

| Field | Notes |
|-------|-------|
| sentence_id | corpus id |
| audio_sha256 | links to manifest item; null when no audio |
| status | `ok` / `skipped_silent` / `skipped_failed` |
| text | recognizer output, raw (not normalized); empty string allowed |
| language | forced `es` |

## Transcripts File (`results/intelligibility/<engine>-transcripts-<ts>.json`, tracked)

`{ schema_version, recognizer, engine, corpus, manifest_sha256, command, environment, transcripts[] }`

## Recognizer Record

| Field | Notes |
|-------|-------|
| name | e.g. `faster-whisper` |
| checkpoint | model name and revision |
| license | recorded, flagged if non-commercial |
| library_versions | recognizer library and runtime |
| settings | decoding and input settings; `settings_hash` over them |
| device | cpu / compute type |
| accent_note | fixed text on regional accent |

## Normalization Ruleset

`{ ruleset_version, steps[], lexicon_version, accent_folding }`. Versioned; a change bumps `ruleset_version`, and `compare` refuses to mix versions. Documented in `docs/intelligibility.md`.

## Error Breakdown (per sentence and level)

| Field | Notes |
|-------|-------|
| level | `word` or `char` |
| substitutions, deletions, insertions | integers |
| reference_length | words or characters after normalization |
| rate | (S+D+I)/reference_length, or null when length is 0 |
| ops[] | word level only: {op, ref, hyp} entries in order, for diagnosis |

## Sentence Result

| Field | Notes |
|-------|-------|
| sentence_id, campaign, tags[], probes | copied from corpus |
| reference | normalized reference (primary ruleset) |
| hypothesis | normalized transcript (after reading selection) |
| number_readings | per numeral token: chosen reading (`cardinal`/`digits`) or empty |
| primary | {word: Error Breakdown, char: Error Breakdown} (accents folded) |
| accent_sensitive | {word, char} (accents kept) |
| flags[] | `silent_audio`, `synthesis_failed`, `empty_transcript`, `empty_reference` |
| counted_as_failure | true for silent, failed |

## Group Summary

| Field | Notes |
|-------|-------|
| group | `overall`, `tag:<name>`, `campaign:<name>`, `untagged` |
| n_sentences, n_flagged, reference_words, reference_chars | sample sizes |
| word / char | pooled S, D, I and rate, for primary and accent-sensitive |
| low_sample | true when n_sentences < 10 |

## Results File (`results/intelligibility/<engine>-<ts>.json`, tracked)

`{ schema_version, notice, recognizer, normalization, engine, corpus, environment, command, summary {reliable, groups[]}, sentences[] }`. The `notice` carries the text required by FR-009 and the recognizer-plus-engine caveat. See [contracts/results-file.md](contracts/results-file.md).

## Relationships

Manifest 1—N items; Transcripts File 1—1 Recognizer Record, 1—N Transcripts; Results File 1—1 Recognizer Record and Normalization Ruleset, 1—N Sentence Results, 1—N Group Summaries. `compare` reads many Results Files.

## State

`synthesize` → manifest + WAVs; `transcribe` → transcripts (cached by audio hash and settings hash); `score` → results; each stage can be re-run alone. A failure inside one sentence is recorded and the stage continues; a failure to load the engine or recognizer aborts with its install hint and writes no file.

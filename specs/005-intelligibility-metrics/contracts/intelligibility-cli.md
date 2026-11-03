# Contract: intelligibility CLI and library

## CLI

```
python -m tts_bench.intelligibility synthesize ENGINE
    [--voice NAME] [--voices-dir cloned_voices]
    [--limit N]                          first N sentences only (stored)
    [--out output/intelligibility]
python -m tts_bench.intelligibility transcribe AUDIO_DIR
    [--model large-v3|fake] [--script FILE.json] [--device cpu] [--compute-type int8]
    [--cache DIR] [--out results/intelligibility]
python -m tts_bench.intelligibility score TRANSCRIPTS_FILE [--out results/intelligibility]
python -m tts_bench.intelligibility compare RESULTS_FILE... [--out FILE.md]
python -m tts_bench.intelligibility errors RESULTS_FILE [--sentence ID] [--tag TAG] [--worst N]
```

- `synthesize` runs one engine in one process, only the `main` subset. `ENGINE=fake` is available for tests. Exit 0 even if some sentences failed (they are recorded); exit 2 if the engine cannot load.
- `synthesize` writes to `<out>/<engine>-<voice>/` and prints that directory; `transcribe` writes `<out>/<engine>-transcripts-<UTC timestamp>.json` and prints its path; `score` writes `<out>/<engine>-<UTC timestamp>.json`.
- `--model fake` selects `FakeRecognizer`, which returns each sentence's expected reference text (WER 0); `--script FILE.json` maps sentence ids to scripted texts that replace it. Used for tests and the quickstart, never for reported results.
- `transcribe` uses the same recognizer settings for every invocation unless flags change them; the settings are stored and `compare` refuses mismatches. Exit 2 if the recognizer or its weights are missing (with an install hint).
- `score` needs no engine and no recognizer. Exit 1 on a missing or malformed transcripts file.
- `compare` prints Markdown tables: overall, per tag, per campaign, with columns engine, voice, WER, CER, S, D, I, accent-sensitive WER, n sentences, flagged, reliable. Exit 3 on a refused merge, naming the differing field.
- `errors` lists per-sentence substitutions, deletions and insertions with the words involved, and the worst sentences by errors.
- Every printed report starts with the notice: "WER and CER measure intelligibility as heard by one recognizer, not naturalness; results reflect the recognizer and the engine together."

## Library

```python
normalize(text, *, fold_accents=True) -> str                          # pure, one text; numerals read as cardinals
normalize_pair(reference, transcript, *, fold_accents=True) -> (str, str, list)   # pure; picks the numeral reading closest to the reference, returns the readings
word_error_rate(reference, hypothesis) -> ErrorBreakdown               # pure, normalized inputs
char_error_rate(reference, hypothesis) -> ErrorBreakdown               # pure
score_transcripts(transcripts, corpus, *, recognizer, engine) -> ResultsFile   # pure
compare_results(files) -> str                                          # Markdown
```

All pure functions take plain strings and lists, so they run with no engine and no recognizer (FR-010).

## Errors

| Situation | Behaviour |
|-----------|-----------|
| Engine not installed / weights missing | `synthesize` exit 2 with the adapter's hint; no manifest |
| Sentence fails to synthesize | recorded `failed`; scored as full failure |
| Silent or empty audio | recorded `silent`; recognizer not run; full failure |
| Recognizer or weights missing | `transcribe` exit 2 with hint; no file |
| Audio missing for a manifest item | transcript `skipped_failed`; full failure |
| `compare` inputs differ in recognizer, settings, ruleset version, corpus hash, subset or limit | refuse (exit 3) naming the field |
| Unknown `schema_version` | refuse with a message |

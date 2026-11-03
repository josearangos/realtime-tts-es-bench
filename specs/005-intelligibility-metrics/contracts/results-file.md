# Contract: results file

JSON, UTF-8, one file per engine per scoring run, `results/intelligibility/<engine>-<UTC timestamp>.json`.

```json
{
  "schema_version": 1,
  "notice": "WER and CER measure intelligibility ... not naturalness ...",
  "recognizer": { "name": "...", "checkpoint": "...", "license": "...", "library_versions": {}, "settings": {}, "settings_hash": "...", "device": "cpu", "accent_note": "..." },
  "normalization": { "ruleset_version": "1", "lexicon_version": "1", "steps": [] },
  "engine": { "name": "...", "engine_version": "...", "model_id": "...", "spanish_variant": "...", "streaming_granularity": "...", "voice": { "name": "...", "kind": "...", "checksum": null } },
  "corpus": { "corpus_version": "...", "corpus_hash": "...", "subset": "main", "limit": null },
  "environment": { "python": "...", "os_name": "...", "os_release": "...", "tts_bench_version": "...", "git_commit": "..." },
  "command": "python -m tts_bench.intelligibility score ...",
  "summary": { "reliable": true, "groups": [ { "group": "overall", "n_sentences": 123, "n_flagged": 0, "reference_words": 0, "reference_chars": 0, "primary": { "word": {"S":0,"D":0,"I":0,"rate":0.0}, "char": {"S":0,"D":0,"I":0,"rate":0.0} }, "accent_sensitive": { "word": {}, "char": {} }, "low_sample": false } ] },
  "sentences": [ { "sentence_id": "COB-001", "campaign": "collections", "tags": [], "probes": "name", "reference": "...", "hypothesis": "...", "number_readings": [], "primary": {}, "accent_sensitive": {}, "flags": [], "counted_as_failure": false } ]
}
```

## Definitions (also in `docs/intelligibility.md`)

- **Reference**: `spoken` if present, else `text`, normalized with the ruleset.
- **WER** = (S + D + I) / number of reference words; **CER** = same on characters of the normalized string (single spaces counted). Not capped at 100%.
- **Overall and group rates**: pooled counts divided by pooled reference length.
- **Full failure**: all reference units counted as deletions, flagged.
- **Alignment tie-break**: substitution, then deletion, then insertion.

## Rules

- No absolute paths, hostnames or user names are stored; paths are relative to the repository root or `<abs-path>`.
- `rate` is `null` when reference length is 0; such sentences are flagged `empty_reference` and excluded from pooled rates but counted in `n_sentences`.
- `reliable` is false when more than 10% of sentences are flagged.
- Re-running `score` on the same transcripts file yields a byte-identical `summary` and `sentences` (timestamps live only in the file name and `environment`).

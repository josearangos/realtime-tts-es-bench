# Contract: results file

JSON, UTF-8, one file per engine per scoring run, `results/speaker/<engine>-<UTC timestamp>.json`. Tracked.

```json
{
  "schema_version": 1,
  "notice": "Speaker similarity scores ... not a substitute for human judgment ...",
  "embedder": { "name": "...", "checkpoint": "...", "license": "...", "library_versions": {}, "settings": {}, "settings_hash": "...", "device": "cpu", "limitation_note": "..." },
  "reference_quality": { "recording_id": "...", "duration_s": 0.0, "speech_seconds": 0.0, "snr_estimate_db": 0.0, "accent": "es-CO", "warnings": [] },
  "engine": { "name": "...", "engine_version": "...", "model_id": "...", "supports_cloning": true, "voice": { "name": "...", "kind": "..." } },
  "corpus": { "corpus_version": "...", "corpus_hash": "...", "subset": "cloning", "limit": null },
  "environment": {}, "command": "python -m tts_bench.speaker score ...",
  "summary": { "status": "scored", "n_sentences": 21, "n_scored": 21, "n_flagged": 0,
               "similarity": { "mean": 0.0, "sd": 0.0, "min": 0.0, "max": 0.0 }, "warnings": [] },
  "sentences": [ { "sentence_id": "CLO-001", "campaign": "...", "tags": [], "similarity": 0.0, "duration_s": 0.0, "flags": [] } ],
  "consistency": { "repetitions": 5, "duration": {}, "similarity": {}, "per_sentence": [] },
  "eer": { "available": true, "eer": 0.0, "threshold": 0.0, "n_same": 0, "n_different": 0, "high_eer_warning": false, "separation": 0.0, "gate_passed": true, "reason": null, "pair_construction": "..." }
}
```

## Definitions (also in `docs/speaker-similarity.md`)

- **Similarity**: cosine of reference and clip embeddings, designated run (repetition 1) only.
- **CV**: sample SD (n−1) / mean over the N repetitions of one sentence; per-engine figure is the median over sentences (mean shown beside it); declined when |mean| < 0.05.
- **EER**: threshold where false-accept and false-reject rates cross, linear interpolation, pooled across cloning engines.
- **Separation and gate**: separation = mean same-speaker score minus mean different-speaker score; the Spanish gate passes when EER ≤ 10% and separation ≥ 0.20.
- **Short audio**: shorter than 3.0 s.

## Rules

- No vectors, audio, absolute paths, hostnames or user names are stored.
- A non-cloning engine appears only as `{ "summary": { "status": "not_applicable" } }` in `compare`, never as a result file with scores.
- Re-running `score` on the same embeddings file yields byte-identical `summary`, `sentences`, `consistency` and `eer` (SC-005).

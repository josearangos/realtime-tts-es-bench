# Contract: Export (consumed by the results report)

Output dir `results/human/` (default). No audio, no emails, no reference recordings.

- `annotations.jsonl` — one row per annotation:
  `batch_id, project, item_id, annotator_id, role, repeat_of, engine, voice, accent, cloned, sentence_id, corpus_version, scale_hash, ls_version, ratings{naturalidad,pronunciacion,prosodia}` (mos) | `cmos` with `engine_a, voice_a, engine_b, voice_b` (cmos) | `sim` (sim), `lead_time_s, created_at`.
- `annotations.csv` — flat equivalent.
- `quality.json` — per annotator `QualityReport` ([data-model.md](../data-model.md)) plus thresholds used.
- `MANIFEST.json` — batch config hash, seed, counts, loudness settings, row count, sha256 of files, Python/numpy/OS and Label Studio versions, exact export command.

Rules: `annotator_id` comes only from user emails of the form `aNN@eval.invalid`; any other form aborts the export (emails are never written). every row has non-null engine(s), voice(s), sentence_id, corpus_version (SC-006); QC rows are included with `role` so analysis can exclude them; no exclusion is applied by the export. Rows are sorted by `(project, item_id, annotator_id)` so exports are byte-comparable (SC-003).

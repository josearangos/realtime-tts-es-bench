# Data Model: Label Studio Human Evaluation

## BatchConfig (`evaluation/batch.toml`)
`seed:int`, `sentences_per_condition:int`, `repeat_rate:float(0-0.3)`, `attention_rate:float(0-0.2)`, `loudness_rms_dbfs:-23`, `peak_limit_dbfs:-1`, `conditions:[{engine, voice}]` (empty = all discovered), `cmos_pairs: all|[[condA,condB]]`, `sim_conditions: cloning only`, `quality_thresholds{repeat_within_1_min:0.7, max_failed_checks:1}`.

## SourceClip
`engine`, `voice`, `accent`, `cloned:bool`, `sentence_id`, `corpus_subset`, `wav_path`, `sample_rate`. Validation: sentence_id exists in the corpus; WAV mono PCM readable.

## Batch (`output/evaluation/batch.json`)
`batch_id`, `created`, `seed`, `corpus_version`, `corpus_sha256`, `scale_hash`, `loudness{...}`, `label_studio_version`, `counts{mos,cmos,sim,repeats,attention}`, `config_sha256`. Immutable once created.

## BlindMapping row (`output/evaluation/private/mapping.jsonl`, never mounted)
| Field | Notes |
|---|---|
| `item_id` | opaque 12-hex; primary key |
| `project` | `mos` \| `cmos` \| `sim` |
| `role` | `test` \| `repeat` \| `attention_instructed` \| `attention_degraded` |
| `repeat_of` | item_id of the original, if role=repeat |
| `engine`, `voice`, `accent`, `cloned` | for pair tasks: `a{...}`, `b{...}` blocks |
| `position` | CMOS only: which condition is shown as A and which as B |
| `sentence_id`, `corpus_version` | from corpus |
| `expected` | attention checks: allowed answers |
| `served_files` | opaque wav names (A/B/reference) |

Relationships: repeat→original (1:1); every served file belongs to exactly one item.

## Task (annotator-visible `data`)
See [contracts/task-schema.md](contracts/task-schema.md): `item_id`, `audio` (or `audio_a`/`audio_b`, `reference`), `text` (the sentence's spoken text, Spanish), `instruction_hint`. Nothing else.

## Annotation (from Label Studio)
`task_id`, `item_id`, `annotator_id` (pseudonym), `ratings{criterion:int}` or `cmos:int` or `sim:int`, `lead_time_s`, `created_at`.

## ExportRow
Annotation joined with mapping; see [contracts/export-format.md](contracts/export-format.md).

## QualityReport
Per annotator: `n_annotations`, `repeat_pairs`, `repeat_mad`, `repeat_within_1`, `attention_total`, `attention_failed`, `flagged:bool`, `reasons[]`.

## VersionMarker (`output/evaluation/ls-version`)
Text file with the Label Studio version that created the data volume; compared with `LS_VERSION` by `eval-up` (upgrade guard).

## Glossary
`item` = one mapping row = one Label Studio task (same `item_id`); `condition` = one engine+voice pair.

## BackupArchive
`backups/evaluation/<UTC>.tar.gz` containing `ls-data/` and `evaluation-output/` (served, private, batch.json) plus `MANIFEST.json` (batch_id, LS version, sha256 of members).

## State transitions
`unprovisioned → prepared (batch.json) → provisioned (projects+tasks) → collecting → exported`. `reset` returns to `unprovisioned`. A new batch needs explicit `eval-new-batch` (archives the old batch directory first).

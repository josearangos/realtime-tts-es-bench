# Human evaluation protocol

Complements the deterministic metrics (intelligibility, speaker similarity, latency) with listener judgements of **naturalidad, pronunciación, prosodia**, A/B preference (**CMOS**) and cloned-voice **similarity (SIM)**. Human scores are reported separately from the automatic metrics (Constitution IV). Operations are in [evaluation/README.md](../evaluation/README.md).

## Protocol

- **Annotators**: native Spanish speakers. The organizer attests this; the tool does not enforce it. 2 to 5 annotators, each completes whole projects.
- **Setup**: headphones, quiet room, listen to each audio at least once completely. The instructions page in each project says so in Spanish.
- **Scales** (frozen, Spanish anchors in `src/tts_bench/evaluation/scales.py`): MOS 1–5 per criterion, CMOS −3…+3 (B vs A), SIM 1–5. A SHA-256 of the scale text is stored in `batch.json`, in every export row, and in each project's description. Any wording change gives a new hash and blocks provisioning until a new batch is started on purpose.
- **Halo effect**: the three MOS criteria are rated on the same audio in one project, which saves listening but lets one impression color all three. Distinct anchors reduce this; read the three scores with that caveat.
- **Blindness**: tasks carry only an opaque id, opaque audio file names and the sentence text. Task order is random (seeded, plus Label Studio's random sampling) and A/B positions are balanced per pair. Loudness is equalized (RMS −23 dBFS).
- **Same sentences** for every condition inside a comparison group (a corpus subset), stratified by campaign.

## Quality control

About 10 % of items are **repeats** (same audio, new id) and about 5 % **attention checks**: instructed responses over a generated tone ("marque 4 estrellas…") and degraded anchors (a real clip with noise at 0 dB SNR, expected ≤ 2). They look like normal tasks. `quality.json` reports per annotator: repeat pairs, mean absolute difference, share within ±1, failed checks, and a `flagged` verdict with reasons (defaults in `batch.toml`: at least 70 % of repeats within ±1, at most 1 failed check). **Nothing is excluded automatically.** Exclusion is an analysis decision: export rows keep `role` so you can filter QC rows and flagged annotators and say so in the report.

## Reading the export

`make eval-export` writes to `results/human/`:

- `annotations.jsonl` / `.csv`: one row per annotation with batch id, project, `item_id`, pseudonymous `annotator_id` (`a01`), `role` (`test`, `repeat`, `attention_*`), engine/voice/accent/cloned (CMOS: `engine_a/voice_a/engine_b/voice_b`), sentence id, corpus version, scale hash, Label Studio version, ratings, lead time.
- `quality.json`, and `MANIFEST.json` (config hash, seed, counts, loudness, file hashes, Python/numpy/OS/Label Studio versions, command).

Rows are sorted by `(project, item_id, annotator_id)`, so two exports of the same state are byte-identical. No emails, audio or reference recordings are written. Use `role == "test"` for scores.

## Privacy, consent and licensing (Constitution VI)

- Annotator accounts are `aNN@eval.invalid` with no names; the export aborts on any other email form (it names the user id, never the email).
- Audio, the blind mapping, backups and `.env` are git-ignored. Reference recordings appear only inside the local SIM project and never in exports.
- Cloned voices are used under the owner's standing consent. If consent is withdrawn, `make eval-purge-voice VOICE=<name>` deletes that voice's served audio (including SIM references), its tasks and its mapping rows, and logs the purge in `output/evaluation/private/purges.jsonl`. Re-export and re-analyse afterwards.

## Compliance notes

- **IV**: blind, randomized, frozen scales; human results never merged with automatic scores.
- **VI**: pseudonymous ids, purge command, nothing sensitive tracked.
- All annotator-facing text is Spanish (Constitution II); only Label Studio Community Edition is used.

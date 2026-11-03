# Data Model: Speaker Similarity and Consistency Metrics

## Audio Manifest (`output/speaker/<engine>-<voice>/manifest.json`, not tracked)

| Field | Notes |
|-------|-------|
| schema_version | integer |
| engine | name, engine_version, model_id, spanish_variant, supports_cloning, voice {name, kind, recording_id, accent_label} |
| corpus | corpus_version, corpus_hash, subset `cloning`, limit |
| repetitions | N and the designated repetition (1) |
| reference | Reference Quality (below) |
| command, environment | invocation and environment |
| items[] | {sentence_id, repetition, file, status, error, sample_rate, duration_s, sha256} |

`status`: `ok` / `failed` / `silent` (zero samples or peak below 1e-4).

## Reference Quality (FR-012)

`{ recording_id, duration_s, speech_seconds, snr_estimate_db, accent, warnings[] }`, copied from the voice library entry. No path.

## Speaker Embedding (`output/speaker/<engine>-<voice>/embeddings.json`, not tracked)

| Field | Notes |
|-------|-------|
| schema_version, embedder | Embedder Record |
| reference | {audio_sha256, vector} |
| clips[] | {sentence_id, repetition, audio_sha256, duration_s, vector, status} |
| extras[] | {label, role (`other_voice_reference`), audio_sha256, vector} for EER pairs |

## Embedder Record (FR-002, FR-009)

| Field | Notes |
|-------|-------|
| name | e.g. `speechbrain-ecapa` |
| checkpoint | model id and pinned revision |
| license | recorded; flagged if non-commercial or data-restricted |
| library_versions | speechbrain, torch |
| settings | sample rate, channels, normalization, dimension; `settings_hash` over them |
| device | cpu |
| limitation_note | fixed text on language, noise, prosody |

## Similarity Score (per sentence, designated run)

| Field | Notes |
|-------|-------|
| sentence_id, campaign, tags[] | from corpus |
| similarity | cosine, or null when excluded |
| duration_s | of the scored clip |
| flags[] | `short_audio`, `silent_audio`, `synthesis_failed` |

## Engine Summary

| Field | Notes |
|-------|-------|
| status | `scored` or `not_applicable` (non-cloning engine) |
| n_sentences, n_scored, n_flagged | sample sizes |
| similarity | {mean, sd, min, max} over scored sentences |
| consistency | Consistency Record |
| warnings[] | short audio count, unreliable-CV notes |

## Consistency Record (per engine, from all repetitions)

| Field | Notes |
|-------|-------|
| repetitions | N |
| duration | {cv_median, cv_mean, n_sentences_valid, n_declined, n_unavailable} |
| similarity | same structure |
| per_sentence[] | {sentence_id, n, duration_cv or null, similarity_cv or null, reason (`near_zero_mean` / `fewer_than_two`) or null} |

## EER Record (optional, once per comparison)

`{ eer, threshold, n_same, n_different, high_eer_warning, separation, gate_passed, available, reason, pair_construction }`. `separation` = mean same-speaker score minus mean different-speaker score; `gate_passed` is true when "EER ≤ 10% and separation ≥ 0.20" (Spanish coherence gate). `available` false when fewer than 2 pairs of either kind.

## Results File (`results/speaker/<engine>-<ts>.json`, tracked)

`{ schema_version, notice, embedder, reference_quality, engine, corpus, environment, command, summary (Engine Summary), sentences[], consistency, eer }`. `notice` carries the FR-008 text. See [contracts/results-file.md](contracts/results-file.md). Contains no vectors, no audio, no paths.

## Validation rules

- All results compared together share `embedder.name`, `checkpoint` and `settings_hash`, `corpus_hash` and the reference's `recording_id`; otherwise refused.
- Cosine similarity requires equal vector length and non-zero norm; a zero vector is a failure flag, not a score.

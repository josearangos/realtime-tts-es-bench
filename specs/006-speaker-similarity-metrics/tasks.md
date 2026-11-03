---

description: "Task list for Speaker Similarity and Consistency Metrics"
---

# Tasks: Speaker Similarity and Consistency Metrics

**Input**: Design documents from `/specs/006-speaker-similarity-metrics/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/speaker-cli.md, contracts/results-file.md, quickstart.md

**Tests**: Included. Constitution Principle VIII and FR-010 require computation to be testable with fixed embeddings and no model weights. All tests use fixed vectors, `FakeEmbedder`, the fake engine and synthetic WAV files: no weights, no network. Only tasks marked `engine` need the real embedding model. Tests never use English text; any sentence comes from the Spanish corpus (Constitution II).

**Organization**: Grouped by user story. Paths follow plan.md (`src/tts_bench/speaker/`, `tests/speaker/`). Foundational holds pure similarity, data types, the embedder protocol with its fake, and the fake engine extensions. US1 delivers the pipeline (synthesize, embed, score, compare) with per-sentence and per-engine similarity, reference quality, short-audio warnings, non-cloning exclusion and the same-model guard. US2 adds the coefficient of variation across repetitions. US3 adds the EER check, which the Spanish coherence gate (plan decision 8) makes required for the first real run.

No task commits anything: the maintainer makes all commits.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1 (similarity to the reference), US2 (consistency), US3 (EER)

---

## Phase 1: Setup

- [X] T001 Create the package `src/tts_bench/speaker/__init__.py` (empty for now), the test package `tests/speaker/__init__.py`, and `results/speaker/.gitkeep`
- [X] T002 Add `output/speaker/` to `.gitignore` under the existing intelligibility entry, with the comment "speaker embeddings, audio and manifests are voice-derived data and never committed (Constitution Principle VI)"; confirm with `git check-ignore -v output/speaker/x/embeddings.json` and `git check-ignore -v output/speaker/x/a.wav` that both ARE ignored, and with `git check-ignore -v results/speaker/x.json` that results files are NOT ignored
- [X] T003 [P] Add the optional dependency group `speaker = ["speechbrain", "torchaudio"]` to `pyproject.toml` (not in core `dependencies`); document in `README.md` how to create `.venv-spk` with `pip install -e ".[speaker]"`

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: pure similarity, data types, embedder protocol and fake, fake-engine extensions, test fixtures

- [X] T004 [P] Implement `src/tts_bench/speaker/similarity.py`: `cosine_similarity(a, b) -> float` over numpy vectors, range -1 to 1; raise `ValueError` on different lengths; a zero-norm vector raises `ZeroNormError` (a failure flag for the caller, never a score; data-model "Cosine similarity requires equal vector length and non-zero norm"). Pure, no I/O
- [X] T005 [P] Implement `src/tts_bench/speaker/model.py` as frozen dataclasses with `to_dict()` / `from_dict()` per data-model.md: `ReferenceQuality`, `ManifestItem`, `Manifest`, `EmbedderRecord`, `ClipEmbedding`, `EmbeddingsFile`, `SimilarityScore`, `EngineSummary`, `ConsistencyRecord`, `EERRecord`, `ResultsFile`. Quote constraints verbatim: manifest `status` is one of `ok` / `failed` / `silent`; summary `status` is `scored` or `not_applicable`; `flags` values are `short_audio`, `silent_audio`, `synthesis_failed`; CV `reason` is `near_zero_mean` / `fewer_than_two` or null; `subset` is `cloning`; every file carries `schema_version` (integer, 1); `ResultsFile` has no field able to hold a vector, an audio path or an absolute path (Principle VI)
- [X] T006 [P] Implement `src/tts_bench/speaker/embedder.py`: `Embedder` protocol (`record() -> EmbedderRecord`, `embed(samples, sample_rate) -> np.ndarray`), `FakeEmbedder` (returns a scripted vector keyed by audio sha256 or, by default, a deterministic vector derived from the dominant tone frequency of the clip so different fixtures give different vectors) and `SpeechBrainEmbedder` skeleton that imports `speechbrain` lazily inside `__init__` and raises a `TTSBenchError` with the install hint when missing (research R3). The real embedding body is implemented in T031
- [X] T007 [P] Implement `src/tts_bench/speaker/files.py`: `sha256_file`, `canonical_json`, `utc_stamp`, `environment_block`, `sanitized_command` imported from `tts_bench.intelligibility.files` (do not copy); `write_manifest` / `read_manifest`, `write_embeddings` / `read_embeddings`, `write_results` / `read_results` with `schema_version` check (unknown version refused with a message), UTF-8 JSON, no absolute paths stored
- [X] T008 [P] Extend `src/tts_bench/adapters/fake.py` (keeping existing behaviour and tests): add constructor params `supports_cloning: bool = False` (written into the descriptor) and `audio_seconds_sequence: tuple[float, ...] | None = None` (the n-th synthesis call uses `audio_seconds_sequence[n % len]`, so repetitions have controlled, known durations); add a deterministic tone frequency per call via `tone_hz_sequence: tuple[float, ...] | None = None`. Run `.venv-core/bin/python -m pytest tests/unit tests/contract -q` to confirm nothing regressed
- [X] T009 [P] Create `tests/speaker/conftest.py` with: a `cloning_corpus` fixture (`load_corpus(subset="cloning")`, 21 sentences), `write_wav` and `tone_audio(seconds, rate, hz)` / `silent_audio` helpers (numpy and standard-library `wave`), a `fixed_embeddings(mapping)` helper that builds an `EmbeddingsFile` with a valid `EmbedderRecord`, and a `fake_voice_library(tmp_path)` fixture that registers a cloned voice with a synthetic reference recording so `ReferenceQuality` can be read without real voices
- [X] T010 [P] Write `tests/speaker/test_similarity.py` (SC-001): identical vectors give similarity within 0.01 of 1.0 (in fact exactly 1.0 for identical input); orthogonal vectors give 0.0; opposite vectors give -1.0; scaling a vector does not change the result; vectors of different length raise `ValueError`; a zero vector raises `ZeroNormError`; the same call twice gives the identical float

**Checkpoint**: foundation ready, user stories can start

---

## Phase 3: User Story 1 - Score how close a cloned voice is to the reference (Priority: P1) 🎯 MVP

**Goal**: for each cloning-capable engine, synthesize the cloning subset with the cloned voice, embed reference and clips with one fixed model, and report cosine similarity per sentence (designated run) and averaged per engine, refusing mixed embedding models.

**Independent Test**: identical audio scores within 0.01 of the maximum; clearly different speakers score at least 0.20 lower; Piper is not applicable; the same-model guard refuses mixed models; the notice appears in every report.

### Tests for User Story 1

- [X] T011 [P] [US1] Write `tests/speaker/test_scoring.py` with fixed embeddings and no model: per-sentence similarity equals the hand-computed cosine of reference and designated-run clip (FR-001, FR-003); only repetition 1 feeds the headline similarity and other repetitions change nothing in it (clarification 2026-11-03); the engine mean, sd, min and max match hand-calculated values over a known set; a fixture with identical vectors scores at least 0.99 and a fixture with a different-speaker vector scores at least 0.20 lower (SC-001); sample sizes `n_sentences`, `n_scored`, `n_flagged` are correct
- [X] T012 [P] [US1] Write `tests/speaker/test_exclusions.py`: an engine with `supports_cloning=False` yields `status: "not_applicable"` with no similarity and no penalty (FR-006) and `synthesize` for it writes nothing and prints "not applicable: <engine> does not clone voices"; a silent clip and a failed synthesis are flagged (`silent_audio`, `synthesis_failed`), excluded from the mean and counted in `n_flagged`; a clip shorter than 3.0 s is flagged `short_audio`, still scored, still in the mean, and produces a warning with the count (FR-007); a clip of exactly 3.0 s is not flagged; a zero-norm embedding is flagged as a failure and gets no score
- [X] T013 [P] [US1] Write `tests/speaker/test_pipeline_fake.py`: using `FakeAdapter(supports_cloning=True)` and `FakeEmbedder`, run `synthesize` on 5 cloning sentences with 3 repetitions into `tmp_path`, `embed`, and `score`; assert the manifest holds 15 items with statuses, repetition 1 is marked designated, the results file records the embedder name, checkpoint, library versions and `settings_hash` (FR-009), the reference quality from the library entry (duration, speech seconds, SNR estimate, accent, warnings; FR-012), the engine block, the corpus stamp with `subset` `cloning`, the audio language `es`, the `command` and `environment` blocks, and the FR-008 notice text
- [X] T014 [P] [US1] Write `tests/speaker/test_files_compare.py` (compare part): `compare` over two results files with the same embedder name, checkpoint and `settings_hash`, `corpus_hash` and reference `recording_id` succeeds (SC-002); a differing embedder name, checkpoint, any `settings` value, `corpus_hash` or reference refuses and the CLI exits 3 naming the differing field; differing hardware does NOT block; an unknown `schema_version` is refused; the printed report starts with the FR-008 notice "Speaker similarity scores come from one embedding model and are not a substitute for human judgment; a score near 1 does not guarantee the voice sounds identical." (SC-004); a non-cloning engine appears as a `not applicable` row and is not averaged with others
- [X] T015 [P] [US1] Write `tests/speaker/test_privacy.py` (Principle VI): a results file produced from a fixture run contains no vector values, no `.wav` path, no absolute path, no host or user name, and no `reference` file path; `git check-ignore` semantics are covered by checking that `output/speaker/` and `*.wav` match the repository `.gitignore` patterns, and that no file under `results/speaker/` has an extension `.wav`, `.safetensors`, `.npy` or `.pt`
- [X] T016 [P] [US1] Write `tests/speaker/test_determinism.py` (SC-005): `score` run twice on the same embeddings file yields byte-identical `summary`, `sentences`, `consistency` and `eer` JSON (timestamps only in file name and `environment`); an embedding cache hit (same audio sha256 and `settings_hash`) returns the stored vector without calling the embedder and a different `settings_hash` misses the cache

### Implementation for User Story 1

- [X] T017 [US1] Implement `src/tts_bench/speaker/synth.py`: `synthesize_cloning(adapter, corpus, voice, out_dir, *, repetitions=5, limit=None, voice_info, reference_quality, command)`: refuse early (return a `not_applicable` marker, write nothing) when `adapter.descriptor.supports_cloning` is false; load the engine once, for each repetition in order and each cloning sentence in corpus order synthesize `s.text` once, write `<sentence_id>-r<N>.wav` at the engine's own sample rate with `write_pcm16` imported from `tts_bench.intelligibility.synth`, inspect with `inspect_wav` from `tts_bench.intelligibility.audio_check`, record `ManifestItem` with status `ok` / `failed` / `silent`; `EmptyAudioError` is `silent`, other `TTSBenchError` is `failed`; a load failure propagates and nothing is written; always `adapter.close()`; write `manifest.json` with repetitions N and designated repetition 1
- [X] T018 [US1] Implement reference resolution in `src/tts_bench/speaker/reference.py`: `resolve_reference(library, voice_name) -> (wav_path, ReferenceQuality)` using only public `LocalVoiceLibrary` methods (`show`, `recording`, `resolve`); for `reference_audio` voices use the stored `reference.wav`, and for a `stored_voice_file` voice such as Phonon's `.safetensors` use the original consented recording segment from the library entry (`recording_id`, `segment`) cut with the library's segment helper; copy `duration_s`, `speech_seconds`, `snr_estimate_db`, `accent` and `warnings` into `ReferenceQuality` (FR-012); never store the path; consent is enforced by `resolve` (`use`/`content` arguments) and its errors propagate
- [X] T019 [US1] Implement `src/tts_bench/speaker/embed.py`: `embed_directory(audio_dir, embedder, *, reference_wav, cache_dir=None)` reads `manifest.json`, embeds the reference once and every `ok` clip (skipping `failed` and `silent`, recording their status), converting to mono and the embedder's sample rate, caching by `sha256(audio) + settings_hash`, and writes `embeddings.json` into the audio directory (never into `results/`); the same `Embedder` instance and settings are used for every clip (FR-002)
- [X] T020 [US1] Implement `src/tts_bench/speaker/scoring.py` (US1 part): `score_embeddings(embeddings, manifest, corpus, *, engine) -> ResultsFile`: per-sentence similarity for repetition 1 only (`SimilarityScore` with flags), engine summary with mean, sd (sample, n−1), min, max over scored sentences, `n_sentences` / `n_scored` / `n_flagged`, warnings listing the count of `short_audio` clips, `status` `scored` or `not_applicable`; include the notice, embedder record, reference quality, language `es` and the limitation note; contains no vectors or paths (data-model "Results File")
- [X] T021 [US1] Implement `src/tts_bench/speaker/compare.py`: `compare_results(files) -> str` returning Markdown that begins with the FR-008 notice, then a per-engine table (engine, voice, mean similarity, sd, n scored, flagged, warnings) and `not applicable` rows for non-cloning engines; refuse with `MergeRefused(field)` when `embedder.name`, `checkpoint`, `settings_hash`, `corpus_hash`, `subset` or reference `recording_id` differ (FR-002, SC-002); the Consistency and EER sections are added in T025 and T029
- [X] T022 [US1] Implement `src/tts_bench/speaker/__main__.py` per contracts/speaker-cli.md: subcommands `synthesize`, `embed`, `score`, `compare` with the listed options (defaults `output/speaker` and `results/speaker`); `synthesize` uses `get_adapter` and `LocalVoiceLibrary` like the intelligibility CLI, calls `resolve` with the consent arguments already used by feature 005, and exits 2 when the engine cannot load; `embed --model fake` selects `FakeEmbedder`, `--script FILE.json` maps audio sha256 or sentence id to vectors; exit 2 if the model or weights are missing (with the hint); `score` exits 1 on a missing or malformed file; `compare` exits 3 naming the differing field; every printed report starts with the FR-008 notice
- [X] T023 [US1] Export `cosine_similarity`, `coefficient_of_variation`, `equal_error_rate`, `score_embeddings` from `src/tts_bench/speaker/__init__.py` (the last two are added when their modules exist in US2 and US3) and run `.venv-core/bin/python -m pytest tests/speaker -q`; all US1 tests from T010 to T016 pass

**Checkpoint**: US1 is the MVP: a similarity score per sentence and per engine, runnable end to end with fakes

---

## Phase 4: User Story 2 - Measure consistency across repeated generations (Priority: P2)

**Goal**: report how much duration and similarity vary across N generations of the same sentence, declining unreliable coefficients.

**Independent Test**: with the fake engine at known durations, the coefficient of variation matches the hand-computed value within 5%; a near-zero mean is declined.

### Tests for User Story 2

- [X] T024 [P] [US2] Write `tests/speaker/test_variation.py` (SC-003): durations `(1.0, 1.1, 0.9)` give CV = sample sd (n−1) / mean = 0.1 exactly (assert within 5% relative and also exact against `statistics.stdev / fmean`); identical values give CV 0.0; a mean below 0.05 in the metric's own unit returns `status: near_zero_mean` and `value: None` (FR-011, never a number); exactly one value returns `fewer_than_two`; an empty list returns `fewer_than_two`; a mean of exactly 0.05 is reported (the guard is "below 0.05"); negative-mean similarity uses `abs(mean)` for the guard and the CV is `sd / abs(mean)`
- [X] T025 [P] [US2] Write `tests/speaker/test_consistency.py`: with `FakeAdapter(supports_cloning=True, audio_seconds_sequence=(3.0, 3.3, 2.7, ...))` and `FakeEmbedder`, a run of 5 repetitions on 4 sentences produces per-sentence duration CV matching the hand-computed value within 5% (SC-003) and a per-sentence similarity CV computed from scripted vectors with known cosines; the per-engine figure is the median of per-sentence CVs with the mean shown beside it; sentences with one successful repetition are `fewer_than_two` and counted in `n_unavailable`; a near-zero-mean sentence is counted in `n_declined`, absent from the median, and carries `reason: near_zero_mean`; the consistency record lists `repetitions` N; failed or silent repetitions are excluded from a sentence's values

### Implementation for User Story 2

- [X] T026 [P] [US2] Implement `src/tts_bench/speaker/variation.py`: `coefficient_of_variation(values, *, min_abs_mean=0.05) -> CV` with `CV(value, status, reason)`: sample sd (n−1) divided by `abs(mean)`; `fewer_than_two` for fewer than 2 values; `near_zero_mean` when `abs(mean) < min_abs_mean`; pure, standard library plus numpy
- [X] T027 [US2] Extend `src/tts_bench/speaker/scoring.py`: build `ConsistencyRecord` from all repetitions of each sentence (duration from the manifest, similarity from the embeddings against the same reference), per-sentence `duration_cv`, `similarity_cv` and `reason`, engine `cv_median`, `cv_mean`, `n_sentences_valid`, `n_declined`, `n_unavailable` per metric (data-model "Consistency Record"); consistency uses all repetitions, the headline similarity from T020 stays on repetition 1 only (FR-004)
- [X] T028 [US2] Extend `src/tts_bench/speaker/compare.py` and `__main__.py`: add a Consistency table (engine, duration CV median/mean, similarity CV median/mean, repetitions, declined, unavailable) printing "declined (unreliable)" or "not available" instead of a number where applicable; run `.venv-core/bin/python -m pytest tests/speaker -q`; T024 and T025 pass and US1 tests still pass

**Checkpoint**: US1 and US2 both work independently

---

## Phase 5: User Story 3 - Optionally verify with equal error rate (Priority: P3)

**Goal**: build labeled same-speaker and different-speaker pairs from the project's own Spanish audio and report one EER per comparison, warning when it is high; the check is required before the first real run's scores are trusted (plan decision 8).

**Independent Test**: with labeled score sets, EER matches hand-calculated values; a high EER produces the warning; with too few pairs EER is "not available".

### Tests for User Story 3

- [X] T029 [P] [US3] Write `tests/speaker/test_eer.py`: perfectly separated scores (all same above all different) give EER 0.0; fully overlapping identical distributions give 0.5; a hand-built case with same `[0.9, 0.8, 0.4]` and different `[0.6, 0.3, 0.2]` gives the hand-calculated EER and threshold (written in the test as exact fractions, with linear interpolation between the two nearest thresholds); ties in scores give a deterministic result (same input twice, identical output); fewer than 2 same-speaker or fewer than 2 different-speaker scores returns `available: false` with a `reason`; EER above 10% sets `high_eer_warning` true, exactly 10% does not (FR-005); `separation` equals mean same minus mean different (hand-computed) and `gate_passed` is true only when EER ≤ 10% and separation ≥ 0.20, with a case at exactly 0.20 passing and 0.19 failing
- [X] T030 [P] [US3] Write `tests/speaker/test_pairs.py`: for two voices A and B with fixed embeddings, same-speaker pairs are reference-A versus each A clip of the designated run, different-speaker pairs are reference-A versus B's reference and B clips, and reference-B versus A's reference and A clips (research R5); pairs are pooled across engines and reported once per comparison (clarification 2026-11-03); one voice only gives `available: false` with reason "at least one other voice is needed"; silent or failed clips never form pairs; the record's `pair_construction` text is stored

### Implementation for User Story 3

- [X] T031 [P] [US3] Implement `src/tts_bench/speaker/eer.py`: `equal_error_rate(same_scores, different_scores, *, high_threshold=0.10) -> EERRecord`; sweep the decision threshold over the sorted distinct scores, compute false-accept and false-reject rates, take the crossing with linear interpolation between the two nearest thresholds; pure; `available` false below 2 scores of either kind; `high_eer_warning` true when EER is above `high_threshold`; also compute `separation` and `gate_passed` (EER ≤ 10% and separation ≥ 0.20, parameter `min_separation=0.20`)
- [X] T032 [US3] Implement `src/tts_bench/speaker/pairs.py`: `build_pairs(embedding_files) -> (same_scores, different_scores, description)` per research R5, pooling across engines; extra other-voice reference vectors come from `extras` in the embeddings file (`embed --extras-from`); no vectors or paths leave the function except scores
- [X] T033 [US3] Extend `scoring.py`, `compare.py` and `__main__.py`: `score --eer [--eer-from FILE...]` adds the `eer` block once per comparison; a high EER (above 10%) adds the warning "similarity scores should be interpreted cautiously" next to every similarity table and marks the results set `not reliable for ranking`; `compare` prints the EER section once with the Spanish-coherence note (audio is es-CO, model is mostly trained on English-dominant data, so EER on the project's own Spanish pairs is the acceptance check); run `.venv-core/bin/python -m pytest tests/speaker -q`; T029 and T030 pass and earlier stories still pass

**Checkpoint**: all three user stories work independently

---

## Phase 6: Polish and Cross-Cutting Concerns

- [X] T034 [P] Implement the real `SpeechBrainEmbedder.embed` in `src/tts_bench/speaker/embedder.py` (body of T006): load `speechbrain/spkrec-ecapa-voxceleb` at a pinned revision on CPU in eval mode, resample to 16 kHz mono, no peak normalization, embed the whole clip, return the 192-dimensional vector; `record()` fills name, checkpoint and revision, speechbrain and torch versions, settings and `settings_hash`, the model license and the training-data note (VoxCeleb terms), and the limitation note; verify the checkpoint license and the VoxCeleb terms when pinning and record the finding in `docs/speaker-similarity.md` (Principle VI)
- [X] T035 [P] Write `tests/speaker/test_embedder_real.py` marked `@pytest.mark.engine`, run in `.venv-spk`: two embeddings of the same Spanish clip are identical (SC-005); the clip against itself scores at least 0.99; the vector length is 192; two clips of the project's two consented voices score at least 0.20 lower on average than two clips of the same voice (Spanish sanity check)
- [X] T036 [P] Write `tests/speaker/test_offline.py`: `score` and `compare` perform no network access (monkeypatch `socket.socket` to raise) and import neither `speechbrain` nor `torch` (assert via `sys.modules` after running them)
- [X] T037 [P] Write `docs/speaker-similarity.md`: definitions of similarity, per-engine average, CV (including the near-zero-mean rule and the median aggregation), EER and the high-EER threshold, short-audio minimum, the pair construction and its two-voice limitation, the Spanish coherence gate and what happens if the model fails it, the embedding model identity and license finding, and the limitations (similarity near 1 is not identity, noise, language, prosody, reference quality; scores are not a substitute for human judgment; not a naturalness metric); a metric definition change needs a spec update and a report note (Constitution Development Workflow)
- [X] T038 Run the real measurement per quickstart section 3 (engine and embedding venvs, one per process): `synthesize` for phonon with `valentina-phonon` and pocket_tts with `valentina-pocket` (5 repetitions, 21 cloning sentences), `synthesize piper` to confirm "not applicable", `embed` with `--extras-from` for the other consented voice, then `score --eer --eer-from` and `compare`; store only the results JSON under `results/speaker/` and write `results/speaker/comparison.md`
- [X] T039 Apply the Spanish coherence gate to the T038 results: if EER is above 10% or `gate_passed` is false (separation below 0.20), mark the run not reliable in `results/speaker/comparison.md`, keep it labeled (Principle V), and open a follow-up to replace ECAPA with a multilingual embedding model and rerun; if it passes, write the conclusions (similarity per engine, consistency per engine) in `results/speaker/comparison.md` next to the FR-008 notice, the model license, the reference quality and the cloning limitations
- [X] T040 Run the full validation in `quickstart.md` sections 1, 2, 4 and 5 (`.venv-core/bin/python -m pytest tests -q`; determinism diff; `git status` shows no audio, embeddings or reference files); update `README.md` and `docs/metrics.md` with a link to `docs/speaker-similarity.md`

---

## Dependencies and Execution Order

- Phase 1 first. Phase 2 depends on Phase 1 and blocks all stories; within Phase 2, T004 to T010 are mostly parallel (T008 touches `fake.py` only, T010 needs T004).
- **US1** (Phase 3) depends on Phase 2 only. **US2** depends on US1 scoring and compare (T020, T021, T022). **US3** depends on US1 embeddings (T019, T020); it is independent of US2, but T033 and T028 both edit `compare.py` and `__main__.py`, so run them in order.
- Tests inside each story come before their implementation tasks. Phase 6 depends on all stories; T038 needs T034 and the real engines; T039 needs T038.
- Same-file tasks are sequential: `scoring.py` (T020, T027, T033), `compare.py` (T021, T028, T033), `__main__.py` (T022, T028, T033).

## Parallel Examples

- Phase 2: T004, T005, T006, T007, T008 and T009 touch different files and can run together; T010 follows T004.
- US1 tests T011 to T016 are separate files and can be written together; implementation T017, T018 and T019 can run in parallel (different files), then T020, T021, T022 in order.
- US2: T024 and T025 together, then T026 in parallel with them, then T027 and T028.
- US3: T029, T030 and T031 together, then T032 and T033.
- Polish: T034 to T037 together.

## Implementation Strategy

1. **MVP**: Phases 1, 2 and 3. A similarity score per sentence and per engine with the same-model guard, runnable with fakes, ready for a first real measurement (needs T034 for the real model).
2. Add US2 (consistency), then US3 (EER). Because of the Spanish gate, the first real publication of results needs US3 and T039, not only the MVP.
3. Run T038 and T039 last, with real engines, one per process; never publish ECAPA-based rankings if the gate fails.

## Requirement coverage

| Requirement | Tasks |
|-------------|-------|
| FR-001 | T004, T010, T011, T020 |
| FR-002 | T006, T019, T021, T014 |
| FR-003 | T011, T017, T020 |
| FR-004 | T024, T025, T026, T027 |
| FR-005 | T029, T030, T031, T032, T033 |
| FR-006 | T012, T017, T021 |
| FR-007 | T012, T020 |
| FR-008 | T013, T014, T022 |
| FR-009 | T013, T034 |
| FR-010 | T006, T009, T036 |
| FR-011 | T024, T026, T028 |
| FR-012 | T013, T018 |
| SC-001 | T010, T011 |
| SC-002 | T014, T021 |
| SC-003 | T024, T025 |
| SC-004 | T014, T022 |
| SC-005 | T016, T035 |

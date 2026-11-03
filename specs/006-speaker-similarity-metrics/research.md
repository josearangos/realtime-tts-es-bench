# Research: Speaker Similarity and Consistency Metrics

## R1. Stage separation and process model
- **Decision**: stages joined by files: `synthesize` (engine venv: WAVs + manifest) → `embed` (embedding venv: embeddings) → `score` (any venv, pure) → `compare`.
- **Rationale**: one engine per process and per-engine dependency isolation (Principle VII); the embedding model is one more heavy dependency. Files between stages let `score` run on fixed embeddings (FR-010) and be re-run without audio or weights (SC-005).
- **Alternatives**: one command doing everything (needs engine and model in one environment, rejected); reusing feature 005 audio (rejected: 005 covers the main subset with the default voices, not the cloning subset, and has no repetitions).

## R2. What is synthesized
- **Decision**: the 21 sentences of the `cloning` subset, for each cloning-capable engine (`descriptor.supports_cloning`) with its cloned voice resolved through `LocalVoiceLibrary.resolve`, N repetitions (default 5), same sentence order. Repetition 1 is the **designated run** for the headline similarity (clarification 2026-11-03); all repetitions feed consistency.
- **Rationale**: the spec scopes the metric to the cloning subset. Feature 004 does not keep audio, so audio must be generated here.
- **Exclusion**: engines with `supports_cloning=False` (Piper) are listed as `not_applicable` in `compare`, never scored (FR-006). The fake engine is treated as cloning-capable in tests through a flag.

## R3. Embedding model
- **Decision**: SpeechBrain ECAPA-TDNN `speechbrain/spkrec-ecapa-voxceleb` (192-d), pinned by revision, run on CPU in `.venv-spk`. Input is resampled to 16 kHz mono, peak left unnormalized, whole clip embedded (no trimming). Similarity is cosine on the raw embeddings.
- **Rationale**: widely used speaker-verification baseline, published EER, local CPU inference, deterministic in eval mode, Apache-2.0 code.
- **Alternatives**: Resemblyzer (GE2E; older, English-centric, torch pinning problems); WeSpeaker ResNet via ONNX (lighter, license and checkpoint to verify per file); pyannote embedding (gated download, token needed, rejected for local-first and secrets constraints).
- **To verify when pinning (Principle VI)**: license of the exact checkpoint and the VoxCeleb training-data terms; determinism across two runs on the same machine (SC-005), covered by an `engine`-marked test.
- **Spanish gate (user requirement, 2026-11-03)**: audio is Spanish (es-CO) throughout, so the model is accepted only if the required EER check on the project's Spanish pairs passes (EER ≤ 10% **and** separation ≥ 0.20, where separation = mean similarity of same-speaker pairs minus mean of different-speaker pairs; threshold approved 2026-11-03). If not, switch to a multilingual embedding model and rerun; results from the failing model are kept and labeled, not hidden (Principle V).
- **Known limitations, stated in outputs**: trained mostly on English/multilingual celebrity interviews, so Spanish and es-CO may score differently; embeddings capture channel, noise and prosody as well as voice; a high score does not mean the voice sounds identical (FR-008).

## R4. Metric definitions (documented in `docs/speaker-similarity.md`)
- **Similarity**: cosine of reference embedding and clip embedding, range −1 to 1, 1 is the maximum. Reference embedding is computed once from the voice's reference audio (the stored `reference.wav`; for Phonon, whose stored voice is a `.safetensors` file, the original consented recording segment from the voice library entry `recording_id`).
- **Per engine**: arithmetic mean over designated-run sentences that are scored (not silent, not failed), with n, standard deviation, min and max. Silent or failed clips are excluded from the mean and counted.
- **Coefficient of variation**: sample standard deviation (n−1) divided by the mean, per sentence over its N repetitions, for duration (seconds) and for similarity; the per-engine figure is the median of per-sentence CVs, with the mean shown beside it. Declined (marked unreliable, no number) when the |mean| is below 0.05 in the metric's own unit; "not available" with fewer than 2 values.
- **EER**: scores from labeled pairs pooled across engines; sweep the decision threshold over sorted distinct scores and take the point where false-accept and false-reject rates are closest, interpolating linearly between the two nearest thresholds; ties are deterministic. Needs at least 2 same-speaker and 2 different-speaker pairs, else "not available". Warning when EER > 10%. The record also stores `separation` and `gate_passed` (EER ≤ 10% and separation ≥ 0.20).
- **Short audio**: duration < 3.0 s gets the `short_audio` flag and a warning.

## R5. Pair construction for EER (clarified)
- **Decision**: same-speaker pairs: reference vs. each cloned clip of the designated run. Different-speaker pairs: the same clips vs. the *other* consented voice's reference recording, and the other voice's clips vs. this voice's reference. Pairs are pooled across cloning engines and reported once per comparison.
- **Rationale**: tests the exact speakers and conditions used for scoring, no external dataset, consent stays simple.
- **Limitation, stated in outputs**: with two speakers the EER measures separation of those two voices only, and cloned clips are not natural recordings; so EER is a sanity check, not a general model evaluation.

## R6. Privacy and storage
- **Decision**: embeddings are voice-derived data. They live under git-ignored `output/speaker/`; tracked results contain scores, statistics, model identity and quality metadata only, with no embeddings, paths or audio. A test (`test_privacy.py`) asserts this.
- **Rationale**: Principle VI forbids committing reference audio and derived voice files; speaker embeddings are derived from them.

## R7. Determinism and caching
- **Decision**: embeddings cached by `sha256(audio) + settings hash`; `score` is pure and byte-identical on the same embeddings file (timestamps only in file names and `environment`). The engine itself may produce different audio per synthesis; this is expected, and the consistency metric measures exactly that variation.
- **Rationale**: SC-005 applies to the same audio.

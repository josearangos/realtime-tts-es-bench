# Speaker similarity and consistency metrics

> Speaker similarity scores come from one embedding model and are not a substitute for human judgment; a score near 1 does not guarantee the voice sounds identical.

How close a cloned voice is to its reference, and how stable it is across repeated generations. Only engines that clone voices are measured (`supports_cloning`): Piper is `not applicable`, never scored or penalized. Spec and design: [specs/006-speaker-similarity-metrics](../specs/006-speaker-similarity-metrics/). Measured results: [results/speaker/comparison.md](../results/speaker/comparison.md).

## Pipeline

| Stage | Environment | Command | Output |
|---|---|---|---|
| synthesize | the engine's venv | `python -m tts_bench.speaker synthesize ENGINE --voice NAME` | `output/speaker/<engine>-<voice>/` (WAVs, `manifest.json`; not tracked) |
| embed | `.venv-spk` | `python -m tts_bench.speaker embed AUDIO_DIR [--extras-from DIR...]` | `embeddings.json` next to the audio (not tracked) |
| score | any (stdlib + numpy) | `python -m tts_bench.speaker score EMBEDDINGS [--eer] [--eer-from FILE...]` | `results/speaker/<engine>-<ts>.json` (tracked, scores only) |
| compare | any | `python -m tts_bench.speaker compare RESULTS...` | Markdown; exit 3 naming the field when inputs are not comparable |

`synthesize` uses the 21 sentences of the `cloning` subset, 5 repetitions by default (`--repetitions`), the cloned voice resolved through the voice library (consent enforced). `score` and `compare` need no engine, no model and no network, so every computation is tested with fixed embeddings.

## Definitions

- **Similarity**: cosine of the reference embedding and the clip embedding (range −1 to 1; 1 is the maximum; rounded to 12 decimals). Only the **designated run** (repetition 1) feeds the headline figure, so repetitions do not inflate the sample. The reference is the voice's stored `reference.wav`; for a voice stored as a model file (Phonon) it is the original consented recording segment named by the library entry.
- **Per engine**: mean, sample standard deviation (n−1), min and max over the scored sentences, with `n_scored` and `n_flagged`. Silent or failed clips and zero-norm embeddings are excluded from the mean, flagged (`silent_audio`, `synthesis_failed`, `embedding_failed`) and counted.
- **Short audio**: a clip shorter than 3.0 s is flagged `short_audio`, still scored and kept in the mean; the count appears as a warning. Exactly 3.0 s is not short.
- **Coefficient of variation (CV)**: sample standard deviation (n−1) divided by |mean| over the repetitions of one sentence, for duration (seconds) and for similarity. The per-engine figure is the **median** over sentences, with the mean shown beside it. With fewer than two values the CV is `not available`; when |mean| is below 0.05 in the metric's own unit it is **declined** (no number, marked unreliable). Failed and silent repetitions are left out. All repetitions feed the CV.
- **EER**: equal error rate of the labeled same-speaker and different-speaker scores, found by sweeping the threshold over the sorted distinct scores and interpolating linearly between the two nearest thresholds. Needs at least 2 pairs of each kind, else `not available`. A warning is raised above 10%.
- **Pairs**: same-speaker pairs are a voice's reference against each of its designated-run clips; different-speaker pairs are that reference against the other consented voice's reference and clips (both directions when both voices are present). Pooled across engines and reported once per comparison. Two voices means the EER measures the separation of those two voices only, and cloned clips are not natural recordings: it is a sanity check on Spanish audio, not a general model evaluation.
- **Spanish coherence gate**: the audio is es-CO and the model is trained on English-dominant data, so scores are trusted only when the EER check passes: EER ≤ 10% **and** separation (mean same-speaker minus mean different-speaker score) ≥ 0.20. If it fails, the run is kept and labeled `not reliable for ranking` (Constitution Principle V), and ECAPA is replaced by a multilingual embedding model before any ranking is published. A change to any definition here needs a spec update and a note in the report.

## Embedding model

SpeechBrain ECAPA-TDNN `speechbrain/spkrec-ecapa-voxceleb` (192-dimensional), pinned to Hugging Face commit `0f99f2d0ebe89ac095bcc5903c4dd8f72b367286`, CPU, eval mode, 16 kHz mono, no peak normalization, whole clip embedded. The checkpoint card declares Apache-2.0; it was trained on VoxCeleb1 and 2, whose own terms were **not verified** for commercial use (checked 2026-11-03: the card lists the license and the dataset only). Weights are cached under the git-ignored `output/speaker/.models/` and the Hugging Face cache. Setup: `python3.11 -m venv .venv-spk && .venv-spk/bin/pip install -e ".[speaker]"`.

Every results file stores the model name, checkpoint, library versions, settings and `settings_hash`; `compare` refuses results whose embedder name, checkpoint, settings, corpus hash, subset or reference recording differ.

## Limitations

- A score near 1 is not identity; embeddings also capture channel, noise and prosody. A score below 1 for a cloned voice is expected.
- Language: the model is English-dominant, hence the Spanish gate above. One reference recording per voice, two consented voices, 21 sentences.
- Reference quality (duration, speech seconds, SNR, accent, warnings) is stored with every result; a poor reference lowers every engine's score.
- It is not a naturalness metric and does not replace a human listening test.

## Privacy

Reference audio, generated clips and embeddings are voice-derived data: they stay under the git-ignored `output/speaker/`. Results files contain only scores, statistics and metadata, with no vectors, audio, absolute paths or host names (`tests/speaker/test_privacy.py`).

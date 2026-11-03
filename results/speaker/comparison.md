> Speaker similarity scores come from one embedding model and are not a substitute for human judgment; a score near 1 does not guarantee the voice sounds identical.

Embedding model: `speechbrain-ecapa` (speechbrain/spkrec-ecapa-voxceleb@0f99f2d0ebe89ac095bcc5903c4dd8f72b367286); settings hash `62f735dd2e57f0be`; audio language `es`. Corpus subset `cloning` (`e4fb3b0af339b63f725652dfffd2a2080ce2ec75c36fd7f2425d6915cf4f36a4`). Reference `rec-5065ba29756d` (es-CO, 16.3 s, SNR 48.2 dB).

## Similarity to the reference (designated run)

| Engine | Voice | Mean | SD | Min | Max | Scored | Flagged | Warnings |
|---|---|---|---|---|---|---|---|---|
| phonon | valentina-phonon | 0.666 | 0.113 | 0.314 | 0.799 | 21/21 | 0 | 2 clip(s) shorter than 3.0 s: speaker embeddings of short audio are less reliable (kept in the average) |
| pocket_tts | valentina-pocket | 0.570 | 0.080 | 0.367 | 0.666 | 21/21 | 0 | 2 clip(s) shorter than 3.0 s: speaker embeddings of short audio are less reliable (kept in the average) |

## Consistency across repetitions (coefficient of variation, median / mean over sentences)

| Engine | Repetitions | Duration CV | Similarity CV | Declined | Unavailable |
|---|---|---|---|---|---|
| phonon | 5 | 0.000 / 0.000 | 0.000 / 0.000 | 0 | 0 |
| pocket_tts | 5 | 0.038 / 0.054 | 0.048 / 0.059 | 0 | 0 |

## Speaker-verification check (EER on the project's Spanish audio)

- EER: 0.0154 at threshold 0.330 (63 same-speaker and 65 different-speaker pairs)
- Separation (mean same minus mean different): 0.357
- Spanish gate (EER <= 10% and separation >= 0.20): passed
- Pairs: Same-speaker pairs: a voice's reference against each of its cloned clips of the designated run. Different-speaker pairs: that reference against the other consented voice's reference and clips (and its extra reference vectors). Pooled across cloning engines. With two speakers the EER measures the separation of those two voices only, and cloned clips are not natural recordings, so it is a sanity check on Spanish audio, not a general model evaluation.
- The audio is es-CO and the model is trained mostly on English-dominant data, so this check on the project's own Spanish pairs is the acceptance test for the scores above.

## Run conditions

- Engines: phonon with `valentina-phonon` and pocket_tts with `valentina-pocket`, both cloned from the same consented recording (`rec-5065ba29756d`, es-CO). Piper does not clone voices: `not applicable`, not scored and not penalized.
- Corpus: the 21 sentences of the `cloning` subset, 5 repetitions per sentence per engine (105 clips each, none failed or silent). Repetition 1 is the designated run for the similarity figures; all five feed the consistency figures.
- Embedding model: SpeechBrain ECAPA-TDNN `spkrec-ecapa-voxceleb`, pinned to Hugging Face commit `0f99f2d`, CPU, 16 kHz mono, same settings for every clip. License on the checkpoint card: Apache-2.0; trained on VoxCeleb1+2, whose own terms were not verified for commercial use.
- EER pairs: the other consented voice (`emiliano-pocket`, 105 clips, recording `rec-874bd765e7f6`) supplies the different-speaker material; pairs are pooled across the three runs and reported once.
- Reference quality: 16.3 s recording, 14.0 s of speech, SNR estimate 48.2 dB, no warnings.

## Conclusions

- **Spanish coherence gate: passed.** EER 1.5% (limit 10%) and separation 0.357 (limit 0.20) on 63 same-speaker and 65 different-speaker pairs of the project's own es-CO audio. The scores above can be read as speaker similarity for this audio. With only two speakers this checks the separation of those two voices, not the model in general.
- **Similarity to the reference:** phonon 0.666 (SD 0.113), pocket_tts 0.570 (SD 0.080), n = 21 each. Per sentence, phonon scored higher on 18 of 21 sentences; the paired difference is 0.096 (SD 0.080, standard error 0.017), which is well outside the sentence-to-sentence noise for this sample. Both are far from 1: cloned speech here is recognizably closer to the reference voice than to the other voice (the gate), but not an identical voice.
- **Consistency:** phonon is deterministic: all 105 clips are bit-identical across repetitions for each sentence, so both CVs are exactly 0. pocket_tts varies between repetitions: median duration CV 3.8% (mean 5.4%) and median similarity CV 4.8% (mean 5.9%), up to 18.5% for the least stable sentence. No coefficient was declined or unavailable.
- **Short audio:** the same two sentences are shorter than 3.0 s for both engines: CLO-007 (phonon 2.08 s, pocket_tts 1.92 s) and CLO-021 (phonon 2.00 s, pocket_tts 1.44 s). They are kept in the averages and are the lowest or near-lowest scores of each engine (phonon 0.314 and 0.453; pocket_tts 0.367 and 0.404), so the means may be slightly pessimistic for both.
- **Limits:** one reference voice and one recording per engine, one embedding model, 21 sentences. Similarity is not a naturalness or human-likeness measure and a human listening test is still the reference for "sounds like her".

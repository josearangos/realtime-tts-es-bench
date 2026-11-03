# Engine selection: Piper, Phonon and Pocket TTS for real-time Spanish call center TTS

Cross-analysis of every measurement the project has produced, written on 2026-11-03. Every figure is copied from the report named next to it, so it can be checked there. The only addition that is not a report is the owner's blind listening check (section 4.3b).

| Front | Feature | Report |
|---|---|---|
| Speed and resources (TTFA, RTF, throughput, RAM, load, cold start) | 004 | [`perf/comparison.md`](perf/comparison.md) |
| Intelligibility (WER, CER with Whisper `large-v3`) | 005 | [`intelligibility/comparison.md`](intelligibility/comparison.md) |
| Speaker similarity and consistency of cloned voices | 006 | [`speaker/comparison.md`](speaker/comparison.md) |
| Licensing and consent | 001, 003 | [`../docs/engines.md`](../docs/engines.md) |

## 1. Recommendation in one paragraph

**Phonon is the best engine on every measured quality and speed front, but its weights are licensed non-commercial (CC BY-NC 4.0).** If this benchmark feeds a commercial call center product, Phonon cannot be shipped as is, and the choice has to be made again with that constraint in view. In that case **Pocket TTS is the only measured engine that clones the target voice and has a usable license**, but its intelligibility on numbers and amounts (WER 33.7% overall) is not acceptable for a call center without fixing or controlling that failure. **Piper** is intelligible and light but does not clone the voice, and its engine is GPL-3.0. So the honest answer has two branches (section 7): use Phonon for evaluation, internal benchmarking and demos; for a commercial deployment, decide between obtaining a commercial license for Phonon, accepting Piper without cloning, or investing in Pocket TTS number handling.

## 2. What was measured, and how comparable it is

- **Same machine, same corpus family.** Apple M2 Pro, 10 cores, 16 GiB, CPU only. Performance and intelligibility use the main corpus (123 sentences, version 1.0.0). Speaker similarity uses its 21-sentence cloning subset, with 5 repetitions per sentence.
- **Different voices.** Phonon and Pocket TTS use cloned es-CO voices (`valentina-phonon`, `valentina-pocket`, from one consented recording). Piper uses a fixed catalog voice, `es_MX-claude-high`, which is Mexican Spanish, not Colombian. Piper's WER and speed therefore mix engine and voice; and it has **no speaker similarity** (it does not clone, so that metric is `not applicable`, not a zero).
- **One recognizer, one embedding model.** WER and CER are as heard by Whisper `large-v3`; similarity is by SpeechBrain ECAPA-TDNN. Both mix the engine with the measuring model, and neither is a naturalness measure.

## 3. Results side by side

| Criterion | Phonon | Pocket TTS | Piper | Best |
|---|---|---|---|---|
| **Time to first audio**, p50 / p95, warm | 8.0 / 15.7 ms | 79.6 / 88.1 ms | 163.5 / 317.4 ms (whole sentence, not comparable as a streaming TTFA) | Phonon |
| **RTF** p50, warm (lower is faster) | 0.056 | 0.282 | 0.029 | Piper (raw speed) |
| **Throughput**, warm (audio s/s) | 16.4 | 3.8 | 33.8 | Piper |
| **Peak RAM** | 301 MiB | 1807 MiB | 769 MiB | Phonon |
| **CPU use** | 20% of a core | 167% | 489% | Phonon |
| **Load time**, warm / cold | 115 / 226 ms | 3835 / 6679 ms | 37 / 63 ms | Piper, then Phonon |
| **First-request penalty**, cold | +470 ms | +1980 ms | +1097 ms | Phonon |
| **WER / CER** (123 sentences) | **1.4% / 0.7%** | 33.7% / 27.6% | 2.9% / 1.4% | Phonon |
| WER on digit sequences | 0.0% | 47.4% | 1.6% | Phonon |
| WER on amounts in pesos | 2.2% | 109.0% | 4.4% | Phonon |
| WER on acronyms | 3.5% | 33.6% | 4.0% | Phonon |
| **Similarity to the reference voice** (mean, 21 sentences) | **0.666** | 0.570 | not applicable | Phonon |
| **Repetition consistency** (median CV, duration / similarity) | 0% / 0% (deterministic) | 3.8% / 4.8% | not measured (no cloning) | Phonon |
| **Failed or silent syntheses** | 0 of 123 and 0 of 105 | 0 of 123 and 0 of 105 | 0 of 123 | tie |
| **License of weights / engine** | **CC BY-NC 4.0 (non-commercial)**; runtime MIT or Apache-2.0 | package MIT; model terms checked by the owner as usable; weights gated | engine **GPL-3.0** (copyleft); voice usable per its model card | Pocket TTS (for commercial use) |
| **Clones the target voice** | yes | yes | no | Phonon, Pocket TTS |

Notes on reading the table:

- Piper's TTFA is the time for the whole sentence, because it does not stream. A caller hears nothing until it is ready, which is roughly 20 times later than Phonon's first sound.
- Piper is the fastest at producing audio, but speed beyond "faster than real time" has little value for a single stream; all three are already well below RTF 1. The advantage of Piper's throughput only matters if many calls share one machine, which was not tested, and Piper's 489% CPU suggests it would not scale simply.
- Pocket TTS's amounts WER above 100% comes from the recognizer looping on digits in a few sentences; it signals a real failure on money, but the exact percentage is inflated by how insertions are counted. The overall 33.7% is the more honest figure, and 18.6% remains after removing the worst sentence ([`intelligibility/comparison.md`](intelligibility/comparison.md)).

## 4. Analysis by front

### 4.1 Real-time behavior

Phonon starts talking in about 8 ms and finishes a sentence at 5.6% of its audio duration, using 301 MiB and a fifth of one core. That is both the best first-sound latency and the lowest resource footprint, which matters when one machine serves several calls. Pocket TTS is fast enough for real time on a single stream (TTFA under 100 ms, RTF 0.28) but is the heaviest (1.8 GiB, 167% CPU) and has the slowest start (3.8 to 6.7 s load, about 2 s extra on the first request). Piper has the best raw speed but each reply arrives whole. **Warm-up before taking calls is mandatory for Pocket TTS and Piper, and advisable for Phonon.**

### 4.2 Intelligibility

Phonon (1.4%) and Piper (2.9%) are both in the range where errors are mostly proper names and recognizer quirks. The gap between them is a handful of words from one synthesis each, so it is a trend, not proof. Pocket TTS is an order of magnitude worse and fails exactly where a call center cannot afford it: digit sequences (47.4% WER), money amounts and acronyms. On short, plain sentences it is as good as the others (0.0% on short sentences), so the failure is specific, not general.

### 4.3 Voice fidelity and stability (cloned voices only)

Phonon's clips score 0.666 against the reference and Pocket TTS's 0.570. Phonon was higher on 18 of 21 sentences; the paired difference is 0.096 with a standard error of 0.017. The metric was validated on the project's own Spanish audio before being trusted (EER 1.5%, separation 0.357; limits 10% and 0.20). Both are far from 1 on this scale, which the human check (section 4.3b) shows is a property of the scale and not of the voice quality. Phonon is bit-identical across repetitions; Pocket TTS varies in both duration (CV 3.8%) and similarity (CV 4.8%, up to 18.5% for the least stable sentence).

### 4.3b Human listening check

The owner of the project listened to the blind kit (reference plus A/B pairs of the same sentences from Phonon and Pocket TTS, engine hidden) and reported on 2026-11-03 that **Phonon clearly outperforms the other models and that its cloning is almost perfect**. This agrees with the direction of the automated ranking (Phonon above Pocket TTS on similarity) and adds what the metric cannot say: that the voice is recognizably the target one to a person.

Two things should be kept apart. First, the human verdict is stronger in size than the automated one: ECAPA gives Phonon 0.666, "far from 1", while the listener judges it almost perfect. This is expected from the measuring instrument, not a contradiction: the embedding model is trained on English-dominant data, compares a synthetic clip against a studio recording, and also reacts to channel and prosody, so its absolute values read low and only the ordering and the Spanish EER check are meaningful. Second, this is the judgment of a single listener, given verbally, and the scored sheet (`output/speaker/listening/hoja.csv`) was not returned, so there are no per-pair ratings to report. It validates the ranking; it is not a statistical listening test.

### 4.4 Stability connects two fronts

Because Phonon is deterministic, **its single-synthesis WER is representative**: the same text always yields the same audio. Because Pocket TTS varies from run to run, **its WER of 33.7% from one synthesis is only one sample** of a variable process; a second synthesis could be better or worse on any given sentence. That uncertainty does not rescue Pocket TTS (the failure is in a whole class of sentences, and its consistency data confirms real variability), but it means the exact figure should be read as indicative and a repeated-synthesis WER run would tighten it.

### 4.5 Licensing and consent

- **Phonon:** weights **CC BY-NC 4.0**. Fine for research, internal benchmarking and demos; **not for a commercial product** without a separate license from the provider.
- **Pocket TTS:** package MIT; the owner checked the model terms and found it usable; the weights are gated (accepting the terms on Hugging Face and logging in is required).
- **Piper:** engine GPL-3.0, which is copyleft and affects how it can be distributed or embedded; voice terms confirmed by the owner for the two catalog voices.
- **Cloned voices:** the two voices (Valentina, Emiliano) have recorded consent that covers internal benchmarking, published results, demo audio and human evaluation, for the content types used. Reference audio, generated clips and embeddings are never committed.
- The embedding model used for similarity is Apache-2.0 on its card; its training data (VoxCeleb) terms were not verified for commercial use. That affects only the measuring tool, not the engines.

## 5. Decision matrix

Ranking per front (1 is best; ties shown as equal; `n/a` where the front does not apply).

| Front | Phonon | Pocket TTS | Piper |
|---|---|---|---|
| First-sound latency | 1 | 2 | 3 |
| Raw speed and throughput | 2 | 3 | 1 |
| Memory and CPU cost | 1 | 3 | 2 |
| Start-up and cold-start cost | 1 | 3 | 2 |
| Intelligibility | 1 | 3 | 2 |
| Numbers, amounts, acronyms | 1 | 3 | 2 |
| Voice fidelity | 1 | 2 | n/a |
| Consistency across runs | 1 | 2 | n/a |
| Commercial license | 3 (non-commercial) | 1 | 2 (GPL-3.0) |
| Clones the target voice | yes | yes | no |

Phonon is first on 7 of 9 rankable fronts and never worse than second apart from the license. Pocket TTS is last on five of the nine fronts. Piper is the only engine whose weaknesses are structural rather than fixable (no cloning, a non-Colombian voice, a streaming granularity of one sentence).

This table is a summary, not a score: no weighting is applied because the project has not defined how much each front is worth. The weighting that matters most is simple: **a cloned voice is required and a commercial license may be required**, and these two constraints decide the outcome (section 7).

## 6. Confounds and limits

- **Different voices across engines.** Piper's Mexican voice, and no cloning, limit what can be said about it. Phonon and Pocket TTS share the same speaker, which makes their comparison fair on voice.
- **Single runs.** Performance has one run per engine and mode; intelligibility has one synthesis per sentence; background-load warnings appear on four of the six performance runs; the Pocket TTS runs were on battery with Low Power Mode on, which probably inflates its slowness, and its cold run being faster than its warm run points to this. Pocket TTS's speed gap versus Phonon is large enough that its direction is safe; its exact size is not.
- **Measuring instruments.** WER depends on Whisper and on the Spanish normalization rules; similarity depends on ECAPA-TDNN and was gated only with two speakers; both mix the engine with the instrument.
- **Not measured at all:** naturalness and prosody scored by several listeners (voice likeness was checked by one listener only, section 4.3b), behavior with several concurrent calls, network and streaming over a real connection, GPU, long sessions, and robustness to texts outside the corpus.
- **One reference recording per voice,** and results do not transfer automatically to other speakers.

## 7. Conclusions

1. **Technically, Phonon wins.** It is first in first-sound latency, memory, CPU, start-up, intelligibility (WER 1.4%, 0.0% on digit sequences), voice similarity (0.666, higher on 18 of 21 sentences) and repetition consistency (deterministic). No other engine beats it on more than raw throughput and load time, where Piper leads without cloning.
2. **Pocket TTS is not recommendable for numbers and amounts as it stands.** Its WER on digit sequences (47.4%) and pesos amounts is unacceptable for a call center, whatever its license advantage. It is fast enough for real time and does clone the voice, so the problem is correctness on specific sentence classes, which might be reduced by how the text is prepared (for example writing numbers as words); that is an untested hypothesis, not a finding.
3. **Piper is the intelligible, light fallback that does not clone.** It reads numbers well (1.6%) and amounts reasonably (4.4%), but delivers audio per sentence (163 ms typical, 317 ms at p95), uses many cores, uses a Mexican voice and cannot reproduce the target voice. It is a baseline, not a candidate for a cloned-voice deployment.
4. **The license is the deciding open question, not the metrics.** The metrics point to Phonon; the license says it is non-commercial. Which branch applies depends on the intended use:

   | Intended use | Recommended engine | Condition |
   |---|---|---|
   | Evaluation, internal benchmarking, demos, research | **Phonon** | within CC BY-NC 4.0 and the recorded consent |
   | Commercial product with the cloned voice | **Phonon with a commercial license**, if the provider offers one | to be obtained; if not, Pocket TTS only after fixing number and amount reading |
   | Commercial product, voice cloning not required | **Piper** | accept GPL-3.0 obligations and a non-Colombian voice |

5. **What the evidence supports and what it does not.** It supports the ranking of Phonon over Pocket TTS on every measured front, now including a human listening check that found Phonon's cloning almost perfect and clearly better than the others, and the unsuitability of Pocket TTS for numeric content as it stands. It does not support treating the human check as more than one listener's judgment, nor claiming that Phonon's lead over Piper on WER (1.5 points) is more than a trend. Piper was not part of the voice comparison because it does not clone.

## 8. Next steps, in order of value

1. **Resolve the Phonon license question** (commercial terms, or confirm the use is non-commercial). This decides the whole selection and costs no engineering.
2. **Extend the listening check** to a few more listeners and write down the ratings (the kit and its answer key are in `output/speaker/listening/`), so the human result can be quoted with numbers and also cover naturalness, not only likeness.
3. **Repeat synthesis for intelligibility** (at least 3 to 5 syntheses per sentence for Pocket TTS) to put an interval on its WER and see whether it is consistently bad on numbers.
4. **Test whether text preparation fixes Pocket TTS** on numbers and amounts (for example sending the `spoken` form of the sentence). If it does, Pocket TTS becomes the viable commercial option.
5. **Re-run performance on an idle, plugged-in machine** with power state recorded, and add a concurrent-calls test; neither was done and both change real deployment decisions.
6. **Add more voices** (a second consented speaker for each engine) so that fidelity conclusions do not rest on one reference recording.

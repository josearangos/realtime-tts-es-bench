> WER and CER measure intelligibility as heard by one recognizer, not naturalness; results reflect the recognizer and the engine together.

Recognizer: faster-whisper large-v3 (cpu/int8), ruleset 1, lexicon 1, corpus 1.0.0 subset main limit None.
Sampling variance across syntheses is not measured (one synthesis per sentence). Recognizer accuracy varies with regional accent; a rate here mixes the engine's Spanish variant with the recognizer's coverage of it.

## Overall

| engine | voice | WER | CER | S | D | I | accent-sensitive WER | n sentences | flagged | reliable |
|---|---|---|---|---|---|---|---|---|---|---|
| phonon | valentina-phonon | 1.4% | 0.7% | 23 | 3 | 1 | 1.6% | 123 | 0 | yes |
| piper | es_MX-claude-high | 2.9% | 1.4% | 37 | 11 | 11 | 3.2% | 123 | 0 | yes |
| pocket_tts | valentina-pocket | 33.7% | 27.6% | 228 | 125 | 321 | 34.2% | 123 | 0 | yes |

## Per tag

| engine | group | n sentences | reference words | WER | CER | S | D | I | accent-sensitive WER | low sample |
|---|---|---|---|---|---|---|---|---|---|---|
| phonon | tag:acronym | 13 | 226 | 3.5% | 1.8% | 5 | 3 | 0 | 3.5% | no |
| piper | tag:acronym | 13 | 226 | 4.0% | 1.1% | 7 | 2 | 0 | 4.0% | no |
| pocket_tts | tag:acronym | 13 | 226 | 33.6% | 26.1% | 34 | 40 | 2 | 33.6% | no |
| phonon | tag:amount_cop | 22 | 457 | 2.2% | 2.0% | 10 | 0 | 0 | 2.2% | no |
| piper | tag:amount_cop | 22 | 457 | 4.4% | 3.6% | 7 | 7 | 6 | 4.4% | no |
| pocket_tts | tag:amount_cop | 22 | 457 | 109.0% | 91.7% | 132 | 58 | 308 | 109.2% | no |
| phonon | tag:datetime | 21 | 385 | 1.3% | 1.2% | 5 | 0 | 0 | 1.3% | no |
| piper | tag:datetime | 21 | 385 | 4.4% | 2.8% | 8 | 4 | 5 | 4.4% | no |
| pocket_tts | tag:datetime | 21 | 385 | 25.7% | 19.5% | 72 | 16 | 11 | 26.8% | no |
| phonon | tag:hard_word | 16 | 278 | 1.8% | 0.3% | 4 | 0 | 1 | 1.8% | no |
| piper | tag:hard_word | 16 | 278 | 4.7% | 2.4% | 8 | 2 | 3 | 5.0% | no |
| pocket_tts | tag:hard_word | 16 | 278 | 10.4% | 7.8% | 18 | 7 | 4 | 10.8% | no |
| phonon | tag:long | 12 | 369 | 1.1% | 0.1% | 3 | 0 | 1 | 1.1% | no |
| piper | tag:long | 12 | 369 | 1.6% | 0.7% | 2 | 0 | 4 | 1.6% | no |
| pocket_tts | tag:long | 12 | 369 | 7.0% | 5.2% | 11 | 11 | 4 | 7.0% | no |
| phonon | tag:number | 10 | 190 | 0.0% | 0.0% | 0 | 0 | 0 | 0.0% | no |
| piper | tag:number | 10 | 190 | 1.6% | 0.7% | 2 | 1 | 0 | 1.6% | no |
| pocket_tts | tag:number | 10 | 190 | 47.4% | 36.4% | 46 | 42 | 2 | 48.9% | no |
| phonon | tag:proper_name | 12 | 197 | 3.0% | 1.0% | 6 | 0 | 0 | 3.0% | no |
| piper | tag:proper_name | 12 | 197 | 3.0% | 1.4% | 4 | 1 | 1 | 3.6% | no |
| pocket_tts | tag:proper_name | 12 | 197 | 11.2% | 6.7% | 17 | 4 | 1 | 11.2% | no |
| phonon | tag:question | 35 | 473 | 2.1% | 1.2% | 10 | 0 | 0 | 2.3% | no |
| piper | tag:question | 35 | 473 | 3.6% | 1.6% | 13 | 3 | 1 | 3.8% | no |
| pocket_tts | tag:question | 35 | 473 | 17.1% | 12.1% | 43 | 31 | 7 | 17.8% | no |
| phonon | tag:short | 12 | 45 | 0.0% | 0.0% | 0 | 0 | 0 | 2.2% | no |
| piper | tag:short | 12 | 45 | 2.2% | 0.9% | 1 | 0 | 0 | 2.2% | no |
| pocket_tts | tag:short | 12 | 45 | 0.0% | 0.0% | 0 | 0 | 0 | 2.2% | no |
| phonon | untagged | 8 | 113 | 0.9% | 0.2% | 1 | 0 | 0 | 3.5% | yes |
| piper | untagged | 8 | 113 | 1.8% | 0.3% | 2 | 0 | 0 | 4.4% | yes |
| pocket_tts | untagged | 8 | 113 | 0.9% | 0.2% | 1 | 0 | 0 | 3.5% | yes |

Tag groups overlap: a sentence with several tags is counted in each of them, so group rows do not add up to the overall row.

## Per campaign

| engine | group | n sentences | reference words | WER | CER | S | D | I | accent-sensitive WER | low sample |
|---|---|---|---|---|---|---|---|---|---|---|
| phonon | campaign:collections | 41 | 674 | 1.5% | 0.7% | 8 | 2 | 0 | 1.5% | no |
| piper | campaign:collections | 41 | 674 | 3.7% | 2.1% | 12 | 6 | 7 | 3.9% | no |
| pocket_tts | campaign:collections | 41 | 674 | 18.8% | 14.3% | 83 | 30 | 14 | 19.3% | no |
| phonon | campaign:inbound | 40 | 587 | 1.2% | 0.6% | 6 | 1 | 0 | 1.4% | no |
| piper | campaign:inbound | 40 | 587 | 2.2% | 0.9% | 11 | 1 | 1 | 2.2% | no |
| pocket_tts | campaign:inbound | 40 | 587 | 16.4% | 12.5% | 54 | 41 | 1 | 16.9% | no |
| phonon | campaign:outbound_sales | 42 | 739 | 1.4% | 0.7% | 9 | 0 | 1 | 1.8% | no |
| piper | campaign:outbound_sales | 42 | 739 | 2.8% | 1.2% | 14 | 4 | 3 | 3.4% | no |
| pocket_tts | campaign:outbound_sales | 42 | 739 | 61.0% | 51.9% | 91 | 54 | 306 | 61.6% | no |

---

The sections below are written by hand (the tables above are the tool's output; re-running `compare --out` overwrites this file, so re-append them).

## Conclusions

Measured by this project on 2026-11-03: Whisper `large-v3`, main corpus of 123 sentences, one synthesis per sentence per engine, ruleset 1.

1. **Phonon is the most intelligible engine in this run.** It has the lowest overall WER (1.4%) and CER (0.7%), and the lowest or tied-lowest error in nearly every tag group. It reads digit sequences (phone and account numbers) with 0.0% WER and amounts in pesos with 2.2%, which are the sentences a call center cannot afford to get wrong.
2. **Piper is a close second** (WER 2.9%, CER 1.4%). It is slightly behind phonon on amounts and numbers and roughly level on proper names. The gap between the two is a handful of words from a single synthesis each, so it is a trend, not proof of a real difference.
3. **Pocket TTS is clearly behind** (WER 33.7%). It garbles numbers (47% WER on the `number` group), amounts, and acronyms (34%). The amount group exceeds 100% WER because the recognizer sometimes loops on digits ("cero cero cero ..."), which uncapped insertions count in full. Even with the worst sentence removed, the overall WER is 18.6%, an order of magnitude above the other two.
4. **Numbers, amounts and acronyms are where engines differ most.** Long, plain sentences and questions are easy for all three (a few percent at most for phonon and piper); the spread between engines appears on the sentence types that carry money, dates and identifiers. A single overall WER hides this, so read the per-tag tables.
5. **Normalization changes the answer more than expected.** The first real run, before the thousands-separator fix, reported 6.0% for phonon and 19.1% for pocket TTS purely because the recognizer writes `$1,847,300` and the reference is spoken words. Any WER figure without a documented, tested normalization (and a stated reading rule for numerals) is not comparable.
6. **What the remaining errors look like.** For phonon and piper they are mostly recognizer-side or name-related: proper names ("Julián Ospina" heard as "Juliano Espina", "Movilar" as "Mobilar"), "PSE" written as the word "pes", and "pesos" heard as "dólares" in some amount sentences. These are shown by `errors`, and they illustrate that WER measures the engine and the recognizer together.
7. **Confounds to keep in mind.** The three engines used different voices: phonon and pocket TTS use cloned es-CO voices, piper uses a fixed Mexican Spanish voice, so accent and voice quality are mixed into the figures. One synthesis per sentence means sampling variance is not measured. Whisper may correct some mispronunciations, which would hide real engine errors. None of this is a naturalness measure.

### Winner: Phonon

**Phonon is the winning model of this experiment.**

- **Why on intelligibility:** lowest WER and CER overall, perfect on digit sequences, best on amounts, and no flagged or failed sentences (123 of 123 synthesized and scored).
- **Why for real-time use:** the performance results of feature 004 ([`results/perf/comparison.md`](../perf/comparison.md)) show it with the best time to first audio (about 8 ms), RTF about 0.056 (far faster than real time), and the lowest memory use. Piper is faster in raw RTF but delivers audio per sentence, so its first audio arrives later; Pocket TTS is the slowest and heaviest.
- **Why the margin over Piper is not overstated:** Piper is within about 1.5 points of WER, so if a deployment prefers a catalog voice with no cloning or consent steps, Piper is a reasonable choice. Against Pocket TTS the gap is large enough that the ranking is not in doubt for this corpus.
- **Before relying on it:** repeat the synthesis a few times to measure variance, and add human listening for naturalness and voice similarity, which this metric does not cover.

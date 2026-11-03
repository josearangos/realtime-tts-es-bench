# Intelligibility metrics (WER and CER)

> WER and CER measure intelligibility as heard by one recognizer, not naturalness; results reflect the recognizer and the engine together.

Intelligibility here means: a fixed speech recognizer transcribes what an engine said, and the transcript is compared with the sentence the engine was asked to say. Lower is better. It says nothing about voice quality, prosody or naturalness (that needs human listeners; see the constitution, Principle IV).

## Pipeline

Four stages joined by files, each runnable alone. Engines and the recognizer live in separate environments.

| Stage | Environment | Command | Output |
|-------|-------------|---------|--------|
| synthesize | the engine's venv | `python -m tts_bench.intelligibility synthesize ENGINE --voice NAME` | `output/intelligibility/<engine>-<voice>/` (WAVs and `manifest.json`, not tracked) |
| transcribe | `.venv-asr` | `python -m tts_bench.intelligibility transcribe AUDIO_DIR` | `results/intelligibility/<engine>-transcripts-<ts>.json` |
| score | any (stdlib + numpy) | `python -m tts_bench.intelligibility score TRANSCRIPTS_FILE` | `results/intelligibility/<engine>-<ts>.json` |
| compare / errors | any | `compare RESULTS...`, `errors RESULTS` | Markdown |

Only the main corpus subset is used, with one synthesis per sentence per engine. Sampling variance across syntheses is not measured, so a small WER difference between two engines (or two runs) should not be over-read.

## Definitions

- **Reference**: the sentence's `spoken` form when present, else its `text`, normalized.
- **WER** = (S + D + I) / number of reference words. **CER** = the same on the characters of the normalized string, single spaces counted. S, D, I come from a unit-cost Levenshtein alignment.
- **Not capped at 100%**: many insertions can push a rate above 1.0.
- **Alignment tie-break** is fixed: substitution, then deletion, then insertion, so the S, D, I counts are reproducible.
- **Pooling**: group and overall rates are `sum(errors) / sum(reference units)`, not the mean of per-sentence rates. Long sentences weigh more; a short sentence with one error has a high per-sentence rate but a small effect on the pooled rate.
- **Empty reference** (zero units after normalization): rate undefined, flagged `empty_reference`, excluded from pooled rates, counted in `n_sentences`.
- **Full failure**: a synthesis that failed, produced silence or no audio counts every reference word and character as a deletion (100%) and is flagged (`synthesis_failed`, `silent_audio`). Silence is zero samples or a peak amplitude below 1e-4 (about -80 dBFS); the recognizer is not run on it. A non-silent audio with an empty transcript is scored the same way and flagged `empty_transcript`.
- **Reliable**: a run is marked not reliable when more than 10% of its sentences are flagged. The run still finishes the whole corpus.
- **Groups**: `overall`, `campaign:<name>`, `tag:<name>` and `untagged`. A sentence with several tags counts in each tag group, so tag groups overlap. Groups under 10 sentences are marked `low_sample`.

## Normalization (ruleset version 1, lexicon version 1)

The same function is applied to the reference and to the transcript. Steps, in order:

1. Unicode NFC.
2. Lowercase.
3. Expand written forms (before punctuation is removed):
   - lexicon, whole tokens, case-insensitive: `pse`→`pe ese e`, `sms`→`ese eme ese`, `pqr`→`pe cu erre`, `tv`→`te ve`, `4g`→`cuatro ge`, `gb`→`gigas`, `nit`, `iva`. Adding an entry bumps `LEXICON_VERSION`.
   - currency: `$1.847.300` → `un millón ochocientos cuarenta y siete mil trescientos pesos`.
   - times: `3:00` → `tres`, `4:30` → `cuatro y media`.
   - percent: `20%` → `veinte por ciento`.
   - day 1 before a month: `1 de diciembre` → `primero de diciembre`.
   - numerals: `.` groups thousands, `,` is the decimal separator (`6,5` → `seis coma cinco`) except groups of exactly three digits (`1,847,300`, `305,872`), which are thousands; letters glued to digits are split (`A15` → `a quince`).
4. Remove punctuation and symbols.
5. Fold accents `á é í ó ú ü` (never `ñ`) for the primary figure. The accent-sensitive figure skips this step and is reported as secondary.
6. Collapse whitespace.

### Reading selection for numerals

A plain integer of two or more digits with no leading zero can be spoken as a cardinal (`4821` → `cuatro mil ochocientos veintiuno`) or digit by digit (`cuatro ocho dos uno`). The recognizer's choice between digits and words is formatting, not intelligibility, so for each such token in the **transcript** the reading closest (word edit distance) to the reference is used; ties go to the cardinal. The chosen reading is stored per sentence in `number_readings`. This cannot hide a word error: a wrong word is a different word under either reading. Tokens with a leading zero (`0045`), separators or decimals have a single reading. A reference without a `spoken` form has its numerals read as cardinals.

`tests/intelligibility/test_corpus_normalization.py` checks that the written `text` and the `spoken` form normalize to identical strings for every main and cloning sentence, and that sentences without `spoken` are touched only by the basic steps. That proves the rules cover the corpus without running any recognizer.

## Recognizer

`faster-whisper`, multilingual checkpoint `large-v3`, int8 on CPU. Settings are fixed and stored: `language="es"`, `beam_size=1`, `temperature=0`, `vad_filter=False`, `condition_on_previous_text=False`, no initial prompt. Recognizer name, checkpoint, license, library versions (`faster-whisper`, `ctranslate2`), settings and their hash are in every results file. `compare` refuses to merge results that differ in any of them, in the ruleset versions, or in corpus hash, subset or limit (exit code 3, naming the field). Hardware differences are listed but never block.

The transcript cache is keyed by `sha256(audio)` plus the settings hash, so identical audio with identical settings is never transcribed twice and different settings never share an entry.

## Limitations

- WER reflects the recognizer and the engine together. A recognizer may be weaker on some regional accents, and the engine's `spanish_variant` is stored with the results for that reason.
- A recognizer may "correct" a mispronounced word toward a likely one, hiding an engine error; it may also mishear a clear word.
- One synthesis per sentence: variance across syntheses of a sampling engine is not measured.
- Short sentences weigh little in pooled rates but heavily in their own per-sentence rate.
- The numeral and lexicon rules cover the corpus, not arbitrary Spanish text.

## Recognizer pinning and license

- Checkpoint: `Systran/faster-whisper-large-v3`, revision `edaa852ec7e145841d8ffdb056a99866b5f0a478` (Hugging Face), run with `faster-whisper` 1.2.1 and `ctranslate2` 4.8.5, int8 on CPU.
- License: **MIT**, confirmed on 2026-11-03 from the model's Hugging Face metadata (`license: mit`). Permissive, so no flag is raised in the results (`license_flag` is null). A different checkpoint would be flagged until its license is verified.
- The results record the checkpoint name `large-v3`; the revision above is recorded here, not in the files.

## Measured results (this project, 2026-11-03)

Main corpus (123 sentences), one synthesis per sentence, same recognizer and settings for all three engines. Full tables, per tag and per campaign: [`results/intelligibility/comparison.md`](../results/intelligibility/comparison.md). Voices are the ones used for the performance results.

| engine | voice | WER | CER | S | D | I |
|--------|-------|-----|-----|---|---|---|
| phonon | valentina-phonon | 1.4% | 0.7% | 23 | 3 | 1 |
| piper | es_MX-claude-high | 2.9% | 1.4% | 37 | 11 | 11 |
| pocket_tts | valentina-pocket | 33.7% | 27.6% | 228 | 125 | 321 |

How to read this:

- These are intelligibility figures as heard by Whisper `large-v3`, not naturalness, and they mix engine and recognizer. One synthesis per sentence, so the gap between phonon (1.4%) and piper (2.9%) is a few words and is within what a second synthesis could change; it should not be read as a ranking.
- pocket_tts is clearly worse: numbers, amounts and acronyms are often garbled (tag `number` and `amount_cop` are the worst groups in the comparison). Part of its pooled WER comes from one sentence (VEN-027) where the recognizer looped on "cero" about 300 times; WER is not capped by design. Without that sentence the pooled WER is 18.6%, still far above the other two.
- Remaining phonon and piper errors are mostly proper names ("Julián Ospina" heard as "Juliano Espina", "Movilar" as "Mobilar"), "PSE" heard as the word "pes", and "pesos" heard as "dólares" in some amount sentences. A recognizer substitution like that can be the recognizer's error as much as the engine's; `errors` shows the words involved.
- Normalization note found during the first real run: Whisper writes amounts with English-style commas (`$1,847,300`, `305,872`). Groups of exactly three digits after a comma are therefore read as thousands separators, and such a number may be read as a cardinal or digit by digit like other numerals.

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
- **Why for real-time use:** the performance results of feature 004 ([`results/perf/comparison.md`](../results/perf/comparison.md)) show it with the best time to first audio (about 8 ms), RTF about 0.056 (far faster than real time), and the lowest memory use. Piper is faster in raw RTF but delivers audio per sentence, so its first audio arrives later; Pocket TTS is the slowest and heaviest.
- **Why the margin over Piper is not overstated:** Piper is within about 1.5 points of WER, so if a deployment prefers a catalog voice with no cloning or consent steps, Piper is a reasonable choice. Against Pocket TTS the gap is large enough that the ranking is not in doubt for this corpus.
- **Before relying on it:** repeat the synthesis a few times to measure variance, and add human listening for naturalness and voice similarity, which this metric does not cover.

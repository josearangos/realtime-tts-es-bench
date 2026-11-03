# Quickstart: validating Intelligibility Metrics

Prerequisites: repo checked out, `.venv-core` (tests), the engine venvs from feature 001, and a new `.venv-asr` with `pip install -e ".[asr]"` for the recognizer. Voices as in feature 003 where an engine needs one.

## 1. Pure computation, no engine and no recognizer (FR-010, SC-001)
```
.venv-core/bin/python -m pytest tests/intelligibility -q
```
Expected: hand-calculated WER and CER cases pass; digits versus words give zero error; `normalize_pair(spoken, text)` gives identical strings for every corpus sentence with a `spoken` form.

## 2. End to end with the fake engine and the fake recognizer
```
.venv-core/bin/python -m tts_bench.intelligibility synthesize fake --limit 5
.venv-core/bin/python -m tts_bench.intelligibility transcribe output/intelligibility/fake-*/ --model fake   # fake recognizer: returns the expected text (WER 0); add --script to inject errors
.venv-core/bin/python -m tts_bench.intelligibility score results/intelligibility/fake-transcripts-*.json
```
Expected: a results file with per-sentence, per-tag, per-campaign and overall WER and CER; silent audio flagged and scored 100%.

## 3. A real engine (one per process, own venv)
```
.venv-piper/bin/python -m tts_bench.intelligibility synthesize piper --voice es_MX-claude-high
.venv-asr/bin/python  -m tts_bench.intelligibility transcribe output/intelligibility/piper-es_MX-claude-high
.venv-core/bin/python -m tts_bench.intelligibility score results/intelligibility/piper-transcripts-*.json
```
Repeat for each engine with the same `transcribe` settings (phonon: `--voice valentina-phonon`, pocket_tts: `--voice valentina-pocket`, in `.venv-phonon` / `.venv-pocket`).

## 4. Compare and diagnose
```
.venv-core/bin/python -m tts_bench.intelligibility compare $(ls results/intelligibility/*.json | grep -v transcripts)
.venv-core/bin/python -m tts_bench.intelligibility errors $(ls results/intelligibility/piper-2*.json | tail -1) --worst 10
```
Expected: tables per group with the intelligibility notice; `compare` exits 3 naming the field if recognizer settings differ; `errors` lists substitutions, deletions and insertions with the words.

## 5. Determinism (SC-004)
Run `score` twice on the same transcripts file and `diff` the `summary` and `sentences` sections: identical. Run `transcribe` twice on the same audio on the same machine: identical transcripts (engine-marked test).

Contracts: [contracts/intelligibility-cli.md](contracts/intelligibility-cli.md), [contracts/results-file.md](contracts/results-file.md). Entities: [data-model.md](data-model.md).

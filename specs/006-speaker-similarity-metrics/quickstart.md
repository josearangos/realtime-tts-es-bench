# Quickstart: validating Speaker Similarity and Consistency Metrics

Prerequisites: repo checked out, `.venv-core` (tests), the engine venvs from feature 001, the consented voices from feature 003 in `cloned_voices/`, and a new `.venv-spk` with `pip install -e ".[speaker]"` for the embedding model.

## 1. Pure computation, no engine and no model (FR-010, SC-001, SC-003)
```
.venv-core/bin/python -m pytest tests/speaker -q
```
Expected: identical vectors score within 0.01 of 1; different-speaker fixtures score clearly lower; CV on the fake engine with controlled duration variation matches the hand-computed value within 5%; near-zero mean is declined; EER matches hand-calculated cases; Piper is `not_applicable`.

## 2. End to end with the fake engine and the fake embedder
```
.venv-core/bin/python -m tts_bench.speaker synthesize fake --limit 5 --repetitions 3
.venv-core/bin/python -m tts_bench.speaker embed output/speaker/fake-default --model fake --reference output/speaker/fake-default/CLO-001-r1.wav
.venv-core/bin/python -m tts_bench.speaker score output/speaker/fake-default/embeddings.json --eer
```
Expected: a results file with per-sentence similarity, engine mean, duration and similarity CV, an EER record, and the FR-008 notice.

## 3. Real engines (one per process, own venv)
```
.venv-phonon/bin/python -m tts_bench.speaker synthesize phonon --voice valentina-phonon
.venv-pocket/bin/python -m tts_bench.speaker synthesize pocket_tts --voice valentina-pocket
.venv-spk/bin/python -m tts_bench.speaker embed output/speaker/phonon-valentina-phonon --extras-from <other voice dir>
.venv-spk/bin/python -m tts_bench.speaker embed output/speaker/pocket_tts-valentina-pocket
.venv-core/bin/python -m tts_bench.speaker score output/speaker/phonon-*/embeddings.json --eer --eer-from output/speaker/pocket_tts-*/embeddings.json
.venv-piper/bin/python -m tts_bench.speaker synthesize piper     # prints "not applicable"
```
Expected: the same embedder record in every file; Piper is not scored.

## 4. Compare
```
.venv-core/bin/python -m tts_bench.speaker compare results/speaker/*.json
```
Expected: tables with the notice first; exit 3 naming the field if embedder, checkpoint or settings differ.

## 5. Determinism and privacy (SC-005)
Run `score` twice on the same embeddings file and `diff` the result sections: identical. `git status` shows no audio, embeddings or reference files; `tests/speaker/test_privacy.py` passes.

Contracts: [contracts/speaker-cli.md](contracts/speaker-cli.md), [contracts/results-file.md](contracts/results-file.md). Entities: [data-model.md](data-model.md).

# Quickstart: Spanish Call Center Test Corpus

Prerequisites: Python 3.11, repository installed (`pip install -e ".[dev]"`). No network needed.

1. **Validate the shipped corpus**
   `python -m tts_bench.corpus validate`
   Expected: exit code 0, at least 100 main sentences, at least 25 per campaign, every feature tag at 10 or more, hash matches `VERSION.json`.

2. **Check the cloning subset against a reference transcript**
   `python -m tts_bench.corpus validate --transcripts cloned_voices/<voice>/transcript.txt`
   Expected: overlap status `passed`. Without transcripts, status is `not run`.

3. **Load from code**
   `from tts_bench.corpus import load_corpus; c = load_corpus(); print(c.version, len(c.sentences))`
   Expected: version string and a count of at least 100.

4. **Prove validation catches problems**
   Run the tests: `pytest tests/corpus`. Fixture corpora with a duplicate id, a missing spoken reading, a count below minimum, and a cloning sentence copied from a transcript each fail with the matching error.

5. **Release a change**
   Edit a sentence, run validation (expect a hash mismatch error), then update `VERSION.json` and `CHANGELOG.md` and validate again (expect success).

Contract details: [contracts/corpus-interface.md](contracts/corpus-interface.md). Fields and rules: [data-model.md](data-model.md).

## Deviations noted while running (T033)

- Step 2: no reference transcripts existed, so Whisper (`small`, Spanish) transcribed the two reference audios into `cloned_voices/valentina/transcript.txt` and `cloned_voices/emiliano/transcript.txt` (git-ignored). With them the overlap status is `passed`. The transcripts are automatic and may contain recognition errors.
- Step 5: while the version is `0.x`, editing a sentence without `stamp` produces a `hash_mismatch` **warning** (research R11), not an error; the error applies from `1.0.0`. Run `python -m tts_bench.corpus stamp` after edits.
- Use `python -m tts_bench.corpus ...` from the repository root after `pip install -e ".[dev]"` (or `PYTHONPATH=src`).

# Contract: Corpus Interface

## Loading (library)

```text
load_corpus(path=None, subset="main") -> Corpus
Corpus.version      -> str        e.g. "1.0.0"
Corpus.content_hash -> str
Corpus.sentences    -> tuple[Sentence, ...]   ordered by id
Corpus.by_campaign(name) / by_tag(name) / by_scenario(name)
```

- Loading validates the structure and raises a clear error naming the line when a record is malformed; it does not run the heavier coverage rules.
- Every result file written by other features MUST include `corpus_version` and `corpus_hash` taken from the loaded corpus. `corpus_stamp(corpus)` returns exactly these two keys for embedding. Enforcing this in result files belongs to the features that write them.
- Order is by id, and never changes within one version.

## Validation (command)

```text
python -m tts_bench.corpus validate [--transcripts PATH ...] [--path DIR]
```

- Exit code 0: no errors. Exit code 1: one or more errors. Warnings do not change the exit code.
- Output: counts per campaign, scenario, and tag; list of errors and warnings; transcript overlap status (`passed`, `failed`, `not run`).
- Makes no network access.

```text
python -m tts_bench.corpus stamp
python -m tts_bench.corpus validate --release
```

- `stamp` rewrites counts and `content_sha256` in `VERSION.json`. A hash mismatch is a warning for `0.x` versions and an error from `1.0.0`.
- `--release` additionally fails if any sentence has `reviewed` false.

## Error classes

Missing field, duplicate id, empty text, unknown enum value, count below minimum, missing spoken reading, spoken reading containing digits or symbols, tag inconsistent with text, duplicate or near-duplicate text, banned phrase in collections, cloning overlap, hash mismatch with `VERSION.json`.

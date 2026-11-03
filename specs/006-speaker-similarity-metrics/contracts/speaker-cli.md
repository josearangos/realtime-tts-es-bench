# Contract: speaker similarity CLI and library

## CLI

```
python -m tts_bench.speaker synthesize ENGINE
    [--voice NAME] [--voices-dir cloned_voices]
    [--repetitions N]                    default 5; repetition 1 is the designated run
    [--limit N]                          first N cloning sentences only (stored)
    [--out output/speaker]
python -m tts_bench.speaker embed AUDIO_DIR
    [--model ecapa|fake] [--script FILE.json] [--device cpu]
    [--extras-from AUDIO_DIR...]         other voices' references/clips used as different-speaker material
    [--out output/speaker]
python -m tts_bench.speaker score EMBEDDINGS_FILE [--eer] [--eer-from EMBEDDINGS_FILE...] [--out results/speaker]
python -m tts_bench.speaker compare RESULTS_FILE... [--out FILE.md]
```

- `synthesize` runs one engine in one process on the `cloning` subset. An engine with `supports_cloning=False` exits 0 after writing nothing and printing `not applicable: <engine> does not clone voices` (FR-006). `ENGINE=fake` is available for tests. Exit 2 if the engine cannot load.
- `embed` embeds the voice's reference and every clip with one embedder and writes `embeddings.json` next to the audio (not tracked). `--model fake` selects `FakeEmbedder` (scripted vectors), never for reported results. Exit 2 if the model or weights are missing, with an install hint.
- `score` needs no engine and no model. It computes designated-run similarity, per-engine summary, consistency across repetitions, warnings, and with `--eer` the EER from pairs built per research R5 (pooled with `--eer-from` for other engines). Exit 1 on a missing or malformed file.
- `compare` prints Markdown tables: per engine similarity (mean, sd, n scored, flagged), consistency (duration CV, similarity CV), EER once, and a `not applicable` row for non-cloning engines. Exit 3 on a refused merge, naming the differing field (embedder name, checkpoint, settings, corpus hash, reference recording).
- Every printed report starts with the notice: "Speaker similarity scores come from one embedding model and are not a substitute for human judgment; a score near 1 does not guarantee the voice sounds identical."

## Library

```python
cosine_similarity(a, b) -> float                       # pure
coefficient_of_variation(values) -> CV                 # {value|None, status: ok|near_zero_mean|fewer_than_two}
equal_error_rate(same_scores, different_scores) -> EER # pure; available false below 2 per kind
score_embeddings(embeddings_file, corpus, *, engine) -> ResultsFile   # pure
compare_results(files) -> str                          # Markdown
```

All pure functions take plain lists and arrays, so they run with no engine and no model (FR-010).

## Errors

| Situation | Behaviour |
|-----------|-----------|
| Non-cloning engine | `not_applicable`, no files, never scored or penalized |
| Engine not installed / weights missing | `synthesize` exit 2 with the adapter's hint |
| Sentence fails or is silent | recorded; excluded from the mean, counted and flagged |
| Clip shorter than 3.0 s | flagged `short_audio`, still scored, warning printed |
| Embedding model or weights missing | `embed` exit 2 with hint; no file |
| Zero-norm embedding | flagged as failure, no score |
| Fewer than 2 repetitions | consistency `not available` |
| Near-zero mean | CV declined, marked unreliable |
| EER with fewer than 2 pairs of a kind | `not available`, reason stored |
| `compare` inputs differ in embedder, checkpoint, settings, corpus hash or reference | refuse (exit 3) naming the field |
| Unknown `schema_version` | refuse with a message |

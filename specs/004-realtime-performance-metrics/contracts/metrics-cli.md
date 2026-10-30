# Contract: metrics CLI and library

## CLI

```
python -m tts_bench.metrics run ENGINE --mode {cold,warm}
    [--voice NAME] [--voices-dir cloned_voices]
    [--subset {main,cloning}]            default main
    [--repetitions N]                    default 5
    [--warmup N]                         default 3, warm mode only
    [--load-threshold X]                 default 0.25 (load average per core)
    [--limit N]                          first N sentences only (smoke runs; stored in config)
    [--out results/perf]
python -m tts_bench.metrics compare FILE... [--allow-mixed-hardware] [--out FILE.md]
```

- `run` loads one engine, runs the protocol, writes one results file, prints its path and a short summary. Exit 0 on success even if some sentences failed (see `reliable`); exit 2 if the engine cannot load; exit 1 on usage errors.
- `compare` prints Markdown tables (one per mode) with columns: engine, voice, granularity, load time, TTFA p50/p95, RTF p50/p95, throughput, peak RAM, CPU, VRAM, reliable, n. Exit 3 on a refused merge, naming the differing fields.
- Voice: resolved through `LocalVoiceLibrary` before timing; engines whose `voice_kind` needs none ignore `--voice`. `ENGINE=fake` is available for tests and examples.

## Library

```python
run_benchmark(adapter, corpus, voice, *, mode, repetitions=5, warmup=3, ...) -> ResultsFile
summarize(measurements, *, load_time_ms, ...) -> RunSummary          # pure
compare_results(files, *, allow_mixed_hardware=False) -> str         # Markdown
```

`summarize` and the percentile helper take plain lists, so they run with no engine (FR-010).

## Errors

| Situation | Behaviour |
|-----------|-----------|
| Engine not installed / weights missing | exit 2 with the adapter's hint; no file |
| Sentence fails | recorded `failed`, run continues |
| Empty audio | recorded `invalid`, run continues |
| `compare` inputs differ in hardware key, corpus, subset, `limit`, or locality | refuse (exit 3); `--allow-mixed-hardware` only lifts the hardware check |
| Results file has unknown `schema_version` | refuse with a message |

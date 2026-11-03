# Real-time performance metrics

Measure one engine in one mode and write a results file:

```
python -m tts_bench.metrics run ENGINE --mode {cold,warm} [--voice NAME] [--repetitions 5] [--warmup 3] [--limit N]
python -m tts_bench.metrics compare results/perf/A.json results/perf/B.json [--allow-mixed-hardware] [--out FILE.md]
```

`ENGINE=fake` needs no weights and no network. Real engines each run in their own venv (one engine per process): activate the engine's venv, run `run`, repeat for the next engine, then `compare` the files from any venv.

## Metric definitions

| Metric | Start instant | End instant | Unit |
|--------|---------------|-------------|------|
| Load time | just before `adapter.load()` | `load()` returns | ms |
| Generation time | just before the synthesis call (`request_started_ns`) | last audio delivered (`finished_ns`) | ms |
| TTFA | `request_started_ns` | first non-empty audio chunk delivered | ms |
| RTF | n/a | n/a | generation time / audio duration (lower is faster than real time) |
| Chunk latency | `request_started_ns` | each chunk's delivery; gap = since previous chunk | ms |
| Throughput | first measured request start in a repetition | last measured request finish in that repetition | audio s per wall s (run value: median over repetitions) |
| First-request time | cold only: start of the first request | its last audio | ms |

Clock: `time.perf_counter_ns()` (monotonic). Audio duration: samples per channel divided by the sample rate as produced by the engine, never resampled. Percentiles use linear interpolation over all valid sentence x repetition values.

## Cold and warm

- **Cold**: `load()` is timed, then the first corpus sentence is the *first request*, reported apart (with its penalty over the steady-state median) and excluded from the steady-state figures.
- **Warm**: after `load()`, `--warmup` requests run and are discarded; every repetition is measured in full. Load time is reported in both modes.

## Reading the results

- `"not available"` means the figure cannot be measured, never that it was estimated. TTFA is `"not available"` for engines that do not stream (granularity `none`); for `sentence` granularity TTFA equals sentence latency and the granularity is shown next to it. VRAM is `"not available"` without an NVIDIA tool or CUDA torch; on unified-memory machines memory is counted under RAM.
- `reliable: false` means more than 10% of the steady-state requests failed or returned empty audio. Those requests stay in the raw data as `failed` / `invalid` and are never given an RTF.
- `p95_low_sample: true` means fewer than 20 values back the p95.
- `background_load.warning` is indicative: it uses the lagging 1-minute load average per core (default threshold 0.25).
- Peak RAM is the process lifetime peak (`ru_maxrss`), read after load and after the measured phase.

## Why `compare` refuses

Results are comparable only on the same hardware, corpus version and hash, subset, `--limit` and locality. Hardware identity is CPU model, logical cores, RAM (GiB), GPU model, OS name and major version. Different hardware is refused unless `--allow-mixed-hardware` (which lifts only that check); differences in library versions or thread settings are listed but do not block. Cold and warm results are always shown in separate tables. A refused merge exits 3 and writes nothing.

Changing a definition above requires a spec update, a `schema_version` bump, and a note in the report.

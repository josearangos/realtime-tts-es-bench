# Contract: results file (JSON, `schema_version: 1`)

```json
{
  "schema_version": 1,
  "environment": {
    "hardware": {"cpu_model": "", "physical_cores": 0, "logical_cores": 0, "ram_gib": 0,
                 "gpu_model": null, "os_name": "", "os_release": "", "hardware_key": ""},
    "software": {"python": "", "libraries": {"numpy": ""}, "tts_bench_version": "", "git_commit": ""},
    "engine": {"name": "", "engine_version": "", "model_id": "", "spanish_variant": "",
               "streaming_granularity": "chunk|sentence|none", "locality": "local",
               "voice": {"name": "", "kind": "", "checksum": null}},
    "config": {"mode": "cold|warm", "repetitions": 5, "warmup": 3, "subset": "main",
               "limit": null, "thread_settings": {}, "load_threshold": 0.25},
    "corpus": {"corpus_version": "", "corpus_hash": ""},
    "command": "",
    "started_utc": ""
  },
  "summary": {},
  "resources": {},
  "measurements": []
}
```

Shapes of `summary`, `resources` and `measurements[]` are in [data-model.md](../data-model.md). Every key under `environment` is always present; unknown values use `null` plus a reason, never omission (SC-003). Unavailable metrics are the string `"not available"` with a `*_note` sibling, never an estimate.

## Metric definitions (also in `docs/metrics.md`)

| Metric | Start instant | End instant | Unit |
|--------|---------------|-------------|------|
| Load time | just before `adapter.load()` | `load()` returns | ms |
| Generation time | just before the synthesis call (`request_started_ns`) | last audio delivered (`finished_ns`) | ms |
| TTFA | `request_started_ns` | first non-empty audio chunk delivered | ms |
| RTF | n/a | n/a | generation time / audio duration |
| Chunk latency | `request_started_ns` | each chunk's delivery; gap = since previous chunk | ms |
| Throughput | first measured request start in a repetition | last measured request finish in that repetition | audio s per wall s |
| First-request time | cold only: start of the first request | its last audio | ms |

Clock: `time.perf_counter_ns()` (monotonic). Audio duration: samples per channel divided by the sample rate as produced by the engine, never resampled.

Changing any definition above requires a spec update, a `schema_version` bump, and a note in the report (Constitution, Development Workflow).

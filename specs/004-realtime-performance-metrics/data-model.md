# Data Model: Real-Time Performance Metrics

## Measurement (one sentence in one repetition)

| Field | Type | Notes |
|-------|------|-------|
| sentence_id | string | corpus id, e.g. `COB-001` |
| repetition | int | 1-based; warm-up requests are not stored as measurements |
| phase | `first_request` / `steady` | `first_request` only in cold mode, one per run |
| status | `ok` / `failed` / `invalid` | `invalid` = empty audio |
| error | string or null | message when not `ok` |
| audio_seconds | float or null | null unless `ok` |
| generation_ms | float or null | request start to last audio |
| rtf | float or null | generation time / audio duration |
| ttfa_ms | float or null | null means "not available" (granularity `none`) or not `ok` |
| chunks | list of {index, at_ms, gap_ms} | empty unless granularity is `chunk` or `sentence` and chunks exist |
| network_time_ms | float or null | reserved for remote engines |

Rules: `rtf` is never computed from zero audio duration (such results are `invalid`). Only `ok` + `steady` measurements enter summaries.

## Run Summary (per engine, mode, machine)

| Field | Notes |
|-------|-------|
| n_ok, n_failed, n_invalid, n_total | counts of steady-state measurements |
| reliable | false when failed + invalid > 10% of total |
| ttfa_ms | {p50, p95, mean, n, p95_low_sample} or "not available" |
| rtf | {p50, p95, mean, n, p95_low_sample} |
| generation_ms | {p50, p95, mean} |
| throughput_audio_s_per_s | median over repetitions, plus the per-repetition list |
| load_time_ms | cold and warm: `load()` duration |
| first_request | cold only: {sentence_id, generation_ms, ttfa_ms, rtf}; first-request penalty = its generation_ms minus the steady p50 |
| warmup | warm only: {requests, discarded: true} |

## Resource Use

| Field | Notes |
|-------|-------|
| peak_ram_mib_after_load / peak_ram_mib_final | normalized MiB |
| ram_method | e.g. `getrusage.ru_maxrss (bytes on darwin, KiB on linux)` |
| cpu_percent_of_one_core | measured phase; may exceed 100 |
| logical_cores | for interpretation |
| peak_vram_mib | number or "not available" with `vram_note` |
| background_load | {before, after, per_core_threshold, warning: bool} |

## Environment Record

hardware: `cpu_model`, `physical_cores`, `logical_cores`, `ram_gib`, `gpu_model`, `os_name`, `os_release`, `hardware_key`
software: `python`, `libraries` {name: version}, `tts_bench_version`, `git_commit`
engine: `name`, `engine_version`, `model_id`, `spanish_variant`, `streaming_granularity`, `locality`, `voice` {name, kind, checksum or null}
config: `mode`, `repetitions`, `warmup`, `subset`, `thread_settings`, `load_threshold`
corpus: `corpus_version`, `corpus_hash`
command: the invocation as `python -m tts_bench.metrics <args>` (module path, not the absolute `sys.argv[0]`); absolute paths in arguments are stored relative to the repository root or as `<abs-path>`, so no user name or home directory is stored
timestamps: `started_utc`

## Results File

`{ schema_version, environment, summary, resources, measurements[] }`, one per run. See [contracts/results-file.md](contracts/results-file.md).

## Relationships

Results File 1—1 Environment Record, 1—1 Run Summary, 1—1 Resource Use, 1—N Measurement. `compare` reads many Results Files and groups by mode.

## State

Run protocol: `load` → (`first_request` if cold | `warm-up` if warm) → `repetitions` → `summarize` → `write`. A failure inside a request is recorded and the protocol continues; a failure in `load` aborts with the adapter's install/weights hint and writes no file.

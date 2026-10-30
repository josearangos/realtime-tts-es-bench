# Research: Real-Time Performance Metrics

## R1. Process model and cold/warm protocol
- **Decision**: One CLI invocation = one process = one engine = one mode. The adapter guard already enforces one engine per process (FR-001). **Cold**: `load()` is timed (load time), then the first corpus sentence is the *first request* (reported separately as first-request time and excluded from steady-state figures), then the remaining sentences of repetition 1 and all later repetitions are steady-state. **Warm**: after `load()`, `--warmup` requests (default 3) on the first corpus sentences run and are discarded; every repetition after that is measured in full.
- **Rationale**: Matches the spec: cold reports load and first request apart from steady state; warm excludes warm-up. A fresh process per run keeps resource figures clean (Principle III).
- **Alternatives**: spawning a subprocess per repetition (rejected: slow, and cold is defined as first-in-process); dropping the OS file cache for "truly cold" (rejected: needs root and varies by OS; spec assumes model files are already cached).

## R2. Metric definitions (instants)
- **Generation time**: `request_started_ns` (just before the adapter call) to `finished_ns` (last audio delivered), from the adapter result.
- **Audio duration**: `samples / sample_rate / channels`-aware length of the returned audio.
- **RTF** = generation time / audio duration (lower is faster than real time).
- **TTFA**: the delivery instant of the first chunk with at least one sample (clarified) minus `request_started_ns`. The runner finds that chunk in `result.chunks`; it does not use `first_audio_ns`, which marks the first chunk even when empty. "Not available" when granularity is `none`. For `sentence` granularity TTFA equals sentence latency and the granularity is stored next to it.
- **Throughput** (clarified): audio seconds produced per wall-clock second for a repetition, from the first measured request start to the last measured request finish; the run value is the median over repetitions. Reported next to overall RTF (its inverse).
- **Chunk latency**: for streaming engines, per chunk the time since request start and the gap since the previous chunk.
- **Rationale**: uses timestamps the adapters already take with `perf_counter_ns`, so the harness adds no timing code in the hot path.

## R3. Percentiles
- **Decision**: p50 and p95 by linear interpolation (NumPy default) over pooled valid sentence x repetition values, with the sample count `n` stored. Fewer than 20 values still reports p95 but adds `p95_low_sample: true`.
- **Rationale**: simple, reproducible by anyone from the raw data (Principle V). Nearest-rank was rejected because it jumps with small `n`.

## R4. Resource measurement without new dependencies
- **Peak RAM**: `resource.getrusage(RUSAGE_SELF).ru_maxrss`, read after load and after the measured phase; unit differs (bytes on macOS, kilobytes on Linux), so the method name and normalized MiB are both stored. It is a process lifetime peak, so the delta shows synthesis growth beyond load.
- **CPU**: process CPU time (`time.process_time`) over the measured phase divided by wall time, stored as percent of one core (may exceed 100 for multi-threaded engines) plus the number of logical cores.
- **VRAM**: `nvidia-smi` query for peak used memory when present, or `torch.cuda.max_memory_allocated` if torch is already loaded by the engine; otherwise `not available` with a reason. Apple unified memory is covered by RAM and recorded as such.
- **No sampling thread**: a polling thread would compete for the interpreter lock and distort latency; peaks are read after the fact.
- **Alternatives**: `psutil` (rejected: new dependency, current-RSS sampling not needed).

## R5. Background load
- **Decision**: read the 1-minute load average divided by logical cores before and after the run (`os.getloadavg`); if either exceeds `--load-threshold` (default 0.25) store a warning in the results. The load average lags, so the check is documented as indicative.
- **Alternatives**: sampling idle CPU for a few seconds before the run (rejected: delays every run and needs a sampler).

## R6. Failed and empty results
- **Decision**: add `EmptyAudioError(SynthesisError)` in `core/errors.py` and raise it where the adapter currently raises "produced no audio"; the runner also treats a result with zero samples as empty. Failed sentences get `status: failed` with the message; empty ones get `status: invalid`. Both stay in the raw data and are excluded from summaries. A run with more than 10% failed or invalid sentences is stamped `reliable: false` (clarified).
- **Rationale**: distinguishing the two needs a type, not message matching. The subclass keeps all existing handlers working.

## R7. Environment record and hardware identity
- **Decision**: CPU model (`sysctl machdep.cpu.brand_string` or `/proc/cpuinfo`), physical and logical cores, RAM (`sysctl hw.memsize` or `os.sysconf`), GPU model when detectable, OS name and release, Python version, thread settings (`OMP_NUM_THREADS`, `MKL_NUM_THREADS`, `VECLIB_MAXIMUM_THREADS`, and torch thread count if torch is imported), library versions (`importlib.metadata` for numpy, tts_bench, torch if present, and the engine package), engine and model revision from the descriptor, corpus version and hash, voice name and checksum, git commit, and the command, recorded as `python -m tts_bench.metrics <args>` with absolute paths made relative to the repository root (or replaced by `<abs-path>`). Hostname and user name are not stored.
- **Hardware key** (clarified): CPU model, logical core count, RAM size rounded to GiB, GPU model, OS name and major version. Compare refuses when keys differ; other differences are listed but do not block.
- **Alternatives**: whole-record equality (rejected: a library bump would block valid comparisons).

## R8. Compare rules
- **Decision**: `compare` refuses with a clear message when the inputs differ in hardware key (override `--allow-mixed-hardware`), corpus version/hash, subset or `--limit` value, or locality (local vs remote). Cold and warm are always shown in separate tables. Refusal exits non-zero and writes nothing.
- **Rationale**: Principle III; SC-005 asks for 100% refusal without the override.

## R9. Remote engines
- **Decision**: no remote adapter exists yet. The results file carries `locality` (default `local`, taken from the descriptor if it ever declares one) and a nullable `network_time_ms` per measurement. Compare refuses to mix localities. A future remote adapter fills the network field; this feature adds no network code.

## R10. Offline operation and timing hygiene
- **Decision**: nothing in the package imports a network library. A test blocks socket creation and runs the fake engine. The runner calls `gc.collect()` once before each repetition, never between requests, so it cannot enter a throughput window; audio is never written inside a timed region. Voices are resolved before timing.
- **Rationale**: SC-004 and SC-001/SC-002.

## R11. Output location
- **Decision**: `results/perf/<engine>-<mode>-<UTC timestamp>.json`, tracked in git. Files contain no audio and no voice material, so Principle VI is unaffected.

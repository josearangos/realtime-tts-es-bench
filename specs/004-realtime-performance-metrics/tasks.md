---

description: "Task list for Real-Time Performance Metrics"
---

# Tasks: Real-Time Performance Metrics

**Input**: Design documents from `/specs/004-realtime-performance-metrics/`

**Prerequisites**: plan.md, spec.md, research.md, data-model.md, contracts/metrics-cli.md, contracts/results-file.md, quickstart.md

**Tests**: Included. Constitution Principle VIII requires every functional requirement to map to a checkable scenario and metric code to be testable without weights. All tests use the fake engine or synthetic measurement lists: no weights, no network.

**Organization**: Grouped by user story. Paths follow plan.md (`src/tts_bench/metrics/`, `tests/metrics/`). US1 delivers measurement, summaries, results file and a `run` CLI for steady-state repetitions; US2 adds the cold/warm protocol on top; US3 adds resources, the full environment record and `compare`.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: can run in parallel (different files, no dependency on unfinished tasks)
- **[Story]**: US1 (latency and speed for one engine), US2 (cold, warm and load time), US3 (resources, environment, hardware guard)

---

## Phase 1: Setup

- [ ] T001 Create the package `src/tts_bench/metrics/__init__.py` (empty for now), the test package `tests/metrics/__init__.py`, and `results/perf/.gitkeep`; confirm with `git check-ignore -v results/perf/x.json` that results files are NOT ignored (they are tracked, per research R11)

---

## Phase 2: Foundational (blocks all user stories)

**Purpose**: empty-audio error type, fake-engine controls, shared data types, test fixtures

- [ ] T002 [P] Add `EmptyAudioError(SynthesisError)` to `src/tts_bench/core/errors.py` and raise it in `src/tts_bench/core/adapter.py` where `synthesize` currently raises "produced no audio" (keep the same message); add `tests/unit/test_empty_audio_error.py` with a throwaway adapter whose `_iter_engine` yields nothing, asserting `EmptyAudioError` is raised and is also caught as `SynthesisError`; run the existing `tests/unit` and `tests/contract` suites to confirm no regression (research R6)
- [ ] T003 [P] Extend `FakeAdapter` in `src/tts_bench/adapters/fake.py` with three optional keyword arguments, all defaulting to no effect: `load_delay_s: float = 0.0` (sleep in `_load`), `fail_texts: frozenset[str] = frozenset()` (raise `RuntimeError("fake engine failure")` before yielding for those texts) and `empty_texts: frozenset[str] = frozenset()` (yield no audio for those texts, so the adapter raises `EmptyAudioError`); existing tests must still pass
- [ ] T004 [P] Implement the data types in `src/tts_bench/metrics/model.py` as frozen dataclasses with `to_dict()` / `from_dict()`: `ChunkTiming(index, at_ms, gap_ms)`; `Measurement` with fields `sentence_id`, `repetition` (1-based), `phase` (`first_request` / `steady`), `status` (`ok` / `failed` / `invalid`), `error`, `audio_seconds`, `generation_ms`, `rtf`, `ttfa_ms`, `chunks`, `network_time_ms`; `RunSummary` and `ResultsFile` (`schema_version`, `environment`, `summary`, `resources`, `measurements`) per data-model.md. Quote in a docstring: "`rtf` is never computed from zero audio duration (such results are `invalid`). Only `ok` + `steady` measurements enter summaries." and "`ttfa_ms`: null means 'not available' (granularity `none`) or not `ok`"; `network_time_ms` is reserved and always null in this feature
- [ ] T005 [P] Create `tests/metrics/conftest.py` with: a `make_adapter(**fake_kwargs)` fixture returning a loaded-on-demand `FakeAdapter` (the autouse guard reset in `tests/conftest.py` already applies), a `voice` fixture (`VoiceReference("default", "fixed_voice", "memory://default")`), and a `mini_corpus(n)` helper that returns a `Corpus` holding the first `n` sentences of `load_corpus()` (same order as the shipped corpus)

**Checkpoint**: foundation ready, user stories can start

---

## Phase 3: User Story 1 - Measure latency and speed for one engine (Priority: P1)

**Goal**: one command over the corpus yields per-sentence and summary TTFA, RTF, generation time and throughput, with p50 and p95.

**Independent Test**: fake engine with first-chunk delay 0.2 s, chunk interval 0.05 s, 4 chunks and 1.0 s of audio: TTFA about 200 ms, generation about 350 ms, RTF about 0.35, throughput about 2.86 audio s per wall s, each within 5% (SC-001).

- [ ] T006 [P] [US1] Tests in `tests/metrics/test_stats.py` on plain lists (no engine): linear-interpolation percentiles (values 1..5 give p50 = 3.0 and p95 = 4.8); `summarize` ignores `failed` and `invalid` measurements and the `first_request` phase; `p95_low_sample` is true when n < 20; `reliable` is false when failed + invalid exceed 10% of total and true at exactly 10%; TTFA summary is the string `"not available"` when no measurement has a TTFA; throughput is the median over repetitions and the per-repetition list is kept (FR-002, FR-003, FR-013)
- [ ] T007 [P] [US1] Tests in `tests/metrics/test_runner_fake.py`: the independent-test figures above for granularity `chunk` within 5%; per-chunk `at_ms` and `gap_ms` recorded for a streaming fake (FR-012); granularity `none` gives `ttfa_ms = None` and no chunks; granularity `sentence` records TTFA and the stored granularity (FR-008); an engine whose first chunk is empty has its TTFA measured at the first non-empty chunk (add a fake-engine option or a throwaway subclass that yields a zero-sample chunk first) (clarified TTFA); with `fail_texts` one sentence is `failed` with its error and the run continues; with `empty_texts` that sentence is `invalid`, never given an RTF (FR-013); the corpus order of measurements equals the corpus order (FR-015)
- [ ] T008 [US1] Implement `src/tts_bench/metrics/stats.py`: `percentile(values, q)` using linear interpolation (NumPy default), and `summarize(measurements, ...)` returning a `RunSummary` with `n_ok`, `n_failed`, `n_invalid`, `n_total`, `reliable` (false when failed + invalid > 10% of total), `ttfa_ms` / `rtf` / `generation_ms` as `{p50, p95, mean, n, p95_low_sample}` (`p95_low_sample` true when n < 20), TTFA as `"not available"` (with `ttfa_note`) when none exists, and `throughput_audio_s_per_s` as the median over repetitions plus the per-repetition list; only `ok` + `steady` measurements enter summaries (FR-003, FR-013)
- [ ] T009 [US1] Implement `src/tts_bench/metrics/runner.py`: `measure_request(adapter, sentence, voice, repetition, phase)` calls `adapter.synthesize`, derives `audio_seconds` (samples per channel / sample rate), `generation_ms` (`finished_ns - request_started_ns`), `rtf` (generation time / audio duration), `ttfa_ms` (`produced_at_ns` of the first chunk in `result.chunks` whose `samples.size > 0`, minus `request_started_ns`; null when granularity is `none`, when there are no chunks, or when every chunk is empty; never taken from `first_audio_ns`, which can mark an empty chunk), chunk timings from `result.chunks`; maps `EmptyAudioError` and zero-sample audio to `invalid`, any other `TTSBenchError` to `failed` with the message; never writes audio and does not call `gc.collect()` itself. `run_repetitions(adapter, corpus, voice, repetitions)` calls `gc.collect()` once before each repetition (never between requests), runs the corpus in corpus order per repetition and computes each repetition's wall-clock window (first measured request start to last measured request finish) for throughput (FR-002, FR-012, FR-013, FR-015)
- [ ] T010 [US1] Implement `src/tts_bench/metrics/results.py`: `write_results(results_file, out_dir)` to `results/perf/<engine>-<mode>-<UTC timestamp>.json` (before US2 adds `--mode`, the mode segment is the placeholder `steady`) and `read_results(path)` that refuses an unknown `schema_version` with a clear message; for this story the environment block carries engine descriptor fields, config, corpus stamp (use `corpus_stamp` from `tts_bench.corpus`) and the command; US3 completes it (FR-007)
- [ ] T011 [US1] Implement the `run` subcommand in `src/tts_bench/metrics/__main__.py` for steady-state runs: `run ENGINE [--voice NAME] [--voices-dir cloned_voices] [--subset main|cloning] [--repetitions 5] [--limit N] [--out results/perf]`; import `tts_bench.adapters`, build the adapter with `get_adapter`, `load()` (engine not installed or weights missing: print the adapter's hint and exit 2, write no file), resolve the voice through `LocalVoiceLibrary.resolve` BEFORE timing, except that `--voice` may be omitted for `fake`; print the written path and a short summary; exit 0 even when some sentences failed (see contracts/metrics-cli.md)
- [ ] T012 [P] [US1] Write `docs/metrics.md` with the metric definition table from `contracts/results-file.md` (start instant, end instant, unit for load time, generation time, TTFA, RTF, chunk latency, throughput, first-request time), the clock used, and how to read "not available"; link it from `README.md` (Constitution Principle VIII)

**Checkpoint**: `python -m tts_bench.metrics run fake --limit 5 --repetitions 2` writes a results file with correct figures

---

## Phase 4: User Story 2 - Separate cold, warm, and load time (Priority: P1)

**Goal**: cold and warm runs are distinct, load time and first-request time are reported apart from steady-state figures, and warm-up is excluded.

**Independent Test**: fake engine with `load_delay_s=0.3`; the cold file shows `load_time_ms` about 300 and a `first_request` block outside the steady-state statistics; the warm file contains no warm-up measurements.

- [ ] T013 [P] [US2] Tests in `tests/metrics/test_cold_warm.py`: cold mode reports `load_time_ms` within 5% of the fake `load_delay_s`, exactly one measurement with `phase = first_request` (the first corpus sentence, repetition 1) that is absent from `summary.ttfa_ms.n` / `summary.rtf.n`, and a first-request penalty (its `generation_ms` minus the steady p50); warm mode runs `--warmup` requests that are not stored as measurements and not counted in `n_total`; load time is also reported in warm mode; a failed `load()` writes no file (FR-004, FR-005)
- [ ] T014 [US2] Implement `run_benchmark(adapter, corpus, voice, *, mode, repetitions=5, warmup=3, ...)` in `src/tts_bench/metrics/runner.py`: time `adapter.load()` (just before the call to its return) as `load_time_ms`; cold: the first corpus sentence of repetition 1 is measured with `phase = first_request`, the rest of repetition 1 and all later repetitions are `steady`; warm: run `warmup` requests over the first corpus sentences and discard them, then every repetition is `steady`; failures in warm-up are logged to the summary as `warmup.failed` and do not stop the run; always call `adapter.close()` in a `finally` (FR-004, FR-005)
- [ ] T015 [US2] Extend `summarize` in `src/tts_bench/metrics/stats.py` with `load_time_ms`, `first_request` (`{sentence_id, generation_ms, ttfa_ms, rtf, penalty_ms}`, cold only) and `warmup` (`{requests, discarded: true}`, warm only); `penalty_ms` is first-request `generation_ms` minus the steady `generation_ms` p50
- [ ] T016 [US2] Add `--mode {cold,warm}` (required) and `--warmup N` (default 3, warm only) to the `run` subcommand in `src/tts_bench/metrics/__main__.py`, switch it to `run_benchmark`, store `mode`, `repetitions` and `warmup` in `config`, and name the results file `<engine>-<mode>-<timestamp>.json`; the quickstart commands in `quickstart.md` already pass `--mode`

**Checkpoint**: cold and warm results files differ as specified for the fake engine

---

## Phase 5: User Story 3 - Record resource use and environment (Priority: P2)

**Goal**: every results file carries peak RAM, CPU use, VRAM (or "not available"), the full environment record, and `compare` refuses to mix hardware.

**Independent Test** (after US2, because the wiring in T022 uses `run_benchmark`; the tests T017–T019 and modules T020–T021 can be developed earlier): a results file contains peak RAM with its method and unit, CPU percent, and every environment key; `compare` on two files with different hardware keys exits 3 unless `--allow-mixed-hardware` is given.

- [ ] T017 [P] [US3] Tests in `tests/metrics/test_resources_environment.py`: RAM peak is a positive MiB number with a non-empty `ram_method` stating the unit conversion; `cpu_percent_of_one_core` and `logical_cores` are present; VRAM is `"not available"` with `vram_note` when no GPU tool exists (monkeypatch the lookup); background-load warning is true when a stubbed `os.getloadavg` exceeds the threshold and false below it; thread settings include the `OMP_NUM_THREADS`, `MKL_NUM_THREADS` and `VECLIB_MAXIMUM_THREADS` values (or null) (FR-006, FR-014)
- [ ] T018 [P] [US3] Tests in `tests/metrics/test_results_file.py`: every key of the `environment` block in `contracts/results-file.md` is present after a fake-engine run, with `null` plus a reason instead of omission for unknown values; the command string starts with `python -m tts_bench.metrics` and equals the arguments passed, with absolute paths relative to the repository root or `<abs-path>`; no hostname, user name or home directory path appears anywhere in the file (run the CLI with an absolute `--out` under `tmp_path` to prove paths are redacted); `read_results` round-trips `write_results` and rejects an unknown `schema_version` (FR-007, SC-003)
- [ ] T019 [P] [US3] Tests in `tests/metrics/test_compare.py` with hand-built results files: identical hardware keys merge into a Markdown table; a difference in CPU model, logical cores, RAM GiB, GPU model, or OS name / major version is refused with exit 3 naming the field, and `--allow-mixed-hardware` lifts only that refusal; differences in library versions or thread settings do not block but are listed; corpus version/hash, subset, `limit` or locality mismatches are refused even with the override; cold and warm results appear in separate tables (FR-009, SC-005)
- [ ] T020 [P] [US3] Implement `src/tts_bench/metrics/resources.py`: `peak_ram_mib()` from `resource.getrusage(RUSAGE_SELF).ru_maxrss` normalized to MiB (bytes on darwin, KiB on linux) returning the value and the method string; `CpuTimer` using `time.process_time` over the measured phase against wall time; `peak_vram_mib()` via `nvidia-smi --query-gpu=memory.used` or `torch.cuda.max_memory_allocated` only if `torch` is already in `sys.modules`, otherwise `"not available"` with a reason (on unified-memory machines the note says memory is counted under RAM); `background_load(threshold)` using `os.getloadavg()[0] / os.cpu_count()` with a documented lag note. No sampling thread (research R4, R5)
- [ ] T021 [P] [US3] Implement `src/tts_bench/metrics/environment.py`: `collect_environment(adapter, voice, corpus, config, argv)` returning the Environment Record from data-model.md (CPU model via `sysctl -n machdep.cpu.brand_string` or `/proc/cpuinfo`; physical and logical cores; RAM GiB via `sysctl hw.memsize` or `os.sysconf`; GPU model when detectable; OS name and release; Python version; library versions via `importlib.metadata` for numpy, tts_bench, torch if installed, and the engine package; git commit via `git rev-parse HEAD` or null; the command string built from `argv` as `python -m tts_bench.metrics <args>` with absolute paths made relative to the repository root or replaced by `<abs-path>`; voice name, kind and checksum (null when none); descriptor fields; `locality` default `local`; no hostname, no user name) and `hardware_key(env)` built from CPU model, logical cores, RAM GiB rounded, GPU model, OS name and major version (FR-007, research R7)
- [ ] T022 [US3] Wire resources and environment into `run_benchmark` and `write_results`: read RAM peak after load and after the measured phase, CPU percent over the measured phase only, VRAM, background load before and after (store `background_load.warning`), and the full environment record with `hardware_key`; remove the partial environment block from T010
- [ ] T023 [US3] Implement `src/tts_bench/metrics/compare.py`: `compare_results(paths, allow_mixed_hardware=False)` groups by mode, checks hardware key, corpus version/hash, subset, `limit` and locality per the rules in research R8 (hardware override lifts only the hardware check), lists non-blocking environment differences, and renders one Markdown table per mode with columns engine, voice, granularity, load time, TTFA p50/p95, RTF p50/p95, throughput, peak RAM, CPU, VRAM, reliable, n; refusals raise `CompareRefusedError` (new, in `compare.py`) naming the differing fields (FR-009)
- [ ] T024 [US3] Add the `compare FILE... [--allow-mixed-hardware] [--out FILE.md]` subcommand to `src/tts_bench/metrics/__main__.py`; exit 3 on `CompareRefusedError` and write nothing; export `run_benchmark`, `summarize` and `compare_results` from `src/tts_bench/metrics/__init__.py`

**Checkpoint**: all three stories work end to end with the fake engine

---

## Phase 6: Polish and cross-cutting

- [ ] T025 [P] Add `tests/metrics/test_offline.py`: replace `socket.socket` with a function that raises, then run the `run` CLI main for the fake engine end to end and assert it succeeds (SC-004)
- [ ] T026 [P] Add a reproducibility test to `tests/metrics/test_cold_warm.py`: two warm runs of the same fake engine on the same machine give median RTF within 10% of each other (SC-002)
- [ ] T027 [P] Add `tests/integration/test_metrics_real_engines.py` marked `@pytest.mark.engine`: runs a short warm benchmark (`--limit 5 --repetitions 2`) for the engine installed in the current venv and checks the results file validates; skipped when no engine is installed
- [ ] T028 [P] Document in `docs/metrics.md` and `README.md` how to run per-engine in separate venvs, why results from different hardware or corpus versions are refused, and how to read `reliable: false` and `"not available"`
- [ ] T029 Run the six quickstart scenarios in `quickstart.md` and the full `pytest` suite; fix any failure; confirm no file under `results/perf/` from test runs is left behind (tests write to `tmp_path`)

---

## Dependencies and execution order

- Phase 1 → Phase 2 → US1 → US2 → US3 → Polish. US2 builds on `runner.py`, `stats.py` and the CLI from US1. US3 can start its tests (T017–T019) and the independent modules (T020, T021) once Phase 2 is done, but wiring (T022) needs US2.
- Within a phase, tasks marked [P] touch different files and can run together.
- T009 → T010 → T011; T014 → T015 → T016; T020 + T021 → T022 → T023 → T024.

### Parallel examples

- Phase 2: T002, T003, T004, T005 together.
- US1 tests: T006 and T007 together, then T008; T012 any time after T011.
- US3: T017, T018, T019, T020, T021 together.

## Implementation strategy

- **MVP**: Phases 1–3 (US1). It already answers the central question (TTFA, RTF, throughput per engine) with the fake engine and for any installed real engine.
- Then US2 (cold/warm/load), which the constitution requires for any published comparison, and US3 (resources, environment, hardware guard) before any cross-engine report is published.
- Each phase ends at a checkpoint that can be demonstrated on its own.

## Requirement coverage

| Requirement | Tasks |
|-------------|-------|
| FR-001 one engine per process | existing adapter guard; T009 and T011 never load a second engine (covered by `tests/unit/test_one_engine_per_process.py`) |
| FR-002 | T006, T007, T008, T009 |
| FR-003 | T006, T008 |
| FR-004 | T013, T014, T015 |
| FR-005 | T013, T014, T016 |
| FR-006 | T017, T020, T022 |
| FR-007 | T010, T018, T021 |
| FR-008 | T007, T021 |
| FR-009 | T019, T023, T024 |
| FR-010 | T005, T006, T007 (fake engine and plain lists) |
| FR-011 | T006, T007, T008 |
| FR-012 | T007, T009 |
| FR-013 | T002, T003, T006, T007, T008, T009 |
| FR-014 | T017, T020 |
| FR-015 | T007, T009 |
| SC-001 | T007 |
| SC-002 | T026 |
| SC-003 | T018 |
| SC-004 | T025 |
| SC-005 | T019 |

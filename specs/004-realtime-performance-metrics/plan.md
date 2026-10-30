# Implementation Plan: Real-Time Performance Metrics

**Branch**: `004-realtime-performance-metrics` | **Date**: 2026-10-30 | **Spec**: [spec.md](spec.md)

**Input**: Feature specification from `/specs/004-realtime-performance-metrics/spec.md`

## Summary

Add a metrics package (`tts_bench.metrics`) with a CLI that runs one engine adapter over the Spanish corpus in one mode (cold or warm), records raw per-sentence measurements (TTFA, generation time, RTF, chunk latencies, status), derives summaries (p50, p95, mean, throughput), captures resource use and an environment record, and writes one JSON results file. A second command, `compare`, merges results files into Markdown tables and refuses to mix hardware (or corpus, mode, locality) without an explicit override. All computation is separated from engine I/O so it is tested with the fake engine and synthetic measurements, with no weights and no network. See [research.md](research.md) for decisions, [data-model.md](data-model.md) for entities, and [contracts/](contracts/) for the CLI and results file.

## Technical Context

**Language/Version**: Python 3.11 (repo requires >=3.11)

**Primary Dependencies**: standard library only (`time`, `resource`, `os`, `platform`, `subprocess` for `sysctl`/`nvidia-smi`, `importlib.metadata`, `json`, `statistics`/`numpy` percentiles) plus `numpy`, already a core dependency. No new dependency (no `psutil`).

**Storage**: JSON results files under `results/perf/` (tracked; contain no voice material, hostnames, or user names). Markdown summaries written by `compare`.

**Testing**: pytest in `tests/metrics/` with the fake engine (known delays and audio length) and synthetic measurement lists. A `@pytest.mark.engine` integration test runs a real engine in its own venv.

**Target Platform**: macOS (Apple Silicon) and Linux; CPU, plus NVIDIA GPU VRAM when present

**Project Type**: library plus CLI (`python -m tts_bench.metrics`)

**Performance Goals**: harness overhead inside the timed region is limited to reading monotonic clocks, so the fake-engine figures match known values within 5% (SC-001) and warm median RTF repeats within 10% (SC-002).

**Constraints**: local-first (no network use at all); one engine per process (already enforced by the adapter guard); no sampling thread during timed regions; voices resolved before timing; no engine-specific logic.

**Scale/Scope**: corpus of 123 main sentences, default 5 repetitions and 3 warm-up requests; about 8 small modules

## Constitution Check

*GATE: Must pass before Phase 0 research. Re-check after Phase 1 design.*

| Principle | Status | Note |
|-----------|--------|------|
| I Real-time relevance | Pass | TTFA, RTF, throughput, load, cold/warm and resources are the whole feature; fast-in-aggregate but slow-to-first-audio is visible because both are reported side by side |
| II Spanish by default | Pass | uses only the Spanish corpus; voice variant comes from the descriptor and is stored |
| III Apples-to-apples | Pass | same corpus and order, one engine per process, cold/warm separate, load separate, p50/p95, hardware/corpus/mode/locality mixing refused, "not available" never estimated |
| IV Deterministic vs human | Pass | deterministic metrics only; no quality or MOS here |
| V Honest reporting | Pass | environment record, exact command, raw per-sentence data kept; vendor figures not involved |
| VI Licensing/consent | Pass | voices only through `LocalVoiceLibrary.resolve` (consent checked); results store voice name and checksum, never audio; no WAV written to `results/` |
| VII Modular | Pass | package imports only `core`, `corpus`, `voices`; no backend or frontend; adding an engine needs no change here |
| VIII Verifiable | Pass | each FR maps to a fake-engine or synthetic-data test; every metric has documented start and end instants (contracts/results-file.md) |

Post-design re-check: no violations; Complexity Tracking not needed. One small change to feature 001 code is required (`EmptyAudioError`, see research R6) and is backward compatible.

## Decisions Confirmed Before Task Generation

Confirmed by the maintainer on 2026-10-30:

1. Defaults stay as planned: 5 repetitions, 3 warm-up requests, load threshold 0.25 per core, `p95_low_sample` flag below 20 values.
2. Only the `main` subset is measured by default; `--subset cloning` remains available.
3. The backward-compatible `EmptyAudioError` change to feature 001 code is accepted, as its own task with its own test.
4. Background load uses `os.getloadavg` and is documented as indicative.
5. Remote engines are deferred to a future feature; only the `locality` field is reserved.
6. VRAM on unified-memory machines is reported as "not available" with a note (memory counted under RAM).

## Project Structure

### Documentation (this feature)

```text
specs/004-realtime-performance-metrics/
├── plan.md
├── research.md
├── data-model.md
├── quickstart.md
├── contracts/
│   ├── metrics-cli.md
│   └── results-file.md
├── checklists/requirements.md
└── tasks.md              # created by /speckit-tasks
```

### Source Code (repository root)

```text
src/tts_bench/
├── core/
│   └── errors.py          # + EmptyAudioError(SynthesisError); adapter raises it when no audio is produced
├── metrics/
│   ├── __init__.py        # exports run_benchmark, summarize, compare_results
│   ├── __main__.py        # CLI: run, compare
│   ├── model.py           # Measurement, ChunkTiming, RunSummary, ResultsFile dataclasses (+ to/from dict)
│   ├── stats.py           # percentile, summarize (pure functions, no I/O)
│   ├── runner.py          # cold/warm protocol around an EngineAdapter
│   ├── resources.py       # peak RAM, CPU time, VRAM, background load
│   ├── environment.py     # Environment Record and hardware key
│   ├── results.py         # write/read results files, schema check
│   └── compare.py         # merge rules and Markdown tables
docs/
└── metrics.md             # metric definitions and how to read results (instants, units)
results/
└── perf/                  # JSON results files
tests/metrics/
├── conftest.py
├── test_stats.py
├── test_runner_fake.py
├── test_cold_warm.py
├── test_resources_environment.py
├── test_results_file.py
├── test_compare.py
└── test_offline.py
```

**Structure Decision**: single project, one new subpackage beside `corpus` and `voices`. Pure statistics (`stats.py`) are separate from the runner so metric computation is testable without any engine (FR-010).

## Complexity Tracking

No violations to justify.

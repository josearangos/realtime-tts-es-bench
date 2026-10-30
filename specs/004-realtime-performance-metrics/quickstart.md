# Quickstart: Real-Time Performance Metrics

Prerequisites: `pip install -e ".[dev]"` in the core venv. Fake-engine steps need no weights and no network.

## 1. Metrics from known values (US1, SC-001)

```
pytest tests/metrics/test_stats.py tests/metrics/test_runner_fake.py
```

Expected: fake engine with first-chunk delay 0.2 s and 1.0 s of audio gives TTFA, RTF and throughput within 5% of the known values; p50 and p95 match hand-computed values.

## 2. Cold, warm and load time (US2)

```
python -m tts_bench.metrics run fake --mode cold --limit 10 --repetitions 2
python -m tts_bench.metrics run fake --mode warm --limit 10 --repetitions 2 --warmup 2
```

Expected: the cold file has `load_time_ms` and a `first_request` block separate from steady-state figures; the warm file has no warm-up measurements.

## 3. Resources and environment (US3, SC-003)

```
pytest tests/metrics/test_resources_environment.py tests/metrics/test_results_file.py
```

Expected: peak RAM with its method and unit, CPU percent, VRAM or "not available", and every environment key present.

## 4. Refusing mixed hardware (SC-005)

```
pytest tests/metrics/test_compare.py
```

Expected: results with different hardware keys are refused (exit 3) unless `--allow-mixed-hardware`; corpus, mode and locality mismatches are handled as in [contracts/metrics-cli.md](contracts/metrics-cli.md).

## 5. Offline (SC-004)

```
pytest tests/metrics/test_offline.py
```

## 6. Real engine (manual, per engine venv)

```
python -m tts_bench.metrics run piper --mode warm --voice <name>
python -m tts_bench.metrics compare results/perf/piper-warm-*.json
```

Repeat the warm run on the same machine; the median RTF should agree within 10% (SC-002).

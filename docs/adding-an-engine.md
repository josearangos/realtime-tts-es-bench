# Adding an engine

1. Copy `src/tts_bench/adapters/fake.py` to `src/tts_bench/adapters/<engine>.py`.
2. Subclass `BaseAdapter`: set `self.descriptor` (declare streaming granularity; never infer it),
   implement `_load()` (import the engine library *inside* it and raise
   `EngineNotInstalledError` / `WeightsMissingError` with a hint) and
   `_iter_engine(text, voice)` yielding `(samples, sample_rate, channels)` at the engine's native rate.
3. Add one line to `src/tts_bench/adapters/__init__.py`:
   `register("<engine>", "tts_bench.adapters.<engine>:<Class>")`.
4. Add the engine to the contract parametrization in `tests/contract/test_adapter_contract.py`
   and run `pytest tests/contract tests/unit`. Add an optional extra in `pyproject.toml`.

Run each engine in its own virtual environment (one engine per process).

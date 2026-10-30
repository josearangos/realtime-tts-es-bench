# Contract: Engine Adapter Interface (Python)

Consumers (metrics, backend, frontend) depend only on this contract.

```python
class EngineAdapter(Protocol):
    descriptor: EngineDescriptor            # available before load(); engine_version is filled at load(),
                                            # and Piper's voice-dependent fields after the first synthesis.
                                            # Streaming granularity is always a fixed declaration.

    def load(self) -> float: ...
        # Loads weights. Returns load seconds (kept apart from synthesis time).
        # Raises EngineNotInstalledError / WeightsMissingError (with install hint),
        # EngineAlreadyLoadedError if another engine is loaded in this process.

    def synthesize(self, text: str, voice: VoiceReference) -> SynthesisResult: ...
        # Complete audio at native sample rate. For streaming engines the result also
        # carries per-chunk timing. For granularity "none", first_audio_ns is None.

    def stream(self, text: str, voice: VoiceReference) -> Iterator[AudioChunk]: ...
        # Only valid when descriptor.streaming.granularity != "none"; otherwise raises
        # StreamingNotSupportedError. Each chunk has produced_at_ns stamped on receipt.

    def close(self) -> None: ...
        # Releases the one-engine-per-process guard so another engine can load afterwards.
```

## Guarantees
- `SynthesisResult.descriptor` reflects the engine and voice actually used; consumers must record that one.
- Text is passed unchanged; length over `descriptor.input_limits` raises `InputLimitError` before the engine is called.
- Audio is never resampled; `sample_rate` is the engine's own.
- Any engine failure raises `SynthesisError`; no partial result is returned as success.

## Registry
```python
register("phonon", "tts_bench.adapters.phonon:PhononAdapter")
get_adapter("phonon") -> EngineAdapter   # imports lazily; unknown name lists registered names
```

## Voice resolution (feature 003 boundary)
```python
class VoiceLibrary(Protocol):
    def resolve(self, name: str, kind: VoiceKind) -> VoiceReference: ...  # raises VoiceNotFoundError
```
A test-only in-memory library and a temporary directory-based library over `cloned_voices/` (mapping names to files via a git-ignored `voices.toml`) are provided until 003 exists; 003's library replaces them without changing adapters.

## Fake engine (FR-010)
`FakeAdapter(granularity, first_chunk_delay_s, chunk_interval_s, audio_seconds, sample_rate)` produces deterministic silence/tone with exactly the configured timings, so metric code can assert exact expected values.

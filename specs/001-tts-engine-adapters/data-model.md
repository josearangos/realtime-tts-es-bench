# Data Model: TTS Engine Adapters

## EngineDescriptor (frozen, per adapter) - FR-007, FR-003, FR-015
| Field | Type | Notes |
|-------|------|-------|
| name | str | registry key, e.g. `phonon` |
| engine_version | str | installed package version, read at load time |
| model_id | str | e.g. `hf://gradium/phonon-40m-es` |
| license_code / license_model | str | flagged if non-commercial or copyleft |
| license_flags | list[str] | e.g. `non-commercial`, `copyleft` |
| language | str | `es` |
| spanish_variant | str | accent actually produced, e.g. `es-ES (closest to CO)` |
| voice_kind | enum | `catalog_name`, `reference_audio`, `stored_voice_file`, `fixed_voice` |
| supports_cloning | bool | |
| streaming | StreamingInfo | declared, never inferred (SC-003) |
| input_limits | InputLimits | `max_chars: int or None` |
| install_hint / weights_hint | str | actionable text (FR-008) |

**Descriptor lifecycle (as built)**: `streaming` and `voice_kind` are fixed constants. `engine_version` is filled in at `load()` (before that it reads `unknown (read at load)`). For Piper, `model_id`, `license_model` and `spanish_variant` follow the selected voice and are updated when the voice is first used, so read the descriptor from `SynthesisResult.descriptor` (taken after synthesis), not only before. A descriptor object is never mutated: the adapter replaces it.

## StreamingInfo
`granularity`: `chunk` | `sentence` | `none`. `none` means time to first audio is "not available".

## VoiceReference (FR-011)
`name` (library name, e.g. `valentina`), `kind` (matches descriptor voice_kind), `path_or_id` (e.g. a `.safetensors` file, a reference `.wav`, or a Piper voice name) (resolved by the voice library from feature 003; adapters never hardcode paths).

## AudioChunk
`samples` (float32 or int16 array as produced), `sample_rate`, `channels`, `produced_at_ns` (perf_counter_ns), `index`.

## SynthesisResult
`audio` (concatenated native-format samples), `sample_rate`, `request_started_ns`, `first_audio_ns` (None if granularity is `none`), `finished_ns`, `chunks` (list of AudioChunk timing records, empty for `none`), `descriptor`.

## Errors (FR-008, FR-012, FR-013, FR-015)
`EngineNotInstalledError`, `WeightsMissingError`, `EngineAlreadyLoadedError`, `InputLimitError`, `SynthesisError` (carries optional partial chunks for diagnosis only, never counted in latency stats), `VoiceNotFoundError`.

## State
`created -> loaded -> (synthesizing <-> loaded) -> closed`. A second engine `load()` in the same process is refused. Failed synthesis returns the engine to `loaded` but the run is a failure.

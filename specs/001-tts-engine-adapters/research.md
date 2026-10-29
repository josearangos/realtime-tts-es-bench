# Research: TTS Engine Adapters

All facts below come from the engines' public pages read on 2026-10-29 and are **vendor-published, not measured by this project**. Items marked *unverified* must be confirmed during implementation.

## Phonon (baseline)

- **Decision**: Use the `ptts` package with the local model directory `./phonon-40m-es` (downloaded from `hf://gradium/phonon-40m-es`), `lang="es"`, no `quant` argument (as in the owner's script).
- **Facts**: install `pip install ptts`; `ptts.TTS(...)`; `tts.save(path, text, voice=...)` for complete audio; `with tts.stream(text, voice=...) as audio:` yields float32 chunks at `audio.sample_rate`; mono 24 kHz; ~100 catalog voices (example `Iker`).
- **Streaming**: chunk-level (declared from the model card example).
- **License**: weights, tokenizer, and voices CC BY-NC 4.0 (non-commercial); runtime MIT OR Apache-2.0. Flag prominently (Principle VI).
- **Cloning (project owner's working script, not yet re-run by this project)**: the model card says cloning is a hosted-studio feature, but the owner generates cloned audio locally with `tts = ptts.TTS("./phonon-40m-es", lang="es")`, `tts.add_voice("valentina", "valentina.safetensors")`, `tts.save("valentina.wav", text, voice="valentina")`. The stored voice file is `cloned_voices/valentina.safetensors`. The adapter loads the model from the local directory `./phonon-40m-es` and registers the stored voice by name. `quant` is left at its default, exactly as in the owner's script (`q8` stays commented out). The model is downloaded from Hugging Face into `./phonon-40m-es` so it runs offline (Local-first).
- **Accent**: Colombian, through the stored cloned voice `valentina`. The catalog voices are not used.
- **Alternatives**: Transformers path (`model.generate`) rejected: no documented streaming.

## Pocket TTS

- **Decision**: Use the `pocket-tts` package, `TTSModel.load_model()`, `get_state_for_audio_prompt(voice)`, `generate_audio(state, text)`.
- **Facts**: install `pip install pocket-tts`; Python 3.10-3.14; PyTorch 2.5+ (CPU build is enough); voice can be a pre-made name (e.g. `alba`), a local wav, or an `hf://` path; `tts_model.sample_rate` gives the rate; README lists Spanish among seven languages with a Spanish voice `lola`; first chunk ~200 ms claimed.
- **Cloning**: yes, from a local wav reference (consent rule applies, Principle VI). Reference audio chosen by the owner, both Colombian Spanish, in `cloned_voices/`: `es-CO_B2_-_Valentina_-_Gentle_Service_v1_sample.wav` and `es-co-b2-04-emiliano_sample.wav`. Their source and licence must be recorded before any results are published.
- **Streaming**: README lists audio streaming, but the Python streaming method is not documented in the page read. *Unverified*: community docs mention `generate_audio_stream`. Resolve by inspecting the installed package before coding; granularity is declared chunk-level only if confirmed, otherwise "none".
- **Language selection in Python**: *unverified* (CLI `--language`; Python parameter not shown).
- **License**: software license not stated on the page read; voice licenses are on a linked Hugging Face page. *Unverified*, record per checkpoint.

## Piper

- **Decision**: Use `piper-tts` (OHF-Voice/piper1-gpl), `PiperVoice.load(<.onnx>)`, `voice.synthesize(text)` yielding `AudioChunk` (`sample_rate`, `sample_width`, `sample_channels`, `audio_int16_bytes`).
- **Voices**: the owner chose any Latin American Spanish voice (owner chose es_MX; exact voice picked in T018); none is Colombian, so results are labeled with the closest accent. Downloaded with `python3 -m piper.download_voices <name>`; Spanish voices exist as es_ES, es_MX (and others, *unverified*). No Colombian voice known.
- **Cloning**: none (fixed voice).
- **Streaming**: the chunk iterator exists but the page does not say whether chunks are per sentence. Declared **sentence-level** (Piper synthesizes sentence by sentence) - *unverified*, confirm by inspecting chunk boundaries with the fake-free smoke test.
- **License**: engine GPL-3.0 (copyleft, flag); each voice has its own model card license, verify per voice.
- **Note**: older `rhasspy/piper` is a different, earlier package; do not mix.

## Cross-cutting decisions

- **Language/runtime**: Python 3.11 (inside the supported range of all three).
- **Isolation (FR-009, Principle VII)**: core package has zero engine dependencies; each engine is an optional extra and is expected to live in its own virtual environment because PyTorch (Pocket TTS) and ONNX (Piper) stacks may conflict.
- **Registration (SC-002)**: a registry maps engine name -> `module:Class` string; adapters import engine libraries lazily inside `load()`, so a missing engine never breaks the others.
- **One engine per process (FR-013)**: a process-level guard in `load()` raises on a second engine.
- **Timing (FR-004/FR-014)**: the adapter stamps `time.perf_counter_ns()` at the moment each chunk is received from the engine; the request start stamp is taken immediately before calling the engine.
- **No resampling (FR-006)**: audio is returned in the engine's native rate and dtype conversions are limited to lossless wrapping into float32 or int16 as the engine produces it; the native format is recorded.
- **Text (FR-015)**: passed through unchanged; per-engine limits live in the descriptor.
- **Accent coverage (updated from owner input)**: Phonon (cloned `valentina`) and Pocket TTS (two Colombian references) target Colombian Spanish; Piper uses a Latin American voice and is labeled with its closest accent, never presented as Colombian.

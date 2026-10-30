# Voice preparation per engine

How each engine's voice is created (FR-004). This file describes steps only; it contains no voice material. Voice files, recordings and consent records live in the git-ignored `cloned_voices/` (Constitution Principle VI). Commands: `python -m tts_bench.voices --help`.

Prerequisite for every cloned voice: a consent record for the speaker (`consent add`) and a registered recording (`add-recording`).

## Pocket TTS (cloning, automated)

1. `prepare <recording_id> --engine pocket_tts --name <voice>` trims the reference segment (default: first 20 s; override with `--start` / `--length`) and registers it as a `reference_audio` voice.
2. Cloning needs the gated model terms accepted at huggingface.co/kyutai/pocket-tts and `hf auth login` (see feature 001).

Voices: `valentina`, `emiliano`.

## Phonon (cloning, external step)

The `.safetensors` voice file is created in the hosted studio, outside this repository:

1. `prepare <recording_id> --engine phonon --name <voice>` writes the trimmed segment (default: first 20 s) and prints the path.
2. Open https://studio.gradium.ai/, clone the voice from that segment, and download the resulting `.safetensors` file. The reference audio is uploaded to that third-party service; the speaker's consent must cover it. Studio input limits are not verified here.
3. `register <voice> --engine phonon --kind stored_voice_file --file <downloaded.safetensors> --recording <recording_id> --start <s> --length <s> --creation "external: studio.gradium.ai" --accent es-CO`.

The same `recording_id` as Pocket TTS's `valentina` voice must be used so cross-engine comparisons share one source (SC-002). Voice: `valentina` only.

## Piper (no cloning, fixed voices)

Piper does not clone and is not penalized for it (FR-010). Two fixed voices are assigned and need no consent or recording:

- `es_MX-claude-high` (es-MX)
- `es_AR-daniela-high` (es-AR)

Download: `python3 -m piper.download_voices --download-dir cloned_voices <voice>`, then `assign-fixed <voice> --engine piper --voice <voice> --accent <accent>` (the library name must equal the voice id: the Piper adapter reads accent and licence from it). Neither is Colombian; reports label them with their actual accent. Check each voice's model-card licence (done by the owner for both, 2026-10-29).

## Removing a voice

`remove <name>` removes one voice and its generated audio. `withdraw <alias>` removes every voice of a speaker, the recording and the consent record, and marks existing results `voice_withdrawn` (SC-004).

`withdraw` only deletes files the library owns. It does not delete the originals you provided (the source `.wav` recordings and the downloaded `.safetensors` in `cloned_voices/`), nor anything uploaded to a third-party service such as studio.gradium.ai. Delete those yourself when consent is withdrawn.

## Keeping voice material out of git

`python -m tts_bench.voices check-repo` exits 1 and lists any `cloned_voices/` path or `.wav`, `.safetensors`, `.onnx`, `.pt`, `.ckpt` file that is tracked or was ever added to history. To use it as a pre-commit check, call it from your own `.git/hooks/pre-commit`; no tool here modifies git config.

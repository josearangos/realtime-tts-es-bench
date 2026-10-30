# Quickstart: validating Voice Preparation and Consent

Runs in the core venv (`.venv-core`, see feature 001's quickstart). Interface details: [contracts/voice-library.md](contracts/voice-library.md). Entities: [data-model.md](data-model.md). Never commit anything under `cloned_voices/`.

## 1. Automated checks (no weights, no real voices)
```sh
.venv-core/bin/pytest tests/voices
```
Expected: tests pass using synthetic WAVs and the fake engine, covering consent, registration, name resolution, engine mismatch, modified/missing files, short/noisy warnings, removal, withdrawal and the repository check.

## 2. Block cloning without consent (User Story 3)
```sh
.venv-core/bin/python -m tts_bench.voices add-recording my.wav --consent nobody --accent es-CO
```
Expected: exit 1, message "consent required", nothing written.

## 3. One recording for both cloning engines (User Story 1)
```sh
R=.venv-core/bin/python
$R -m tts_bench.voices consent add --alias valentina --date 2025 \
   --uses internal_benchmarking,published_results,published_demo_audio,human_evaluation \
   --content outbound_sales,collections,inbound,cloning_prompts
# repeat for the second speaker: --alias emiliano --date 2025 (same uses and content)
$R -m tts_bench.voices add-recording cloned_voices/es-CO_B2_-_Valentina_-_Gentle_Service_v1_sample.wav \
   --consent valentina --accent es-CO --no-music-confirmed        # prints rec-XXXXXXXXXXXX and any warnings
$R -m tts_bench.voices prepare rec-XXXXXXXXXXXX --engine pocket_tts --name valentina-pocket
$R -m tts_bench.voices prepare rec-XXXXXXXXXXXX --engine phonon --name valentina-phonon   # writes the segment to upload to studio.gradium.ai, prints the steps
# second speaker, Pocket TTS only: add-recording for emiliano, then prepare ... --engine pocket_tts --name emiliano-pocket
# after cloning the voice at studio.gradium.ai and downloading the .safetensors (docs/voice-preparation.md):
$R -m tts_bench.voices register valentina-phonon --engine phonon --kind stored_voice_file \
   --file cloned_voices/valentina.safetensors --recording rec-XXXXXXXXXXXX --start 0 --length 20 \
   --creation "external: studio.gradium.ai" --accent es-CO
$R -m tts_bench.voices assign-fixed es_MX-claude-high --engine piper --voice es_MX-claude-high --accent es-MX
$R -m tts_bench.voices assign-fixed es_AR-daniela-high --engine piper --voice es_AR-daniela-high --accent es-AR
$R -m tts_bench.voices list
```
Expected: `list` shows the Phonon, both Pocket and both Piper voices; `show valentina-pocket` and `show valentina-phonon` have the same `recording_id`, each with its own segment.

## 4. Use by name, with refusals (User Story 2, FR-013, FR-014, FR-016)
```sh
.venv-pocket/bin/python -m tts_bench.smoke pocket_tts --voice valentina-pocket --out /tmp/p.wav   # works
.venv-pocket/bin/python -m tts_bench.smoke pocket_tts --voice valentina-phonon --out /tmp/x.wav   # refused: voice belongs to phonon
echo x >> cloned_voices/voices/valentina-pocket/reference.wav
.venv-core/bin/python -m tts_bench.voices verify                                                  # exit 1: valentina-pocket modified
```
Expected: the second command prints the engine mismatch explanation; `verify` reports the checksum mismatch. Restore the file by running `prepare` again after `remove`.

## 5. Repository stays clean (User Story 4, SC-003)
```sh
.venv-core/bin/python -m tts_bench.voices check-repo
git status --short            # no wav, safetensors, onnx or cloned_voices/ entries
```
Expected: `check-repo` exits 0. Optional pre-commit use: call the same command from your own `.git/hooks/pre-commit`.

## 6. Withdraw consent (edge case, SC-004)
```sh
.venv-core/bin/python -m tts_bench.voices withdraw valentina --results-dir results
```
Expected: the report lists voices removed, files deleted and result files marked; `list` no longer shows the voices; marked result files contain `"voice_withdrawn": true` with measurements unchanged. Do this on a copy of your data first.

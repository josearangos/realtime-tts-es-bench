# Engines

| Engine | Voice | Spanish accent | License flags | Weights |
|--------|-------|----------------|---------------|---------|
| `phonon` | stored cloned voice `valentina` (`cloned_voices/valentina.safetensors`) | es-CO | **non-commercial** (weights CC BY-NC 4.0; runtime MIT OR Apache-2.0) | `huggingface-cli download gradium/phonon-40m-es --local-dir ./phonon-40m-es` |
| `pocket_tts` | cloned from reference audio (`valentina`, `emiliano`) | es-CO | package MIT; model terms checked by the owner on the Hugging Face card (usable); weights are gated | downloaded on first load; voice cloning needs accepting the terms at huggingface.co/kyutai/pocket-tts and `hf auth login` |
| `piper` | fixed voice (`es_MX-claude-high` default, or `es_AR-daniela-high`) | es-MX (`claude`) or es-AR (`daniela`), the closest available. **Not Colombian**: label results with the accent of the voice used | **copyleft** (engine GPL-3.0); voice licence per its model card (es_MX-claude-high confirmed usable by the owner on its Hugging Face card; `es_AR-daniela-high` also confirmed usable by the owner) | `python3 -m piper.download_voices --download-dir cloned_voices es_MX-claude-high es_AR-daniela-high` |

## Voices and consent (Constitution Principle VI)

The project owner confirmed that the voices in `cloned_voices/` are authorized. The directory,
model weights and generated audio are git-ignored and never committed.
Reference files (rights purchased by the owner's company; keep the contracts outside the repo):

- `es-CO_B2_-_Valentina_-_Gentle_Service_v1_sample.wav`: voice of an employee of the owner's company; the company purchased the rights to this voice (owner statement, 2026-10-29)
- `es-co-b2-04-emiliano_sample.wav`: voice of an employee of the owner's company; the company purchased the rights to this voice (owner statement, 2026-10-29)
- `valentina.safetensors`: stored Phonon voice derived from the Valentina reference.

Voices are registered in the git-ignored `cloned_voices/` library and resolved by name (see `docs/voice-preparation.md`).

## Listening notes (owner, 2026-10-29)

- Phonon `valentina` and Pocket TTS `valentina`/`emiliano`: accent confirmed as Colombian.
- Piper `es_MX-claude-high`: accent is Mexican (as labeled) and the voice sounds robotic; report this when comparing naturalness. Voices kept after comparison: `es_MX-claude-high` and `es_AR-daniela-high`. Discarded by the owner: `es_MX-ald-medium`, `es_ES-davefx-medium`, `es_ES-sharvard-medium`. The adapter descriptor reports the accent of the selected voice.

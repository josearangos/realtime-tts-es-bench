# Brag Plan: Real-time TTS tester (realtime-tts-es-bench)

## What is this app?
A local web page that streams Spanish text-to-speech from several engines and shows live latency figures (time to first audio, real-time factor).

## The angle
The app narrates its own demo: the voice you hear is `valentina-phonon — es-CO`, one of the voices in the app. Real captures of the running frontend (http://127.0.0.1:5173/), no mock-ups.

## Hook (0–2s)
The real empty page ("Real-time TTS tester"), zooming into the Spanish text box while Valentina says "Escribe una frase en español y escúchala al instante."

## Key moments
- Typed sentence in the text box.
- Engines checked: phonon (valentina-phonon — es-CO) and piper.
- Play → comparison: "Starts speaking after 31.89 ms and generates 11.33× faster than real time." (real figures from the capture)
- Phonon result card: valentina-phonon · es-CO.

## Outro
"Real-time TTS tester" + "Pruébalo tú."

## User flow worth showing
Type text → pick engines → Play → read TTFA / real-time factor / total time.

## Tone
- Preset: app-store; Creative direction: calm product demo narrated by its own voice
## Format: landscape — 1920x1080 · Duration: 22s

## Visual identity (from frontend/styles.css)
- Background: paper ≈ #f6f1e9 · Text: ink ≈ #2b211b · Accent: signal ≈ #c8360a
- Fonts: system serif for display (New York/Georgia), mono for figures

## Voiceover script (Phonon, valentina-phonon — es-CO, generated via the local backend POST /v1/synthesize)
1. Escribe una frase en español y escúchala al instante.
2. Elige motores de voz, como Phonon, Piper y Pocket TTS.
3. La app mide la latencia en vivo: tiempo al primer audio y factor de tiempo real.
4. Esta voz es Valentina, en español colombiano.
5. Pruébalo tú.
(Deviation from the skill default: Kokoro is replaced by Phonon at the user's explicit request.)

## Audio direction
Music: Happy Beats vol-1 (120 BPM), ducked to ~0.12 under the voice. SFX: one click on Play (9.52s, on a beat), one soft hit on the end card (20.02s, strong cue). Audio-reactive: none (screen capture is the star).

## Storyboard
1. Hook — 0–4.4s — empty page → typed sentence (zoom on text box)
2. Engines — 4.4–9.5s — phonon + piper checked, zoom on engine list
3. Play + comparison — 9.5–15s — Play, then TTFA / RTF bars
4. Valentina card — 15–19.2s — phonon result card, es-CO
5. Outro — 19.2–22s — title + CTA

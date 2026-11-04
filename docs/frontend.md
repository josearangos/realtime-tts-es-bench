# Real-time testing frontend

A static, dependency-free web page (`frontend/`) for trying the real-time backend by ear and by number. The interface is in English; the synthesized text and the corpus are Spanish.

**It is a live-testing aid, not a benchmark.** Every panel is labelled `interactive`. Figures are measured on a single request with whatever else the machine is doing, so they are not comparable with benchmark results (Constitution III).

## Run

```bash
.venv-core/bin/python -m tts_bench.backend serve                          # backend on 127.0.0.1:8000
python -m http.server 5173 --bind 127.0.0.1 --directory frontend          # page on 127.0.0.1:5173
```

Open http://127.0.0.1:5173. The page makes no request outside the machine (no CDN, fonts or scripts). The backend must have a WebSocket library installed (`pip install -e ".[backend]"` includes `websockets`).

The backend URL is an editable field (kept in memory only). The page is served separately so the backend never serves static files; the backend therefore allows the page's origin through CORS (see below).

## What it does

- Lists every engine with availability (unavailable ones are disabled and show the reason and hint), a cloning badge, engine version, model id, license and each voice's name and accent label.
- Streams audio over `WS /v1/ws/synthesize` and starts playing at the first chunk. Each engine plays at its own sample rate.
- Compares engines **sequentially**: one text, one panel per engine, in order. The next engine starts only after the previous one finished and its audio has played, so engines never compete for CPU. A failed panel does not stop the rest. Stop cancels the running request and marks the rest "not run".
- Keeps each panel's audio in memory so Replay plays it without a new request. Results are lost on reload.
- Corpus picker: filter the `main` corpus subset by campaign or text; one click copies the sentence (its spoken form) into the input.

## Where each number comes from

| Shown | Source |
|-------|--------|
| Time to first audio | `summary.ttfa_ms`; `"not available"` is shown as such with the reason when the engine produces the whole audio at once |
| Granularity | `summary.granularity` (`chunk`, `sentence`, `none`), next to TTFA with its meaning |
| Total time | `summary.generation_ms` |
| Audio duration | `summary.audio_seconds` |
| Real-time factor | `summary.rtf` |
| Queue wait, model load | `summary.queue_wait_ms`, `summary.load_ms` (tagged "includes model load" on a cold first request) |
| Heard after | browser clock: request sent to first chunk handed to playback. Browser-side, never combined with TTFA |

Values are copied, never recomputed; the page keeps the digits the backend sent. Definitions live in [metrics.md](metrics.md).

## Limits and conditions

- The character counter uses the smallest `input_limit_chars` among the selected engines and names the engine that sets it; Play is disabled above it.
- The one-minute comparison target (SC-003) applies to engines that are already loaded and a sentence of 5 s of audio or less; a cold first request adds its model load time.
- Browsers need a click before sound: the audio context is created in the Play click. If it stays suspended an "Enable audio" button appears and plays the stored audio.
- Licenses flagged `non-commercial`, `copyleft` or any unknown flag show a prominent warning on the engine and on each panel.

## Backend additions (feature 008)

- `GET /v1/corpus`: read-only; `main` subset of `corpus/sentences.jsonl` as `{id, text, campaign, scenario, tags}`; never `cloning.jsonl`. A missing or malformed corpus returns 503 `corpus_unavailable` without a path.
- CORS: `cors_origins` (env `TTS_BACKEND_CORS_ORIGINS`, comma separated, or `backend.toml`). Default `http://127.0.0.1:5173` and `http://localhost:5173`; never `*`; empty disables browser access. The WebSocket also rejects a browser `Origin` that is not allowed; requests with no `Origin` (curl, tests) are unaffected.

## Privacy

The page renders only each voice's `name`, `kind`, `cloned` and `accent_label`. No voice path, hash, recording id or consent id is requested, rendered or accepted by the page or the new endpoint.

## Tests

```bash
node --test frontend/tests/
.venv-core/bin/python -m pytest tests/backend -q
node frontend/tests/e2e-fake-engine.mjs      # starts the gateway with the fake engine
```

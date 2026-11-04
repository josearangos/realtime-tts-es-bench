# realtime-tts-es-bench

Benchmark of real-time Spanish text-to-speech engines for call center use.

![TTS Wrapped: Piper vs Phonon vs Pocket TTS](docs/assets/tts-wrapped.gif)

### Frontend demo

[![Frontend tour: one script, three engines](docs/assets/demo-peluditos.gif)](docs/assets/demo-peluditos.mp4)

A tour of the real-time frontend: every option, the same pet-insurance script synthesized with `phonon`, `piper` and `pocket_tts`, and a walkthrough of the three comparison charts. The GIF is silent; [watch the full video with Spanish narration](docs/assets/demo-peluditos.mp4) (voice `valentina-phonon`, es-CO). Figures shown are interactive measurements, not benchmark results. Music: Sascha Ende, [ende.app](https://ende.app/en) (CC BY 4.0).

The animation above summarizes the results. Interactive version: [`results/wrapped.en.html`](results/wrapped.en.html). Full analysis: [`results/engine-selection.md`](results/engine-selection.md).

- [Engines](docs/engines.md) and [adding an engine](docs/adding-an-engine.md)
- [Voice preparation and consent](docs/voice-preparation.md)
- [Real-time performance metrics](docs/metrics.md): TTFA, RTF, throughput, load time, resources, and how to compare runs
- [Speaker similarity and consistency metrics](docs/speaker-similarity.md): cloned-voice similarity to the reference, repetition consistency, and the Spanish EER check
- [Intelligibility metrics (WER and CER)](docs/intelligibility.md): speech recognizer based accuracy per engine, Spanish normalization, and how to compare runs

## Intelligibility metrics: recognizer environment

Only the `transcribe` stage needs a speech recognizer. Keep it in its own environment so engine environments stay unchanged:

```
python3.11 -m venv .venv-asr
.venv-asr/bin/pip install -e ".[asr]"
```

`synthesize` runs in the engine's environment, `transcribe` in `.venv-asr`, and `score`, `compare` and `errors` in any environment (they use only the standard library and numpy). The `--model fake` option needs no recognizer.

## Speaker similarity metrics: embedding environment

Only the `embed` stage needs a speaker-embedding model. Keep it in its own environment:

```
python3.11 -m venv .venv-spk
.venv-spk/bin/pip install -e ".[speaker]"
```

`synthesize` runs in the cloning engine's environment, `embed` in `.venv-spk`, and `score` and `compare` in any environment (standard library and numpy only). The `--model fake` option needs no model. See [docs/speaker-similarity.md](docs/speaker-similarity.md).

## Real-time backend

The backend gateway needs `fastapi`, `uvicorn` and `websockets` (the `backend` extra) and `httpx` for its tests. Install them into `.venv-core`:

```bash
.venv-core/bin/pip install -e ".[dev,backend]"
# if .venv-core has no pip:
uv pip install --python .venv-core/bin/python -e ".[dev,backend]"
```

Start it with `.venv-core/bin/python -m tts_bench.backend serve` (http://127.0.0.1:8000; `/v1/health`, `/v1/engines`, `WS /v1/ws/synthesize`, `POST /v1/synthesize`). Tests need no weights: `.venv-core/bin/python -m pytest tests/backend -q`.

Engines keep their own virtual environments; the gateway starts one worker per engine in that engine's venv (see `docs/backend.md`).

See [docs/backend.md](docs/backend.md) for the real-time backend (endpoints, metric definitions, limits).

## Frontend

A static page for live testing of the real-time backend: type Spanish text, hear it stream, compare engines one at a time and read the backend's latency figures. It is a live-testing aid, not a benchmark; the numbers it shows are interactive measurements. No build step and no external network.

```bash
.venv-core/bin/python -m tts_bench.backend serve                          # terminal 1
python -m http.server 5173 --bind 127.0.0.1 --directory frontend          # terminal 2
```

Open http://127.0.0.1:5173 in Chrome, Safari or Firefox. The backend must be running first; the page's Backend URL field defaults to `http://127.0.0.1:8000`. The page's origin is allowed by the backend's CORS setting (default `http://127.0.0.1:5173` and `http://localhost:5173`; change it with `TTS_BACKEND_CORS_ORIGINS` or `cors_origins` in `backend.toml` if you use another port or host).

Frontend tests (Node 20+, no install step): `node --test frontend/tests/` and, with the fake engine, `.venv-core/bin/python` available, `node frontend/tests/e2e-fake-engine.mjs`. See [docs/frontend.md](docs/frontend.md).

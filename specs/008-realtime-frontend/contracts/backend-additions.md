# Contract: Additions to the 007 Backend

Both additions are additive and opt-in/read-only. Existing 007 behavior and tests are unchanged.

## GET /v1/corpus

Read-only list of corpus sentences for the picker (FR-006).

```json
{"corpus_version":"<from corpus/VERSION.json>","count":123,
 "sentences":[{"id":"COB-002","text":"El saldo actual de su tarjeta es de ...","campaign":"collections","scenario":"card_balance","tags":["amount_cop"]}]}
```

Rules:

- Source: `corpus/sentences.jsonl` via `tts_bench.corpus.loader`, `main` subset only.
- `text` is the sentence's spoken form (`Sentence.speak_text`).
- Never reads or returns `cloning.jsonl`, reference recordings, or any file path.
- Corpus directory missing or malformed -> `503` JSON `ErrorBody` with code `corpus_unavailable` and no filesystem path; the rest of the API keeps working.

## CORS

- New setting `cors_origins` (env `TTS_BACKEND_CORS_ORIGINS`, comma separated; `backend.toml` key `cors_origins`). Default: `http://127.0.0.1:5173` and `http://localhost:5173`.
- Allowed methods `GET, POST`; no credentials; no wildcard `*`.
- The WebSocket handler also rejects a browser `Origin` that is not in the allowlist (browsers do not apply CORS to WebSockets). A request with no `Origin` header (curl, tests) is still accepted.
- Setting the list to empty disables browser access entirely.

## Unchanged guarantees (re-checked by tests)

| Rule | Check |
|------|-------|
| FR-010 (007) | `/v1/corpus` and CORS responses contain no voice path, hash or id; existing `test_privacy.py` still passes |
| No static serving | `frontend/` is never mounted by the gateway |
| Loopback default | binding unchanged |

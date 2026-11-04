"""Gateway: HTTP/WebSocket routes, validation and error mapping.

Imports no engine. The only module that needs fastapi.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI, Request, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, Response
from starlette.websockets import WebSocketDisconnect, WebSocketState

from ..corpus import loader as corpus_loader
from ..voices.library import LocalVoiceLibrary
from . import catalog as catalog_mod
from .config import BackendConfig
from .errors import BackendError
from .requestlog import RequestLog
from .scrub import scrub_paths
from .supervisor import EngineSupervisor, active_engine_count
from .wav import pcm16_to_wav

NOT_AVAILABLE = "not available"
STREAMING_NOTICE = "This engine does not stream: the complete audio is delivered in one piece and TTFA is not available."


def _version() -> str:
    try:
        from importlib.metadata import version

        return version("tts-bench")
    except Exception:  # noqa: BLE001
        return "0.1.0"


class Validated:
    def __init__(self, **kw) -> None:
        self.__dict__.update(kw)


def create_app(config: BackendConfig | None = None, supervisors: dict | None = None, library=None) -> FastAPI:
    config = config or BackendConfig.load()
    if library is None:
        voices_root = Path(config.voices_dir) if config.voices_dir else LocalVoiceLibrary().root
        library = LocalVoiceLibrary(voices_root if voices_root.is_absolute() else config.repo_root / voices_root)
    supervisors = supervisors if supervisors is not None else {}
    catalog = catalog_mod.Catalog(config, library, supervisors)
    log_path = Path(config.log_path)
    request_log = RequestLog(
        log_path if log_path.is_absolute() else config.repo_root / log_path,
        log_text=config.log_text, max_bytes=config.log_max_bytes, keep=config.log_keep,
    )
    roots = (str(config.repo_root), str(getattr(library, "root", "") or ""))

    def scrub(text: str) -> str:
        return scrub_paths(text, tuple(str(Path(r).resolve()) for r in roots if r) + roots)

    def scrubbed_body(err: BackendError) -> dict:
        body = err.body()
        return {k: (scrub(v) if isinstance(v, str) else v) for k, v in body.items()}

    def supervisor(engine: str) -> EngineSupervisor:
        if engine not in supervisors:
            supervisors[engine] = EngineSupervisor(config, engine)
        return supervisors[engine]

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        yield
        for sup in list(supervisors.values()):
            await asyncio.to_thread(sup.shutdown)

    app = FastAPI(title="tts-bench real-time backend", version=_version(), lifespan=lifespan,
                  docs_url=None, redoc_url=None, openapi_url=None)
    app.state.config = config
    app.state.supervisors = supervisors
    app.state.catalog = catalog
    app.state.request_log = request_log

    allowed_origins = [o for o in config.cors_origins if o and o != "*"]
    if allowed_origins:
        app.add_middleware(CORSMiddleware, allow_origins=allowed_origins, allow_methods=["GET", "POST"],
                           allow_headers=["content-type"], allow_credentials=False)

    @app.exception_handler(BackendError)
    async def _backend_error(_request, exc: BackendError):
        return JSONResponse(scrubbed_body(exc), status_code=exc.status)

    # -- helpers -----------------------------------------------------------
    async def available_engines() -> list[str]:
        names = await asyncio.to_thread(catalog.engines)
        results = await asyncio.gather(*[asyncio.to_thread(catalog.availability, n) for n in names])
        return [n for n, a in zip(names, results) if a["status"] == "available"]

    async def validate(payload) -> Validated:
        if not isinstance(payload, dict):
            raise BackendError("bad_request", "The request must be a JSON object.")
        engine = payload.get("engine")
        voice = payload.get("voice")
        text = payload.get("text")
        options = payload.get("options") or {}
        if not isinstance(options, dict):
            raise BackendError("bad_request", "'options' must be an object.")
        request_id = str(options.get("request_id") or uuid.uuid4())
        names = await asyncio.to_thread(catalog.engines)
        if engine not in names:
            raise BackendError("unknown_engine", f"Unknown engine '{engine}'.",
                               available=await available_engines())
        availability = await asyncio.to_thread(catalog.availability, engine)
        if availability["status"] != "available":
            raise BackendError("engine_unavailable", f"Engine '{engine}' is unavailable ({availability.get('reason')}).",
                               reason=availability.get("reason"), hint=availability.get("hint"))
        if not isinstance(text, str) or not text.strip():
            raise BackendError("text_empty", "The text is empty.")
        desc = await asyncio.to_thread(catalog.descriptor, engine)
        limit = config.max_chars
        if desc and desc.get("input_limits", {}).get("max_chars") is not None:
            limit = min(limit, desc["input_limits"]["max_chars"])
        if len(text) > limit:
            raise BackendError("text_too_long", f"The text has {len(text)} characters; the limit is {limit}.",
                               limit=limit, received=len(text))
        if not isinstance(voice, str):
            raise BackendError("unknown_voice", "A voice name is required.",
                               available=[v["name"] for v in catalog_mod.voices_for(engine, library)])
        ref = await asyncio.to_thread(catalog_mod.resolve_voice, engine, voice, library)
        voices = {v["name"]: v for v in catalog_mod.voices_for(engine, library)}
        return Validated(
            engine=engine, voice=voice, text=text, request_id=request_id, ref=ref,
            accent_label=voices[voice]["accent_label"], desc=desc or {},
            stream=bool(options.get("stream", True)),
        )

    def worker_error(header: dict) -> BackendError:
        code = header.get("code", "synthesis_failed")
        msg = header.get("message", "")
        if code in ("not_installed", "weights_missing"):
            return BackendError("engine_unavailable", msg, reason=code, hint=msg)
        if code not in ("empty_audio", "text_too_long", "synthesis_failed"):
            code = "synthesis_failed"
        return BackendError(code, msg)

    def start_message(v: Validated, job, chunk: dict) -> dict:
        d = v.desc
        granularity = d.get("streaming", {}).get("granularity")
        msg = {
            "type": "start", "request_id": v.request_id, "engine": v.engine,
            "engine_version": (job.sup.descriptor or d).get("engine_version"),
            "model_id": (job.sup.descriptor or d).get("model_id"),
            "spanish_variant": (job.sup.descriptor or d).get("spanish_variant"),
            "voice": v.voice, "accent_label": v.accent_label, "granularity": granularity,
            "sample_rate": chunk["sample_rate"], "channels": chunk["channels"], "sample_format": "s16le",
            "streaming": granularity != "none", "queue_wait_ms": job.queue_wait_ms,
            "concurrent_engines": job.concurrent_engines,
        }
        if granularity == "none":
            msg["streaming_available"] = False
            msg["notice"] = STREAMING_NOTICE
        if job.load_ms is not None:
            msg["load_ms"] = job.load_ms
            msg["first_request_after_load"] = True
        return msg

    def summary_dict(job, done: dict) -> dict:
        s = {
            "ttfa_ms": done["ttfa_ms"] if done.get("ttfa_ms") is not None else NOT_AVAILABLE,
            "generation_ms": done["generation_ms"], "audio_seconds": done["audio_seconds"],
            "rtf": done["rtf"], "chunks": done["chunks"], "queue_wait_ms": job.queue_wait_ms,
            "granularity": done["granularity"], "kind": "interactive",
        }
        if job.load_ms is not None:
            s["load_ms"] = job.load_ms
            s["first_request_after_load"] = True
        return s

    def log(v, payload, status, *, error=None, summary=None, job=None, engine_version=None) -> None:
        payload = payload if isinstance(payload, dict) else {}
        opts = payload.get("options") if isinstance(payload.get("options"), dict) else {}
        desc = getattr(v, "desc", {}) if v else {}
        if job is not None and job.sup.descriptor:
            desc = job.sup.descriptor  # real version/model id reported by the loaded worker
        try:
            request_log.log_request(
                request_id=(v.request_id if v else None) or opts.get("request_id"),
                engine=payload.get("engine"), voice=payload.get("voice"), text=payload.get("text")
                if isinstance(payload.get("text"), str) else "", status=status,
                engine_version=engine_version or desc.get("engine_version"), model_id=desc.get("model_id"),
                error=error, summary=summary,
                concurrent_engines=job.concurrent_engines if job else active_engine_count(),
            )
        except OSError:
            pass

    def status_for(err: BackendError) -> str:
        if err.code == "empty_audio":
            return "invalid"
        if err.code in ("synthesis_failed", "worker_timeout", "worker_crashed", "load_failed"):
            return "failed"
        return "rejected"

    # -- routes --------------------------------------------------------------
    @app.get("/v1/health")
    async def health():
        return {"status": "ok", "version": _version(),
                "limits": {"max_chars": config.max_chars, "queue_waiting": config.queue_waiting}}

    @app.get("/v1/corpus")
    async def corpus():
        corpus_dir = config.repo_root / "corpus"
        try:
            version = corpus_loader.read_version(corpus_dir)
            sentences = corpus_loader.read_sentences(corpus_dir / corpus_loader.SENTENCES_FILE)
        except (corpus_loader.CorpusError, OSError):
            return JSONResponse({"error": "corpus_unavailable", "message": "The corpus is not available."},
                                status_code=503)
        items = [{"id": s.id, "text": s.speak_text, "campaign": s.campaign.value,
                  "scenario": s.scenario.value, "tags": [t.value for t in s.tags]}
                 for s in sentences if s.subset.value == "main"]
        return {"corpus_version": version.version, "count": len(items), "sentences": items}

    @app.get("/v1/engines")
    async def list_engines():
        names = await asyncio.to_thread(catalog.engines)
        items = await asyncio.gather(*[asyncio.to_thread(catalog.listing, n) for n in names])
        return {"engines": list(items)}

    @app.post("/v1/engines/refresh")
    async def refresh_engines():
        catalog.refresh()
        return await list_engines()

    async def require_engine(name: str) -> None:
        if name not in await asyncio.to_thread(catalog.engines):
            raise BackendError("unknown_engine", f"Unknown engine '{name}'.", available=await available_engines())

    @app.get("/v1/engines/{name}")
    async def one_engine(name: str):
        await require_engine(name)
        return await asyncio.to_thread(catalog.listing, name)

    @app.post("/v1/engines/{name}/load")
    async def load_engine(name: str):
        await require_engine(name)
        availability = await asyncio.to_thread(catalog.availability, name)
        if availability["status"] != "available":
            raise BackendError("engine_unavailable", f"Engine '{name}' is unavailable ({availability.get('reason')}).",
                               reason=availability.get("reason"), hint=availability.get("hint"))
        load_ms = await supervisor(name).load()
        if load_ms is None:
            return {"load_ms": None, "already_loaded": True}
        return {"load_ms": load_ms}

    @app.websocket("/v1/ws/synthesize")
    async def ws_synthesize(ws: WebSocket):
        await ws.accept()
        origin = ws.headers.get("origin")
        if origin is not None and origin.rstrip("/") not in allowed_origins:
            # Browsers do not apply CORS to WebSockets, so the Origin is checked here.
            await ws.send_json({"type": "error", "error": "bad_request",
                                "message": "This browser origin is not allowed to use the backend."})
            await ws.close()
            return
        v = None
        payload = None
        closed = False

        async def send_json(obj) -> bool:
            nonlocal closed
            if closed:
                return False
            try:
                await ws.send_json(obj)
                return True
            except Exception:  # noqa: BLE001
                closed = True
                return False

        async def send_bytes(data) -> bool:
            nonlocal closed
            if closed:
                return False
            try:
                await ws.send_bytes(data)
                return True
            except Exception:  # noqa: BLE001
                closed = True
                return False

        async def send_error(err: BackendError) -> None:
            await send_json({"type": "error", **scrubbed_body(err)})

        try:
            try:
                payload = await ws.receive_json()
            except WebSocketDisconnect:
                return
            except Exception:  # noqa: BLE001
                err = BackendError("bad_request", "The first message must be a JSON request.")
                await send_error(err)
                log(None, None, "rejected", error=err.message)
                return
            try:
                v = await validate(payload)
                sup = supervisor(v.engine)
                job_cm = sup.acquire()
                job = await job_cm.__aenter__()
            except BackendError as err:
                await send_error(err)
                log(v, payload, status_for(err), error=err.message)
                return
            status, error, summary, receiver = "ok", None, None, None
            try:
                async def receive_loop():
                    nonlocal closed
                    try:
                        while True:
                            msg = await ws.receive()
                            if msg["type"] == "websocket.disconnect":
                                closed = True
                                job.request_cancel()
                                return
                            text = msg.get("text")
                            if text:
                                try:
                                    if json.loads(text).get("cancel"):
                                        job.request_cancel()
                                except ValueError:
                                    pass
                    except Exception:  # noqa: BLE001
                        closed = True
                        job.request_cancel()

                receiver = asyncio.create_task(receive_loop())
                started = False
                voice = {"name": v.ref.name, "kind": v.ref.kind, "path_or_id": v.ref.path_or_id}
                async for header, payload_bytes in job.stream(v.text, voice, v.request_id,
                                                              config.request_timeout_s):
                    kind = header["type"]
                    if kind == "chunk":
                        if not started:
                            started = True
                            await send_json(start_message(v, job, header))
                        await send_json({"type": "chunk", "index": header["index"], "at_ms": header["at_ms"],
                                         "gap_ms": header["gap_ms"], "samples": header["samples"]})
                        await send_bytes(payload_bytes)
                        if closed:
                            job.request_cancel()
                    elif kind == "done":
                        if header["status"] == "cancelled":
                            status = "cancelled"
                        else:
                            summary = summary_dict(job, header)
                            await send_json({"type": "summary", **summary})
                    elif kind == "error":
                        raise worker_error(header)
            except BackendError as err:
                status, error = status_for(err), err.message
                await send_error(err)
            finally:
                if receiver is not None:
                    receiver.cancel()
                try:
                    await job_cm.__aexit__(None, None, None)
                finally:  # also when this task itself is being cancelled
                    if status == "ok" and summary is None:
                        status = "cancelled"
                    log(v, payload, status, error=error, summary=summary, job=job)
        finally:
            if ws.application_state == WebSocketState.CONNECTED:
                try:
                    await ws.close()
                except Exception:  # noqa: BLE001
                    pass

    @app.post("/v1/synthesize")
    async def synthesize(request: Request):
        try:
            payload = await request.json()
        except ValueError:
            err = BackendError("bad_request", "The body must be valid JSON.")
            log(None, None, "rejected", error=err.message)
            raise err
        v = None
        try:
            v = await validate(payload)
        except BackendError as err:
            log(v, payload, status_for(err), error=err.message)
            raise
        sup = supervisor(v.engine)
        job_cm = sup.acquire()
        try:
            job = await job_cm.__aenter__()
        except BackendError as err:
            log(v, payload, status_for(err), error=err.message)
            raise

        async def watch_disconnect():
            while True:
                if await request.is_disconnected():
                    job.request_cancel()
                    return
                await asyncio.sleep(0.1)

        watcher = asyncio.create_task(watch_disconnect())
        pcm = bytearray()
        first = None
        summary = None
        status, error = "ok", None
        try:
            voice = {"name": v.ref.name, "kind": v.ref.kind, "path_or_id": v.ref.path_or_id}
            async for header, payload_bytes in job.stream(v.text, voice, v.request_id, config.request_timeout_s):
                if header["type"] == "chunk":
                    first = first or header
                    pcm.extend(payload_bytes)
                elif header["type"] == "done":
                    if header["status"] == "cancelled":
                        status = "cancelled"
                    else:
                        summary = summary_dict(job, header)
                elif header["type"] == "error":
                    raise worker_error(header)
        except BackendError as err:
            status, error = status_for(err), err.message
            raise
        finally:
            watcher.cancel()
            try:
                await job_cm.__aexit__(None, None, None)
            finally:
                if status == "ok" and summary is None:
                    status = "cancelled"
                log(v, payload, status, error=error, summary=summary, job=job)
        if summary is None or first is None:
            raise BackendError("cancelled", "The request was cancelled.")
        wav = pcm16_to_wav(bytes(pcm), first["sample_rate"], first["channels"])
        headers = {"X-TTS-Summary": json.dumps(summary, separators=(",", ":"), ensure_ascii=True),
                   "X-TTS-Request-Id": v.request_id}
        if summary["granularity"] == "none":
            headers["X-TTS-Streaming"] = "unavailable"
        return Response(wav, media_type="audio/wav", headers=headers)

    return app

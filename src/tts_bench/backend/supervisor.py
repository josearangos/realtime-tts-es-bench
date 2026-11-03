"""Per-engine worker lifecycle: lazy spawn, bounded queue, cancel, kill/restart."""

from __future__ import annotations

import asyncio
import os
import queue
import subprocess
import sys
import threading
import time
from pathlib import Path

from .config import BackendConfig
from .errors import BackendError
from .protocol import ProtocolError, read_frame, write_frame

_ACTIVE: set[int] = set()  # ids of supervisors with an active synthesis


def active_engine_count() -> int:
    return len(_ACTIVE)


class EngineSupervisor:
    def __init__(self, config: BackendConfig, engine: str) -> None:
        self.config = config
        self.engine = engine
        self.state = "not_started"
        self.descriptor: dict | None = None
        self.unavailable: dict | None = None  # set when a load fails; cleared on refresh
        self.events: list[str] = []  # lifecycle log: "started", "killed", ...
        self._proc: subprocess.Popen | None = None
        self._frames: asyncio.Queue | None = None
        self._loop: asyncio.AbstractEventLoop | None = None
        self._lock: asyncio.Lock | None = None
        self._loop_for_lock: asyncio.AbstractEventLoop | None = None
        self._waiting = 0
        self._running = False
        self._write_lock = threading.Lock()

    # -- introspection ---------------------------------------------------
    @property
    def queue_depth(self) -> int:
        return self._waiting

    def clear_unavailable(self) -> None:
        self.unavailable = None

    # -- process management ----------------------------------------------
    def _worker_env(self) -> dict:
        env = dict(os.environ)
        src = str(self.config.repo_root / "src")
        env["PYTHONPATH"] = src + (os.pathsep + env["PYTHONPATH"] if env.get("PYTHONPATH") else "")
        env.update({k: str(v) for k, v in self.config.worker_env.items()})
        return env

    def _spawn(self) -> None:
        python = self.config.venv_python(self.engine)
        if not Path(python).is_file():
            raise BackendError(
                "engine_unavailable",
                f"Engine '{self.engine}' is unavailable: its virtual environment is missing.",
                reason="venv_missing", hint=f"Create the engine's venv or set it in backend.toml ({self.engine}).",
            )
        log_dir = self.config.log_dir
        log_dir.mkdir(parents=True, exist_ok=True)
        err = open(log_dir / f"worker-{self.engine}.log", "ab")
        self._proc = subprocess.Popen(
            [str(python), "-m", "tts_bench.backend.worker", self.engine],
            stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=err,
            env=self._worker_env(), cwd=str(self.config.repo_root),
        )
        err.close()
        self._loop = asyncio.get_running_loop()
        self._frames = asyncio.Queue()
        threading.Thread(
            target=self._reader, args=(self._proc, self._loop, self._frames), daemon=True
        ).start()
        self.events.append("started")

    @staticmethod
    def _reader(proc, loop, frames) -> None:
        def put(item):
            try:
                loop.call_soon_threadsafe(frames.put_nowait, item)
            except RuntimeError:  # loop closed
                pass

        try:
            while True:
                frame = read_frame(proc.stdout)
                if frame is None:
                    break
                put(frame)
        except (ProtocolError, ValueError, OSError):
            pass
        put(None)

    def _send(self, header: dict) -> None:
        with self._write_lock:
            try:
                write_frame(self._proc.stdin, header)
            except (BrokenPipeError, OSError, ValueError):
                pass  # the reader will report the death

    def _kill(self, reason: str = "killed") -> None:
        proc, self._proc = self._proc, None
        if proc is not None:
            try:
                proc.kill()
            except OSError:
                pass
            try:
                proc.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            for stream in (proc.stdin, proc.stdout):
                try:
                    stream.close()
                except (OSError, ValueError):
                    pass
        self._frames = None
        self.state = "not_started"
        self.events.append(reason)

    def shutdown(self) -> None:
        proc = self._proc
        if proc is None:
            return
        try:
            proc.stdin.close()
            proc.wait(timeout=3)
        except Exception:  # noqa: BLE001
            pass
        self._kill("shutdown")

    async def _next(self, timeout: float | None):
        """Next frame from the worker; raises BackendError if the worker died."""
        if self._frames is None:
            raise BackendError("worker_crashed", f"The '{self.engine}' worker is not running.")
        item = await asyncio.wait_for(self._frames.get(), timeout)
        if item is None:
            self._kill("crashed")
            raise BackendError("worker_crashed", f"The '{self.engine}' worker stopped unexpectedly.")
        return item

    # -- loading -----------------------------------------------------------
    async def _ensure_loaded(self) -> float | None:
        if self.state in ("ready", "busy"):
            if self._loop is asyncio.get_running_loop():
                return None
            self._kill("restarted")
        self.state = "loading"
        try:
            self._spawn()
            header, _ = await self._next(30)
            if header.get("type") != "ready":
                raise BackendError("load_failed", "The worker did not report ready.")
            self._send({"type": "load"})
            header, _ = await self._next(None)
        except BackendError:
            if self.state == "loading":
                self._kill("failed")
            raise
        if header["type"] == "error":
            self._kill("failed")
            code = header.get("code", "load_failed")
            if code in ("not_installed", "weights_missing"):
                self.unavailable = {"status": "unavailable", "reason": code, "hint": header.get("message", "")}
                raise BackendError("engine_unavailable", header.get("message", ""), reason=code,
                                   hint=header.get("message", ""))
            raise BackendError("load_failed", header.get("message", "load failed"))
        self.descriptor = header["descriptor"]
        self.state = "ready"
        return float(header["load_ms"])

    async def load(self) -> float | None:
        """Explicit load (POST /v1/engines/{name}/load). Returns load_ms or None if already loaded."""
        async with self.acquire() as job:
            return job.load_ms

    # -- synthesis -------------------------------------------------------
    def acquire(self) -> "Job":
        return Job(self)


class Job:
    """One slot on the engine: `async with supervisor.acquire() as job`."""

    def __init__(self, sup: EngineSupervisor) -> None:
        self.sup = sup
        self.queue_wait_ms = 0.0
        self.load_ms: float | None = None
        self.concurrent_engines = 0
        self.finished = False  # a done/error frame was seen
        self._synthesizing = False
        self._holding = False

    async def __aenter__(self) -> "Job":
        sup = self.sup
        if sup._lock is None or sup._loop_for_lock is not asyncio.get_running_loop():
            sup._lock = asyncio.Lock()
            sup._loop_for_lock = asyncio.get_running_loop()
        if sup._running and sup._waiting >= sup.config.queue_waiting:
            raise BackendError(
                "engine_busy", f"Engine '{sup.engine}' is busy and its queue is full.",
                queue_depth=sup._waiting,
            )
        sup._waiting += 1
        t0 = time.perf_counter_ns()
        try:
            await sup._lock.acquire()
        finally:
            sup._waiting -= 1
        self._holding = True
        sup._running = True
        self.queue_wait_ms = (time.perf_counter_ns() - t0) / 1e6
        try:
            self.load_ms = await sup._ensure_loaded()
        except BaseException:
            await self._release()
            raise
        self.concurrent_engines = len(_ACTIVE - {id(sup)})
        _ACTIVE.add(id(sup))
        sup.state = "busy"
        return self

    async def _release(self) -> None:
        sup = self.sup
        if self._holding:
            self._holding = False
            sup._running = False
            _ACTIVE.discard(id(sup))
            if sup.state == "busy":
                sup.state = "ready"
            sup._lock.release()

    def request_cancel(self) -> None:
        if self._synthesizing and not self.finished:
            self.sup._send({"type": "cancel"})

    async def stream(self, text: str, voice: dict, request_id: str | None, timeout: float | None = None):
        """Yield (header, payload) from `start` through `done`/`error`.

        On timeout the job is cancelled (grace rule) and worker_timeout is raised."""
        sup = self.sup
        self._synthesizing = True
        sup._send({"type": "synthesize", "text": text, "voice": voice, "request_id": request_id})
        deadline = None if timeout is None else time.monotonic() + timeout
        while True:
            remaining = None if deadline is None else max(deadline - time.monotonic(), 0.0)
            try:
                header, payload = await sup._next(remaining)
            except asyncio.TimeoutError:
                await self.cancel()
                raise BackendError("worker_timeout", f"Engine '{sup.engine}' exceeded the request timeout.")
            if header["type"] in ("done", "error"):
                self.finished = True
            yield header, payload
            if self.finished:
                return

    async def cancel(self) -> None:
        """Ask the worker to stop; kill and restart it if it is not idle within the grace period."""
        sup = self.sup
        if self.finished or not self._synthesizing or sup._proc is None:
            return
        sup._send({"type": "cancel"})
        deadline = time.monotonic() + sup.config.cancel_grace_s
        try:
            while True:
                header, _ = await sup._next(max(deadline - time.monotonic(), 0.0))
                if header["type"] in ("done", "error"):
                    self.finished = True
                    return
        except asyncio.TimeoutError:
            sup._kill("killed")
            self.finished = True
        except BackendError:
            self.finished = True

    async def __aexit__(self, exc_type, exc, tb) -> None:
        cancelled = False
        try:
            if self._synthesizing and not self.finished and self.sup.state == "busy":
                # Graceful stop first. Even if this task is itself being cancelled (client
                # gone), keep waiting for the bounded stop so the worker is not killed needlessly.
                task = asyncio.ensure_future(self.cancel())
                while not task.done():
                    try:
                        await asyncio.shield(task)
                    except asyncio.CancelledError:
                        cancelled = True
                    except Exception:  # noqa: BLE001
                        self.sup._kill("killed")
                        break
        finally:
            await self._release()
        if cancelled:
            raise asyncio.CancelledError

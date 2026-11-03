"""Engine worker: `python -m tts_bench.backend.worker ENGINE [--describe]`.

Wraps one adapter. `--describe` prints the descriptor as JSON without loading weights.
Serve mode speaks length-prefixed frames on stdin/stdout (stdout is reserved for frames;
logs go to stderr). The worker never writes audio to disk.
"""

from __future__ import annotations

import dataclasses
import json
import os
import queue
import sys
import threading
import time

from ..core.errors import (
    EmptyAudioError,
    EngineNotInstalledError,
    InputLimitError,
    SynthesisError,
    WeightsMissingError,
)
from ..core.voices import VoiceReference
from ..metrics.timing import timing_from_marks
from .protocol import ProtocolError, read_frame, write_frame
from .scrub import scrub_paths
from .wav import float_to_pcm16


def build_adapter(engine: str):
    """The fake engine takes its timings from TTS_FAKE_* variables (tests only)."""
    if engine.startswith("fake"):
        from ..adapters.fake import FakeAdapter

        kwargs: dict = {"name": engine}
        for var, key, cast in (
            ("TTS_FAKE_FIRST_CHUNK_S", "first_chunk_delay_s", float),
            ("TTS_FAKE_CHUNK_INTERVAL_S", "chunk_interval_s", float),
            ("TTS_FAKE_AUDIO_S", "audio_seconds", float),
            ("TTS_FAKE_CHUNKS", "n_chunks", int),
            ("TTS_FAKE_GRANULARITY", "granularity", str),
            ("TTS_FAKE_LOAD_S", "load_delay_s", float),
            ("TTS_FAKE_FAIL_AFTER", "fail_after_chunks", int),
            ("TTS_FAKE_MAX_CHARS", "max_chars", int),
        ):
            if os.environ.get(var):
                kwargs[key] = cast(os.environ[var])
        return FakeAdapter(**kwargs)
    from .. import adapters  # noqa: F401  (registers engines)
    from ..core.registry import get_adapter

    return get_adapter(engine)


def _fake_failure() -> str | None:
    return os.environ.get("TTS_FAKE_DESCRIBE_FAIL")


def _classify(exc: BaseException) -> tuple[str, str]:
    if isinstance(exc, EngineNotInstalledError):
        return "not_installed", str(exc)
    if isinstance(exc, WeightsMissingError):
        return "weights_missing", str(exc)
    return "error", str(exc)


def _raise_fake_failure(adapter) -> None:
    mode = _fake_failure()
    if mode == "not_installed":
        raise EngineNotInstalledError(adapter.descriptor.name, "Run: pip install -e '.[fake]' (test hint).")
    if mode == "weights_missing":
        raise WeightsMissingError(adapter.descriptor.name, "Download the test weights (test hint).")
    if mode == "error":
        raise RuntimeError("fake describe failure")


def descriptor_dict(adapter) -> dict:
    return json.loads(json.dumps(dataclasses.asdict(adapter.descriptor)))


def describe(engine: str) -> int:
    try:
        adapter = build_adapter(engine)
        if engine.startswith("fake"):
            _raise_fake_failure(adapter)
        adapter.check_ready()
    except Exception as exc:  # noqa: BLE001
        reason, hint = _classify(exc)
        print(json.dumps({"reason": reason, "hint": scrub_paths(hint)}))
        return 2
    print(json.dumps(descriptor_dict(adapter)))
    return 0


class Worker:
    def __init__(self, engine: str, stdin, stdout) -> None:
        self.engine = engine
        self.stdin = stdin
        self.stdout = stdout
        self.adapter = build_adapter(engine)
        self.inbox: queue.Queue = queue.Queue()
        self.cancel = threading.Event()
        self.ignore_cancel = os.environ.get("TTS_FAKE_IGNORE_CANCEL") == "1" and engine.startswith("fake")

    # -- plumbing --------------------------------------------------------
    def _reader(self) -> None:
        try:
            while True:
                frame = read_frame(self.stdin)
                if frame is None:
                    break
                if frame[0].get("type") == "cancel":
                    if not self.ignore_cancel:
                        self.cancel.set()
                    continue
                self.inbox.put(frame)
        except ProtocolError:
            pass
        finally:
            self.cancel.set()
            self.inbox.put(None)

    def send(self, header: dict, payload: bytes = b"") -> None:
        write_frame(self.stdout, header, payload)

    def error(self, code: str, message: str, **extra) -> None:
        self.send({"type": "error", "code": code, "message": scrub_paths(message), **extra})

    # -- handlers --------------------------------------------------------
    def handle_load(self) -> None:
        try:
            if self.engine.startswith("fake"):
                _raise_fake_failure(self.adapter)
            self.adapter.check_ready()
            t0 = time.perf_counter_ns()
            self.adapter.load()
            load_ms = (time.perf_counter_ns() - t0) / 1e6
        except (EngineNotInstalledError, WeightsMissingError) as exc:
            code, msg = _classify(exc)
            self.error(code, msg)
        except Exception as exc:  # noqa: BLE001
            self.error("load_failed", str(exc))
        else:
            self.send({"type": "loaded", "load_ms": load_ms, "descriptor": descriptor_dict(self.adapter)})

    def handle_synthesize(self, header: dict) -> None:
        text = header["text"]
        v = header["voice"]
        voice = VoiceReference(v["name"], v["kind"], v["path_or_id"])
        self.cancel.clear()
        streams = self.adapter.descriptor.streaming.granularity != "none"
        self.send({"type": "start", "request_id": header.get("request_id")})
        marks: list[tuple[int, int, int]] = []
        total_samples = 0
        rate = channels = 0
        status = "ok"
        started = time.perf_counter_ns()
        finished = started
        try:
            if streams:
                gen = self.adapter.stream(text, voice)
                try:
                    started = time.perf_counter_ns()
                    for chunk in gen:
                        finished = chunk.produced_at_ns
                        n = int(chunk.samples.shape[0]) if chunk.samples.ndim else 0
                        rate, channels = chunk.sample_rate, chunk.channels
                        total_samples += n
                        marks.append((chunk.index, chunk.produced_at_ns, int(chunk.samples.size)))
                        prev = marks[-2][1] if len(marks) > 1 else started
                        self.send(
                            {
                                "type": "chunk", "index": chunk.index,
                                "at_ms": (chunk.produced_at_ns - started) / 1e6,
                                "gap_ms": (chunk.produced_at_ns - prev) / 1e6,
                                "samples": n, "sample_rate": rate, "channels": channels,
                            },
                            float_to_pcm16(chunk.samples),
                        )
                        if self.cancel.is_set():
                            status = "cancelled"
                            break
                finally:
                    gen.close()
            else:
                result = self.adapter.synthesize(text, voice)
                started = result.request_started_ns
                finished = result.finished_ns
                rate = result.sample_rate
                channels = 1
                audio = result.audio
                total_samples = int(audio.shape[0]) if audio.ndim else 0
                marks = []
                self.send(
                    {"type": "chunk", "index": 0, "at_ms": (finished - started) / 1e6,
                     "gap_ms": (finished - started) / 1e6, "samples": total_samples,
                     "sample_rate": rate, "channels": channels},
                    float_to_pcm16(audio),
                )
        except EmptyAudioError as exc:
            return self.error("empty_audio", str(exc))
        except InputLimitError as exc:
            return self.error("text_too_long", str(exc))
        except (EngineNotInstalledError, WeightsMissingError) as exc:
            code, msg = _classify(exc)
            return self.error(code, msg)
        except SynthesisError as exc:
            return self.error("synthesis_failed", str(exc))
        except Exception as exc:  # noqa: BLE001
            return self.error("synthesis_failed", f"Synthesis failed in '{self.engine}': {exc}")
        n_chunks = len(marks) if streams else 1
        if status == "ok" and total_samples == 0:
            return self.error("empty_audio", f"Engine '{self.engine}' produced no audio.")
        audio_seconds = (total_samples / rate) if rate else 0.0
        timing = timing_from_marks(started, marks, finished, audio_seconds, streams)
        self.send(
            {
                "type": "done", "status": status,
                "generation_ms": timing.generation_ms, "ttfa_ms": timing.ttfa_ms,
                "rtf": timing.rtf, "audio_seconds": audio_seconds, "chunks": n_chunks,
                "granularity": self.adapter.descriptor.streaming.granularity,
                "engine_version": self.adapter.descriptor.engine_version,
                "model_id": self.adapter.descriptor.model_id,
                "spanish_variant": self.adapter.descriptor.spanish_variant,
            }
        )

    # -- main loop -------------------------------------------------------
    def serve(self) -> int:
        threading.Thread(target=self._reader, daemon=True).start()
        self.send({"type": "ready", "descriptor": descriptor_dict(self.adapter)})
        while True:
            item = self.inbox.get()
            if item is None:
                break
            header, _ = item
            kind = header.get("type")
            if kind == "load":
                self.handle_load()
            elif kind == "synthesize":
                self.handle_synthesize(header)
            elif kind == "describe":
                self.send({"type": "ready", "descriptor": descriptor_dict(self.adapter)})
        try:
            self.adapter.close()
        except Exception:  # noqa: BLE001
            pass
        return 0


def main(argv: list[str] | None = None) -> int:
    args = list(sys.argv[1:] if argv is None else argv)
    if not args or args[0].startswith("-"):
        print("usage: python -m tts_bench.backend.worker ENGINE [--describe]", file=sys.stderr)
        return 1
    engine = args[0]
    if "--describe" in args[1:]:
        return describe(engine)
    # stdout is reserved for frames: route stray prints to stderr
    real_stdout = sys.stdout.buffer
    sys.stdout = sys.stderr
    return Worker(engine, sys.stdin.buffer, real_stdout).serve()


if __name__ == "__main__":
    raise SystemExit(main())

"""Synthesis stage: one synthesis per main-corpus sentence, WAV files plus a manifest."""

from __future__ import annotations

import wave
from pathlib import Path

import numpy as np

from ..core.errors import EmptyAudioError, TTSBenchError
from ..corpus import Corpus, corpus_stamp
from .audio_check import inspect_wav
from .files import environment_block, sha256_file, write_manifest
from .model import Manifest, ManifestItem


def write_pcm16(path: Path, audio: np.ndarray, sample_rate: int, channels: int = 1) -> None:
    x = np.asarray(audio)
    if np.issubdtype(x.dtype, np.integer):
        pcm = x.astype("<i2") if x.dtype != np.int16 else x
    else:
        pcm = np.round(np.clip(x.astype(np.float64), -1.0, 1.0) * 32767.0).astype("<i2")
    with wave.open(str(path), "wb") as w:
        w.setnchannels(channels)
        w.setsampwidth(2)
        w.setframerate(sample_rate)
        w.writeframes(pcm.tobytes())


def _engine_block(adapter, voice_info: dict) -> dict:
    d = adapter.descriptor
    return {
        "name": d.name, "engine_version": d.engine_version, "model_id": d.model_id,
        "spanish_variant": d.spanish_variant, "streaming_granularity": d.streaming.granularity,
        "voice": voice_info,
    }


def synthesize_corpus(
    adapter, corpus: Corpus, voice, out_dir: str | Path, *,
    limit: int | None = None, voice_info: dict | None = None, command: str = "",
) -> Manifest:
    """Load the engine once, synthesize each sentence once in corpus order, write
    `<id>.wav` (engine's own sample rate, PCM 16-bit) and `manifest.json` into `out_dir`.

    The text sent is the sentence `text`. The voice must already be resolved through the
    voice library by the caller. A TTSBenchError from load() propagates (nothing written).
    """
    out = Path(out_dir)
    sentences = corpus.sentences[:limit] if limit is not None else corpus.sentences
    info = voice_info or {"name": voice.name, "kind": voice.kind, "checksum": None}
    adapter.load()
    items: list[ManifestItem] = []
    try:
        out.mkdir(parents=True, exist_ok=True)
        for s in sentences:
            try:
                result = adapter.synthesize(s.text, voice)
            except EmptyAudioError as exc:
                items.append(ManifestItem(s.id, None, "silent", str(exc), None, 0.0, None))
                continue
            except TTSBenchError as exc:
                items.append(ManifestItem(s.id, None, "failed", str(exc)))
                continue
            audio = np.asarray(result.audio)
            channels = result.chunks[0].channels if result.chunks else 1
            if audio.ndim > 1:
                channels = audio.shape[1]
                audio = audio.reshape(-1)
            name = f"{s.id}.wav"
            write_pcm16(out / name, audio, result.sample_rate, channels)
            facts = inspect_wav(out / name)
            items.append(ManifestItem(
                s.id, name, "silent" if facts["silent"] else "ok", None,
                result.sample_rate, round(facts["duration_s"], 6), sha256_file(out / name),
            ))
    finally:
        adapter.close()
    manifest = Manifest(
        engine=_engine_block(adapter, info),
        corpus={**corpus_stamp(corpus), "subset": "main", "limit": limit},
        command=command, environment=environment_block(), items=tuple(items),
    )
    write_manifest(manifest, out)
    return manifest

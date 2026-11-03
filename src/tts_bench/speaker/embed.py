"""Embedding stage: the reference and every clip, with one embedder and identical settings."""

from __future__ import annotations

import json
import wave
from pathlib import Path

import numpy as np

from ..intelligibility.audio_check import to_float
from .files import EMBEDDINGS_NAME, environment_block, read_manifest, sha256_file, write_embeddings
from .model import ClipEmbedding, EmbeddingsFile, ExtraEmbedding


def read_wav_mono(path: str | Path) -> tuple[np.ndarray, int]:
    with wave.open(str(path), "rb") as w:
        rate, width, ch, frames = w.getframerate(), w.getsampwidth(), w.getnchannels(), w.getnframes()
        raw = w.readframes(frames)
    if width == 2:
        x = to_float(np.frombuffer(raw, dtype="<i2"))
    elif width == 4:
        x = to_float(np.frombuffer(raw, dtype="<i4"))
    elif width == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float64) - 128.0) / 128.0
    else:
        raise ValueError(f"unsupported sample width {width} bytes")
    if ch > 1:
        x = x[: x.size // ch * ch].reshape(-1, ch).mean(axis=1)
    return x.astype(np.float32), rate


class _Cache:
    """Vectors cached by sha256(audio) + settings hash (same audio and settings, same vector)."""

    def __init__(self, directory: str | Path | None, settings_hash: str) -> None:
        self.dir = Path(directory) if directory else None
        self.suffix = settings_hash
        if self.dir:
            self.dir.mkdir(parents=True, exist_ok=True)

    def get(self, sha: str):
        if self.dir is None:
            return None
        p = self.dir / f"{sha}-{self.suffix}.json"
        return json.loads(p.read_text(encoding="utf-8")) if p.is_file() else None

    def put(self, sha: str, vector) -> None:
        if self.dir is not None:
            (self.dir / f"{sha}-{self.suffix}.json").write_text(json.dumps(list(vector)), encoding="utf-8")


def embed_directory(audio_dir: str | Path, embedder, *, reference_wav: str | Path,
                    cache_dir: str | Path | None = None, extras: tuple[ExtraEmbedding, ...] = (),
                    command: str = "") -> EmbeddingsFile:
    """Embed the reference once and every `ok` clip of `audio_dir/manifest.json`.

    Failed and silent clips are recorded with their status and no vector. The result is written to
    `audio_dir/embeddings.json` (git-ignored, never into `results/`).
    """
    root = Path(audio_dir)
    manifest = read_manifest(root)
    record = embedder.record()
    cache = _Cache(cache_dir, record.settings_hash)

    def vector_for(path: Path, sha: str, keys: tuple[str, ...]) -> tuple[float, ...]:
        hit = cache.get(sha)
        if hit is not None:
            return tuple(hit)
        samples, rate = read_wav_mono(path)
        vec = tuple(float(v) for v in np.asarray(embedder.embed(samples, rate, keys)).reshape(-1))
        cache.put(sha, vec)
        return vec

    ref_sha = sha256_file(reference_wav)
    ref_vec = vector_for(Path(reference_wav), ref_sha, ("reference", ref_sha))
    clips = []
    for item in manifest.items:
        if item.status != "ok":
            clips.append(ClipEmbedding(item.sentence_id, item.repetition, item.sha256, item.duration_s,
                                       None, item.status))
            continue
        keys = (item.sha256, f"{item.sentence_id}-r{item.repetition}")
        clips.append(ClipEmbedding(item.sentence_id, item.repetition, item.sha256, item.duration_s,
                                   vector_for(root / item.file, item.sha256, keys), "ok"))
    result = EmbeddingsFile(
        record, manifest.engine, manifest.corpus, manifest.repetitions, manifest.designated_repetition,
        manifest.reference, ref_sha, ref_vec, tuple(clips), tuple(extras), command, environment_block())
    write_embeddings(result, root / EMBEDDINGS_NAME)
    return result

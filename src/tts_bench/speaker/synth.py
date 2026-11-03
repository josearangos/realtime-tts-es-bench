"""Synthesis stage: the cloning subset, N repetitions, WAV files plus a manifest."""

from __future__ import annotations

from pathlib import Path

import numpy as np

from ..core.errors import EmptyAudioError, TTSBenchError
from ..corpus import Corpus, corpus_stamp
from ..intelligibility.audio_check import inspect_wav
from ..intelligibility.synth import write_pcm16
from .files import environment_block, sha256_file, write_manifest
from .model import SUBSET, Manifest, ManifestItem, ReferenceQuality

DESIGNATED_REPETITION = 1
DEFAULT_REPETITIONS = 5


def not_applicable_message(engine: str) -> str:
    return f"not applicable: {engine} does not clone voices"


def synthesize_cloning(
    adapter, corpus: Corpus, voice, out_dir: str | Path, *, repetitions: int = DEFAULT_REPETITIONS,
    limit: int | None = None, voice_info: dict | None = None,
    reference_quality: ReferenceQuality, command: str = "",
) -> Manifest | None:
    """Synthesize each cloning sentence `repetitions` times with the cloned `voice`.

    Returns None and writes nothing when the engine does not clone voices (FR-006). Otherwise the
    engine is loaded once; for each repetition in order and each sentence in corpus order the
    sentence text is synthesized once and written as `<sentence_id>-r<N>.wav` at the engine's own
    sample rate. A load failure propagates and nothing is written.
    """
    if not adapter.descriptor.supports_cloning:
        return None
    if repetitions < 1:
        raise ValueError("repetitions must be >= 1")
    out = Path(out_dir)
    sentences = corpus.sentences[:limit] if limit is not None else corpus.sentences
    info = voice_info or {"name": voice.name, "kind": voice.kind}
    adapter.load()
    items: list[ManifestItem] = []
    try:
        out.mkdir(parents=True, exist_ok=True)
        for rep in range(1, repetitions + 1):
            for s in sentences:
                try:
                    result = adapter.synthesize(s.text, voice)
                except EmptyAudioError as exc:
                    items.append(ManifestItem(s.id, rep, None, "silent", str(exc), None, 0.0, None))
                    continue
                except TTSBenchError as exc:
                    items.append(ManifestItem(s.id, rep, None, "failed", str(exc)))
                    continue
                audio = np.asarray(result.audio)
                channels = result.chunks[0].channels if result.chunks else 1
                if audio.ndim > 1:
                    channels = audio.shape[1]
                    audio = audio.reshape(-1)
                name = f"{s.id}-r{rep}.wav"
                write_pcm16(out / name, audio, result.sample_rate, channels)
                facts = inspect_wav(out / name)
                items.append(ManifestItem(
                    s.id, rep, name, "silent" if facts["silent"] else "ok", None, result.sample_rate,
                    round(facts["duration_s"], 6), sha256_file(out / name)))
    finally:
        adapter.close()
    d = adapter.descriptor
    manifest = Manifest(
        engine={"name": d.name, "engine_version": d.engine_version, "model_id": d.model_id,
                "spanish_variant": d.spanish_variant, "supports_cloning": d.supports_cloning,
                "voice": info},
        corpus={**corpus_stamp(corpus), "subset": SUBSET, "limit": limit},
        repetitions=repetitions, designated_repetition=DESIGNATED_REPETITION,
        reference=reference_quality, command=command, environment=environment_block(),
        items=tuple(items))
    write_manifest(manifest, out)
    return manifest

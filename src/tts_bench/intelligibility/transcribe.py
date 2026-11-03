"""Transcription stage: one recognizer, one settings set, skips silent and failed audio."""

from __future__ import annotations

import json
from pathlib import Path

from .files import environment_block, sha256_json
from .model import Manifest, Transcript, Transcripts


def _cache_path(cache_dir: Path, audio_sha: str, settings_hash: str) -> Path:
    return cache_dir / f"{audio_sha}-{settings_hash[:16]}.json"


def transcribe_manifest(
    manifest: Manifest, audio_dir: str | Path, recognizer, cache_dir: str | Path | None = None,
    *, command: str = "",
) -> Transcripts:
    """Transcribe every `ok` item. `silent` items are `skipped_silent` and failed or missing
    audio is `skipped_failed`; the recognizer is not called for them. Text is stored raw."""
    audio = Path(audio_dir)
    record = recognizer.record()
    cache = Path(cache_dir) if cache_dir is not None else None
    if cache is not None:
        cache.mkdir(parents=True, exist_ok=True)
    out: list[Transcript] = []
    for item in manifest.items:
        if item.status == "silent":
            out.append(Transcript(item.sentence_id, item.sha256, "skipped_silent"))
            continue
        path = audio / item.file if item.file else None
        if item.status == "failed" or path is None or not path.is_file():
            out.append(Transcript(item.sentence_id, item.sha256, "skipped_failed"))
            continue
        hit = _cache_path(cache, item.sha256 or "", record.settings_hash) if cache and item.sha256 else None
        if hit is not None and hit.is_file():
            text = json.loads(hit.read_text(encoding="utf-8"))["text"]
        else:
            text = recognizer.transcribe(path)
            if hit is not None:
                hit.write_text(json.dumps({"text": text}, ensure_ascii=False), encoding="utf-8")
        out.append(Transcript(item.sentence_id, item.sha256, "ok", text))
    return Transcripts(
        recognizer=record, engine=manifest.engine, corpus=manifest.corpus,
        manifest_sha256=sha256_json(manifest.to_dict()), command=command,
        environment=environment_block(), transcripts=tuple(out),
    )

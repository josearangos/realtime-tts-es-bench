"""Reference audio and its quality, read from the voice library (consent enforced there)."""

from __future__ import annotations

import tempfile
from pathlib import Path

from .model import ReferenceQuality

USE = "internal_benchmarking"


def resolve_reference(library, voice_name: str, *, engine: str, use: str = USE, content: str | None = None,
                      work_dir: str | Path | None = None) -> tuple[Path, ReferenceQuality]:
    """-> (path of the reference WAV, ReferenceQuality). The path is never stored.

    `resolve` enforces consent (errors propagate). A `reference_audio` voice uses its stored
    `reference.wav`; any other cloned voice (a stored voice file, as Phonon uses) uses the original
    consented recording segment named by the library entry, cut with the library's segment helper.
    """
    entry = library.show(voice_name)
    ref = library.resolve(voice_name, entry["kind"], engine=engine, use=use, content=content)
    rec = library.recording(entry["recording_id"])
    if entry["kind"] == "reference_audio":
        wav = Path(ref.path_or_id)
    else:
        seg = entry["segment"]
        folder = Path(work_dir) if work_dir else Path(tempfile.mkdtemp(prefix="speaker-ref-"))
        wav = library.prepare_segment(
            entry["recording_id"], engine, seg["start_s"], seg["length_s"],
            dest=folder / f"{voice_name}-reference.wav")
    quality = ReferenceQuality(
        rec["recording_id"], rec["duration_s"], rec["speech_seconds"], rec["snr_estimate_db"],
        rec["accent"], tuple(rec["warnings"]))
    return wav, quality

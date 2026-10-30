from __future__ import annotations

from pathlib import Path

from .library import LocalVoiceLibrary

# Known primary Spanish variant per engine. Unverified: "unknown" until the owner confirms it,
# so no accent_mismatch warning is raised for these engines.
ENGINE_PRIMARY_VARIANT: dict[str, str] = {"phonon": "unknown", "pocket_tts": "unknown", "piper": "unknown"}

PHONON_STEPS = """Phonon voices are created outside this repository:
1. Open https://studio.gradium.ai/ and clone a voice from: {segment}
   (the audio is uploaded to that third-party service; the speaker's consent must cover it)
2. Download the resulting .safetensors file.
3. Register it with the same recording so engines share one source:
   python -m tts_bench.voices register {name} --engine phonon --kind stored_voice_file \\
     --file <downloaded.safetensors> --recording {rec} --start {start} --length {length} \\
     --creation "external: studio.gradium.ai" --accent {accent}"""


def _mismatch(engine: str, accent: str) -> list[str]:
    known = ENGINE_PRIMARY_VARIANT.get(engine, "unknown")
    return [f"accent_mismatch:{engine}"] if known != "unknown" and accent != "unknown" and known != accent else []


def prepare_for_engine(
    lib: LocalVoiceLibrary,
    recording_id: str,
    engine: str,
    name: str,
    start_s: float | None = None,
    length_s: float | None = None,
) -> str:
    """Prepare a voice for `engine`; returns a human-readable message."""
    seg = lib.segment_for(recording_id, start_s, length_s)  # also enforces consent
    rec = lib.recording(recording_id)
    if engine == "pocket_tts":
        lib.ensure_free(name)
        dest = lib.root / "voices" / name / "reference.wav"
        lib.prepare_segment(recording_id, engine, seg["start_s"], seg["length_s"], dest=dest)
        lib.register(
            name, engine, "reference_audio", dest, recording_id=recording_id, segment=seg,
            creation="automated", accent_label=rec["accent"],
            extra_warnings=_mismatch(engine, rec["accent"]),
        )
        return f"registered '{name}' for pocket_tts from {recording_id} segment {seg}"
    if engine == "phonon":
        dest = lib.prepare_segment(recording_id, engine, seg["start_s"], seg["length_s"])
        return PHONON_STEPS.format(
            segment=dest, name=name, rec=recording_id, start=seg["start_s"], length=seg["length_s"], accent=rec["accent"]
        )
    raise ValueError(f"engine '{engine}' cannot be prepared automatically (supported: pocket_tts, phonon)")

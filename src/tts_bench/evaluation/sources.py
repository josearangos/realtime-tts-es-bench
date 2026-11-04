"""Discover synthesized clips (features 004-006 layouts or a generic manifest) and validate against the corpus."""

from __future__ import annotations

import json
import sys
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

from tts_bench.corpus import CorpusError, load_corpus
from tts_bench.corpus.loader import default_corpus_dir


class SourceError(ValueError):
    """Bad or unknown source data (CLI exit code 2)."""


@dataclass(frozen=True)
class SourceClip:
    engine: str
    voice: str
    accent: str
    cloned: bool
    sentence_id: str
    corpus_subset: str
    wav_path: str
    sample_rate: int
    reference_wav: str | None = None

    @property
    def condition(self) -> str:
        return f"{self.engine}/{self.voice}"


@dataclass(frozen=True)
class CorpusInfo:
    version: str
    content_sha256: str
    texts: dict  # sentence_id -> written text


def load_corpus_info(corpus_dir: str | Path | None = None) -> CorpusInfo:
    # cwd first: inside the provisioner the package lives in /opt/src, so the repo-relative default is wrong there
    directory = Path(corpus_dir) if corpus_dir else (Path("corpus") if Path("corpus").is_dir() else default_corpus_dir())
    texts: dict[str, str] = {}
    version = sha = ""
    try:
        for subset in ("main", "cloning"):
            c = load_corpus(directory, subset)
            version, sha = c.version, c.content_hash
            texts.update({s.id: s.text for s in c.sentences})
    except (CorpusError, OSError) as exc:
        raise SourceError(f"corpus: {exc}") from None
    return CorpusInfo(version, sha, texts)


def _rate(path: Path) -> int:
    try:
        with wave.open(str(path), "rb") as w:
            if w.getnchannels() < 1:
                raise SourceError(f"{path}: not a readable WAV")
            return w.getframerate()
    except (wave.Error, EOFError, OSError) as exc:
        raise SourceError(f"{path}: not a readable WAV ({exc})") from None


USE = "human_evaluation"  # consent purpose checked by the voice library before any cloned voice is used


def discover_layout(output_root: str | Path, voices_dir: str | Path | None = None) -> list[SourceClip]:
    """Read output/speaker/* and output/intelligibility/* `manifest.json` files (schema_version 1).

    Sidecar fields used: engine.name, engine.voice.{name,kind,accent_label}, reference.accent,
    corpus.subset, items[].{file,sentence_id,status,sample_rate,repetition}, repetitions.designated.
    """
    from tts_bench.voices.library import LocalVoiceLibrary

    output_root = Path(output_root)
    library = LocalVoiceLibrary(voices_dir) if voices_dir else LocalVoiceLibrary()
    ref_dir = Path(tempfile.mkdtemp(prefix="eval-ref-"))
    refs: dict[str, str | None] = {}
    clips: list[SourceClip] = []
    seen: set[tuple] = set()
    for kind in ("speaker", "intelligibility"):
        base = output_root / kind
        if not base.is_dir():
            continue
        for d in sorted(p for p in base.iterdir() if (p / "manifest.json").is_file()):
            m = json.loads((d / "manifest.json").read_text(encoding="utf-8"))
            eng = m.get("engine", {})
            voice = eng.get("voice", {})
            name, vname = eng.get("name"), voice.get("name")
            if not name or not vname:
                continue
            accent = voice.get("accent_label") or m.get("reference", {}).get("accent") or "unknown"
            cloned = voice.get("kind") == "reference_audio"
            ref = None
            if cloned:
                if vname not in refs:
                    refs[vname] = _reference(library, vname, name, ref_dir)
                if refs[vname] == _DENIED:
                    continue  # consent does not cover human evaluation: the voice is not used at all
                ref = refs[vname]
            designated = m.get("repetitions", {}).get("designated")
            subset = m.get("corpus", {}).get("subset", "main")
            for it in m.get("items", []):
                if it.get("status") != "ok" or (designated is not None and it.get("repetition", designated) != designated):
                    continue
                wav = d / it["file"]
                key = (name, vname, it["sentence_id"])
                if not wav.is_file() or key in seen:
                    continue
                seen.add(key)
                clips.append(SourceClip(name, vname, accent, cloned, it["sentence_id"], subset, str(wav),
                                        int(it.get("sample_rate") or _rate(wav)), ref))
    return clips


_DENIED = "<denied>"


def _reference(library, voice: str, engine: str, work_dir: Path) -> str | None:
    """Reference WAV through the voice library (consent enforced there). None when the voice is not in the library."""
    from tts_bench.speaker.reference import resolve_reference
    from tts_bench.voices.library import ConsentNotPermittedError, ConsentRequiredError, VoiceNotFoundError

    try:
        wav, _quality = resolve_reference(library, voice, engine=engine, use=USE, work_dir=work_dir)
        return str(wav)
    except VoiceNotFoundError:
        return None
    except (ConsentNotPermittedError, ConsentRequiredError) as exc:
        print(f"warning: voice {voice!r} excluded from human evaluation: {exc}", file=sys.stderr)
        return _DENIED


def read_source_manifest(path: str | Path) -> list[SourceClip]:
    """Generic JSONL: engine, voice, accent, cloned, sentence_id, wav [, reference, subset]."""
    clips = []
    for n, line in enumerate(Path(path).read_text(encoding="utf-8").splitlines(), 1):
        if not line.strip():
            continue
        try:
            r = json.loads(line)
            wav = Path(r["wav"])
            ref = r.get("reference")
            clips.append(SourceClip(r["engine"], r["voice"], r.get("accent", "unknown"), bool(r.get("cloned", False)),
                                    r["sentence_id"], r.get("subset", "main"), str(wav), _rate(wav),
                                    str(ref) if ref else None))
        except (KeyError, json.JSONDecodeError) as exc:
            raise SourceError(f"{path}:{n}: invalid manifest line ({exc})") from None
    return clips


def validate(clips: list[SourceClip], corpus: CorpusInfo) -> list[SourceClip]:
    for c in clips:
        if c.sentence_id not in corpus.texts:
            raise SourceError(f"unknown sentence_id {c.sentence_id!r} (clip of {c.condition}) is not in corpus {corpus.version}")
    return clips


def discover(output_root: str | Path, corpus: CorpusInfo, manifests: list[str | Path] = (),
             voices_dir: str | Path | None = None) -> list[SourceClip]:
    clips = discover_layout(output_root, voices_dir)
    for m in manifests:
        clips.extend(read_source_manifest(m))
    return validate(clips, corpus)

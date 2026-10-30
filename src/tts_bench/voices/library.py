from __future__ import annotations

import datetime
import hashlib
import json
import os
import re
import shutil
from dataclasses import asdict, dataclass, field
from pathlib import Path

from ..core.descriptor import VoiceKind
from ..core.errors import (
    ConsentNotPermittedError,
    ConsentRequiredError,
    VoiceAlreadyRegisteredError,
    VoiceEngineMismatchError,
    VoiceIntegrityError,
    VoiceNotFoundError,
)
from ..core.voices import VoiceReference
from . import audio_check
from .consent import CONTENT, USES, ConsentRecord

_NAME = re.compile(r"[A-Za-z0-9_-]+")
DEFAULT_SEGMENT_S = 20.0


@dataclass
class RecordingInfo:
    recording_id: str
    consent_id: str
    file: str
    sample_rate: int
    duration_s: float
    speech_seconds: float
    snr_estimate_db: float
    accent: str
    warnings: list[str]
    added: str


@dataclass
class WithdrawReport:
    voices_removed: list[str] = field(default_factory=list)
    files_deleted: int = 0
    results_marked: list[str] = field(default_factory=list)
    tombstones_written: int = 0

    def __str__(self) -> str:
        return (
            f"withdrew {len(self.voices_removed)} voice(s) {self.voices_removed}, "
            f"deleted {self.files_deleted} file(s), marked {len(self.results_marked)} result file(s), "
            f"wrote {self.tombstones_written} tombstone(s)"
        )


def sha256_file(path: Path) -> str:
    h = hashlib.sha256()
    with Path(path).open("rb") as f:
        for block in iter(lambda: f.read(1 << 20), b""):
            h.update(block)
    return h.hexdigest()


def _today() -> str:
    return datetime.date.today().isoformat()


def _check_name(name: str) -> None:
    if not _NAME.fullmatch(name or ""):
        raise ValueError(f"invalid voice name {name!r}: use letters, digits, '_' and '-'")


class LocalVoiceLibrary:
    def __init__(self, root: str | Path = "cloned_voices"):
        self.root = Path(root)
        self._index_unreadable = False

    # ---- index storage -------------------------------------------------
    @property
    def _index_path(self) -> Path:
        return self.root / "library.json"

    def _empty(self) -> dict:
        return {"version": 1, "recordings": {}, "voices": {}, "withdrawn": []}

    def _load(self) -> dict:
        try:
            data = json.loads(self._index_path.read_text(encoding="utf-8"))
            if not isinstance(data, dict):
                raise ValueError("index is not an object")
        except FileNotFoundError:
            return self._empty()
        except (OSError, ValueError):
            self._index_unreadable = True
            return self._empty()
        for k, v in self._empty().items():
            data.setdefault(k, v)
        return data

    def _save(self, data: dict) -> None:
        self.root.mkdir(parents=True, exist_ok=True)
        if self._index_unreadable and self._index_path.exists():
            shutil.copy2(self._index_path, self._index_path.with_suffix(".json.corrupt"))
            self._index_unreadable = False
        tmp = self._index_path.with_suffix(".json.tmp")
        tmp.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
        os.replace(tmp, self._index_path)

    def _consent_path(self, consent_id: str) -> Path:
        return self.root / "consent" / f"{consent_id}.json"

    def _abs(self, rel: str) -> Path:
        p = Path(rel)
        return p if p.is_absolute() else self.root / p

    def _rel(self, p: Path) -> str:
        try:
            return str(Path(p).resolve().relative_to(self.root.resolve()))
        except ValueError:
            return str(Path(p).resolve())

    # ---- consent and recordings ---------------------------------------
    def add_consent(self, record: ConsentRecord) -> None:
        record.save(self._consent_path(record.alias))

    def consent(self, consent_id: str) -> ConsentRecord:
        path = self._consent_path(consent_id)
        if not path.is_file():
            raise ConsentRequiredError(
                f"consent required for '{consent_id}': run `python -m tts_bench.voices consent add --alias {consent_id} …`"
            )
        return ConsentRecord.load(path)

    def add_recording(
        self,
        wav: Path,
        consent_id: str,
        accent: str,
        no_music_confirmed: bool = False,
        noise_threshold_db: float = 20.0,
    ) -> RecordingInfo:
        self.consent(consent_id)  # refuse before copying anything
        wav = Path(wav)
        analysis = audio_check.analyze(wav)
        warns = audio_check.warnings(analysis, noise_threshold_db)
        if not no_music_confirmed:
            warns.append("music_not_ruled_out")
        rec_id = "rec-" + sha256_file(wav)[:12]
        dst = self.root / "recordings" / f"{rec_id}.wav"
        dst.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(wav, dst)
        info = RecordingInfo(
            recording_id=rec_id,
            consent_id=consent_id,
            file=self._rel(dst),
            accent=accent,
            warnings=warns,
            added=_today(),
            **analysis,
        )
        data = self._load()
        data["recordings"][rec_id] = asdict(info)
        self._save(data)
        return info

    def recording(self, recording_id: str) -> dict:
        rec = self._load()["recordings"].get(recording_id)
        if rec is None:
            raise VoiceNotFoundError(f"No recording '{recording_id}'")
        return rec

    # ---- preparing -----------------------------------------------------
    def segment_for(self, recording_id: str, start_s: float | None, length_s: float | None) -> dict:
        rec = self.recording(recording_id)
        self.consent(rec["consent_id"])
        start = 0.0 if start_s is None else float(start_s)
        length = float(length_s) if length_s is not None else min(DEFAULT_SEGMENT_S, rec["duration_s"] - start)
        return {"start_s": start, "length_s": max(length, 0.0)}

    def prepare_segment(
        self,
        recording_id: str,
        engine: str,
        start_s: float | None = None,
        length_s: float | None = None,
        *,
        dest: Path | None = None,
    ) -> Path:
        """Write the trimmed reference segment; returns its path. Refuses without consent."""
        seg = self.segment_for(recording_id, start_s, length_s)
        rec = self.recording(recording_id)
        dest = Path(dest) if dest else self.root / "recordings" / "segments" / f"{recording_id}-{engine}.wav"
        audio_check.write_segment(self._abs(rec["file"]), dest, seg["start_s"], seg["length_s"])
        return dest

    # ---- registering ---------------------------------------------------
    def _taken(self, data: dict, name: str) -> bool:
        return name in data["voices"] or any(t["name"] == name for t in data["withdrawn"])

    def ensure_free(self, name: str) -> None:
        _check_name(name)
        if self._taken(self._load(), name):
            raise VoiceAlreadyRegisteredError(f"voice '{name}' is already registered or was withdrawn")

    def register(
        self,
        name: str,
        engine: str,
        kind: VoiceKind,
        file: Path,
        *,
        recording_id: str | None,
        segment: dict | None,
        creation: str,
        accent_label: str,
        extra_warnings: list[str] | None = None,
    ) -> None:
        _check_name(name)
        data = self._load()
        if self._taken(data, name):
            raise VoiceAlreadyRegisteredError(f"voice '{name}' is already registered or was withdrawn")
        if not recording_id or not segment:
            raise ConsentRequiredError(
                "a cloned voice needs --recording and a segment (start/length) tied to a consented recording"
            )
        rec = data["recordings"].get(recording_id)
        if rec is None:
            raise VoiceNotFoundError(f"No recording '{recording_id}'; run `add-recording` first")
        self.consent(rec["consent_id"])
        dst_dir = self.root / "voices" / name
        dst_dir.mkdir(parents=True, exist_ok=True)
        dst = dst_dir / Path(file).name
        if Path(file).resolve() != dst.resolve():
            shutil.copyfile(file, dst)
        data["voices"][name] = {
            "name": name,
            "engine": engine,
            "kind": kind,
            "cloned": True,
            "file": self._rel(dst),
            "owned": True,
            "sha256": sha256_file(dst),
            "recording_id": recording_id,
            "consent_id": rec["consent_id"],
            "segment": {"start_s": float(segment["start_s"]), "length_s": float(segment["length_s"])},
            "creation": creation,
            "accent_label": accent_label,
            "warnings": list(rec["warnings"]) + list(extra_warnings or []),
            "created": _today(),
        }
        self._save(data)

    def register_fixed(self, name: str, engine: str, voice_id_or_file: str, accent_label: str, creation: str) -> None:
        _check_name(name)
        candidate = Path(voice_id_or_file)
        is_file = candidate.is_file()
        if engine == "piper":
            voice_id = candidate.name.removesuffix(".onnx") if is_file else voice_id_or_file
            if name != voice_id:
                raise ValueError(
                    f"for piper the library name must equal the voice id ('{voice_id}'), got '{name}': "
                    "the Piper adapter derives accent, model id and licence from the name"
                )
        data = self._load()
        if self._taken(data, name):
            raise VoiceAlreadyRegisteredError(f"voice '{name}' is already registered or was withdrawn")
        data["voices"][name] = {
            "name": name,
            "engine": engine,
            "kind": "fixed_voice",
            "cloned": False,
            "file": self._rel(candidate) if is_file else voice_id_or_file,
            "owned": False,
            "sha256": sha256_file(candidate) if is_file else None,
            "recording_id": None,
            "consent_id": None,
            "segment": None,
            "creation": creation,
            "accent_label": accent_label,
            "warnings": [],
            "created": _today(),
        }
        self._save(data)

    # ---- resolving -----------------------------------------------------
    def _entry(self, data: dict, name: str, engine: str | None = None) -> dict:
        entry = data["voices"].get(name)
        if entry is None:
            known = sorted(n for n, v in data["voices"].items() if engine is None or v["engine"] == engine)
            raise VoiceNotFoundError(f"No voice '{name}'. Known: {known}")
        return entry

    def resolve(
        self,
        name: str,
        kind: VoiceKind | None = None,
        *,
        engine: str | None = None,
        use: str | None = None,
        content: str | None = None,
    ) -> VoiceReference:
        e = self._entry(self._load(), name, engine)
        if engine is not None and e["engine"] != engine:
            raise VoiceEngineMismatchError(f"voice '{name}' belongs to engine '{e['engine']}', not '{engine}'")
        if kind is not None and e["kind"] != kind:
            raise VoiceEngineMismatchError(
                f"voice '{name}' is a '{e['kind']}' voice for engine '{e['engine']}', not '{kind}' (engine '{engine or e['engine']}')"
            )
        if e["cloned"]:
            record = self.consent(e["consent_id"])
            for label, value, allowed in (("use", use, USES), ("content", content, CONTENT)):
                if value is not None and value not in allowed:
                    raise ConsentNotPermittedError(f"invalid {label} '{value}'; allowed: {list(allowed)}")
            missing = record.permits(use, content)
            if missing:
                raise ConsentNotPermittedError(f"consent for '{e['consent_id']}' does not permit '{missing}'")
        self._check_integrity(e)
        if e["sha256"] is None:
            return VoiceReference(name, e["kind"], e["file"])
        return VoiceReference(name, e["kind"], str(self._abs(e["file"]).resolve()))

    def _check_integrity(self, e: dict) -> None:
        if e["sha256"] is None:
            return
        path = self._abs(e["file"])
        if not path.is_file():
            raise VoiceIntegrityError(f"voice '{e['name']}': file {path} is missing", "missing")
        actual = sha256_file(path)
        if actual != e["sha256"]:
            raise VoiceIntegrityError(
                f"voice '{e['name']}': file modified (expected sha256 {e['sha256']}, actual {actual})", "modified"
            )

    # ---- views ---------------------------------------------------------
    def public_index(self) -> list[dict]:
        keys = ("name", "engine", "kind", "cloned", "accent_label", "sha256", "recording_id")
        return [{k: v[k] for k in keys} for v in self._load()["voices"].values()]

    def show(self, name: str) -> dict:
        return dict(self._entry(self._load(), name))

    def same_source(self, names: list[str]) -> bool:
        data = self._load()
        ids = set()
        for n in names:
            rid = self._entry(data, n)["recording_id"]
            if rid is None:
                return False
            ids.add(rid)
        return len(ids) == 1

    def verify(self, name: str | None = None) -> list[tuple[str, str]]:
        """Every problem found as (voice name, description); empty when all is fine."""
        data = self._load()
        names = [name] if name else sorted(data["voices"])
        problems = []
        for n in names:
            e = self._entry(data, n)
            if e["cloned"] and not self._consent_path(e["consent_id"]).is_file():
                problems.append((n, "consent record missing"))
            try:
                self._check_integrity(e)
            except VoiceIntegrityError as exc:
                problems.append((n, str(exc)))
        return problems

    # ---- removing ------------------------------------------------------
    def _drop_voice_files(self, e: dict) -> int:
        count = 0
        for d in (self.root / "voices" / e["name"], self.root / "generated" / e["name"]):
            if d.is_dir():
                count += sum(1 for p in d.rglob("*") if p.is_file())
                shutil.rmtree(d)
        return count

    def remove(self, name: str) -> None:
        data = self._load()
        e = self._entry(data, name)
        self._drop_voice_files(e)
        del data["voices"][name]
        self._save(data)

    def withdraw(self, consent_id: str, results_dir: Path | None = None) -> WithdrawReport:
        data = self._load()
        report = WithdrawReport()
        today = _today()
        for name, e in list(data["voices"].items()):
            if e["consent_id"] != consent_id:
                continue
            report.files_deleted += self._drop_voice_files(e)
            data["withdrawn"].append({"name": name, "recording_id": e["recording_id"], "date": today})
            del data["voices"][name]
            report.voices_removed.append(name)
            report.tombstones_written += 1
        for rid, rec in list(data["recordings"].items()):
            if rec["consent_id"] != consent_id:
                continue
            for p in [self._abs(rec["file"]), *(self.root / "recordings" / "segments").glob(f"{rid}-*")]:
                if p.is_file():
                    p.unlink()
                    report.files_deleted += 1
            del data["recordings"][rid]
        consent_file = self._consent_path(consent_id)
        if consent_file.is_file():
            consent_file.unlink()
            report.files_deleted += 1
        self._save(data)
        withdrawn = {t["name"] for t in data["withdrawn"]}
        results = Path(results_dir) if results_dir is not None else Path("results")
        if results.is_dir():
            for f in sorted(results.rglob("*.json")):
                try:
                    doc = json.loads(f.read_text(encoding="utf-8"))
                except (OSError, ValueError):
                    continue
                voice = doc.get("voice") if isinstance(doc, dict) else None
                if isinstance(voice, dict) and voice.get("name") in withdrawn and not doc.get("voice_withdrawn"):
                    doc["voice_withdrawn"] = True
                    f.write_text(json.dumps(doc, indent=2, ensure_ascii=False), encoding="utf-8")
                    report.results_marked.append(str(f))
        return report

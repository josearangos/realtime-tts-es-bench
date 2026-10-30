from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..core.errors import TTSBenchError
from .consent import ConsentRecord
from .library import LocalVoiceLibrary
from .prepare import prepare_for_engine
from .repocheck import check_repo

KINDS = ("reference_audio", "stored_voice_file", "fixed_voice")


def _csv(s: str) -> list[str]:
    return [x for x in s.split(",") if x]


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m tts_bench.voices")
    p.add_argument("--root", default="cloned_voices")
    sub = p.add_subparsers(dest="cmd", required=True)

    c = sub.add_parser("consent").add_subparsers(dest="sub", required=True).add_parser("add")
    c.add_argument("--alias", required=True)
    c.add_argument("--date", required=True)
    c.add_argument("--uses", required=True)
    c.add_argument("--content", required=True)
    c.add_argument("--notes", default="")

    a = sub.add_parser("add-recording")
    a.add_argument("file")
    a.add_argument("--consent", required=True)
    a.add_argument("--accent", required=True)
    a.add_argument("--no-music-confirmed", action="store_true")
    a.add_argument("--noise-threshold-db", type=float, default=20.0)

    pr = sub.add_parser("prepare")
    pr.add_argument("recording")
    pr.add_argument("--engine", required=True)
    pr.add_argument("--name", required=True)
    pr.add_argument("--start", type=float)
    pr.add_argument("--length", type=float)

    r = sub.add_parser("register")
    r.add_argument("name")
    r.add_argument("--engine", required=True)
    r.add_argument("--kind", required=True, choices=KINDS)
    r.add_argument("--file", required=True)
    r.add_argument("--recording", required=True)
    r.add_argument("--start", type=float, required=True)
    r.add_argument("--length", type=float, required=True)
    r.add_argument("--creation", required=True)
    r.add_argument("--accent", required=True)

    f = sub.add_parser("assign-fixed")
    f.add_argument("name")
    f.add_argument("--engine", required=True)
    f.add_argument("--voice", required=True)
    f.add_argument("--accent", required=True)

    ls = sub.add_parser("list")
    ls.add_argument("--json", action="store_true")
    sub.add_parser("show").add_argument("name")
    sub.add_parser("verify").add_argument("name", nargs="?")
    sub.add_parser("remove").add_argument("name")
    w = sub.add_parser("withdraw")
    w.add_argument("alias")
    w.add_argument("--results-dir", default="results")
    sub.add_parser("check-repo")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _parser().parse_args(argv)
    lib = LocalVoiceLibrary(args.root)
    try:
        return _run(args, lib)
    except ValueError as exc:
        print(f"invalid: {exc}", file=sys.stderr)
        return 2
    except TTSBenchError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 1


def _run(a: argparse.Namespace, lib: LocalVoiceLibrary) -> int:
    if a.cmd == "consent":
        lib.add_consent(ConsentRecord(a.alias, a.date, _csv(a.uses), _csv(a.content), a.notes))
        print(f"consent recorded for '{a.alias}'")
    elif a.cmd == "add-recording":
        info = lib.add_recording(Path(a.file), a.consent, a.accent, a.no_music_confirmed, a.noise_threshold_db)
        print(f"recording_id: {info.recording_id}")
        print(f"speech_seconds: {info.speech_seconds}  snr_estimate_db: {info.snr_estimate_db}")
        print(f"warnings: {', '.join(info.warnings) or 'none'}")
    elif a.cmd == "prepare":
        print(prepare_for_engine(lib, a.recording, a.engine, a.name, a.start, a.length))
    elif a.cmd == "register":
        lib.register(
            a.name, a.engine, a.kind, Path(a.file), recording_id=a.recording,
            segment={"start_s": a.start, "length_s": a.length}, creation=a.creation, accent_label=a.accent,
        )
        print(f"registered '{a.name}'")
    elif a.cmd == "assign-fixed":
        model = Path(args_root(a)) / f"{a.voice}.onnx"
        lib.register_fixed(a.name, a.engine, str(model) if model.is_file() else a.voice, a.accent, "downloaded model")
        print(f"registered fixed voice '{a.name}'")
    elif a.cmd == "list":
        rows = lib.public_index()
        if a.json:
            print(json.dumps(rows, indent=2, ensure_ascii=False))
        for r in ([] if a.json else rows):
            print(f"{r['name']}\t{r['engine']}\t{r['kind']}\tcloned={r['cloned']}\t{r['accent_label']}\t{r['recording_id']}")
    elif a.cmd == "show":
        print(json.dumps(lib.show(a.name), indent=2, ensure_ascii=False))
    elif a.cmd == "verify":
        problems = lib.verify(a.name)
        for n, msg in problems:
            print(f"{n}: {msg}")
        if problems:
            return 1
        print("all voices ok")
    elif a.cmd == "remove":
        lib.remove(a.name)
        print(f"removed '{a.name}'")
    elif a.cmd == "withdraw":
        print(lib.withdraw(a.alias, Path(a.results_dir)))
    elif a.cmd == "check-repo":
        found = check_repo()
        for path in found:
            print(path)
        if found:
            return 1
        print("clean: no voice material tracked or in history")
    return 0


def args_root(a: argparse.Namespace) -> str:
    return a.root


if __name__ == "__main__":
    raise SystemExit(main())

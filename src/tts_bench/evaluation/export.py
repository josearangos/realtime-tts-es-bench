"""Join Label Studio annotations with the private mapping and write the export files (contracts/export-format.md)."""

from __future__ import annotations

import csv
import hashlib
import json
import platform
import re

from pathlib import Path

import numpy as np

from . import labelconfig, scales
from .batch import load_batch, paths
from .blind import read_mapping
from .config import default_config_path, load_config
from .lsclient import LSClient
from .provision import UsageError
from .quality import compute_quality
from .tasks import PROJECTS

EMAIL_RE = re.compile(r"^(a[0-9]{2,})@eval\.invalid$")
MOS_KEYS = list(scales.MOS_CRITERIA)


class ExportError(UsageError):
    """Export refused (CLI exit code 2)."""


def _answers(project: str, result: list[dict]) -> dict:
    out = {}
    for r in result:
        name, value = r.get("from_name"), r.get("value", {})
        if "rating" in value:
            out[name] = int(value["rating"])
        elif "choices" in value and value["choices"]:
            out[name] = int(value["choices"][0])
    return out


def collect(client: LSClient, out_dir: str | Path) -> tuple[list[dict], list[dict], dict]:
    """Return (export rows, quality records, batch)."""
    p = paths(out_dir)
    batch = load_batch(out_dir)
    if batch is None or not p["mapping"].exists():
        raise ExportError("nothing to export: no batch/mapping found (run prepare/provision first)")
    mapping = {r.item_id: r for r in read_mapping(p["mapping"])}
    users = {u["id"]: u.get("email", "") for u in client.list_users()}
    projects = {pr["title"]: pr for pr in client.list_projects()}
    rows, records = [], []
    for key in PROJECTS:
        pr = projects.get(labelconfig.TITLES[key])
        if not pr:
            continue
        for task in client.export_annotations(pr["id"]):
            item_id = task.get("data", {}).get("item_id")
            m = mapping.get(item_id)
            for ann in task.get("annotations", []):
                if ann.get("was_cancelled"):
                    continue
                if m is None:
                    raise ExportError(f"annotation on item {item_id!r} has no mapping row (purged or foreign task)")
                uid = ann.get("completed_by")
                if isinstance(uid, dict):
                    uid = uid.get("id")
                match = EMAIL_RE.match(users.get(uid, ""))
                if not match:
                    raise ExportError(f"user id {uid} is not a pseudonymous annotator (aNN@eval.invalid); "
                                      "annotate only with accounts created by `make eval-annotator`")
                answers = _answers(key, ann.get("result", []))
                row = {
                    "batch_id": batch["batch_id"], "project": key, "item_id": item_id,
                    "annotator_id": match.group(1), "role": m.role, "repeat_of": m.repeat_of,
                    "engine": m.engine, "voice": m.voice, "accent": m.accent, "cloned": m.cloned,
                    "sentence_id": m.sentence_id, "corpus_version": m.corpus_version,
                    "scale_hash": batch["scale_hash"], "ls_version": batch["label_studio_version"],
                    "lead_time_s": ann.get("lead_time"), "created_at": ann.get("created_at"),
                }
                if key == "mos":
                    row["ratings"] = {k: answers.get(k) for k in MOS_KEYS}
                elif key == "cmos":
                    row["cmos"] = answers.get("cmos")
                    row.update(engine_a=m.a["engine"], voice_a=m.a["voice"], engine_b=m.b["engine"], voice_b=m.b["voice"])
                else:
                    row["sim"] = answers.get("sim")
                _check_complete(row)
                rows.append(row)
                records.append({"project": key, "item_id": item_id, "annotator_id": row["annotator_id"],
                                "role": m.role, "repeat_of": m.repeat_of, "answers": answers, "expected": m.expected})
    rows.sort(key=lambda r: (r["project"], r["item_id"], r["annotator_id"]))
    records.sort(key=lambda r: (r["project"], r["item_id"], r["annotator_id"]))
    return rows, records, batch


def _check_complete(row: dict) -> None:
    keys = ("engine_a", "voice_a", "engine_b", "voice_b") if row["project"] == "cmos" else ("engine", "voice")
    missing = [k for k in (*keys, "sentence_id", "corpus_version") if not row.get(k)]
    if missing:
        raise ExportError(f"item {row['item_id']} lacks {', '.join(missing)} in the mapping; refusing to export")


def _line(obj) -> str:
    return json.dumps(obj, ensure_ascii=False, sort_keys=True)


CSV_COLUMNS = ["batch_id", "project", "item_id", "annotator_id", "role", "repeat_of", "engine", "voice", "accent",
               "cloned", "engine_a", "voice_a", "engine_b", "voice_b", "sentence_id", "corpus_version", "scale_hash",
               "ls_version", "naturalidad", "pronunciacion", "prosodia", "cmos", "sim", "lead_time_s", "created_at"]


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_export(rows, records, batch, cfg, out: str | Path, command: str, ls_version: str) -> dict:
    out = Path(out)
    out.mkdir(parents=True, exist_ok=True)
    jl = out / "annotations.jsonl"
    jl.write_text("".join(_line(r) + "\n" for r in rows), encoding="utf-8")
    cv = out / "annotations.csv"
    with cv.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=CSV_COLUMNS, lineterminator="\n")
        w.writeheader()
        for r in rows:
            flat = {k: v for k, v in r.items() if k != "ratings"}
            flat.update(r.get("ratings", {}))
            w.writerow({k: ("" if flat.get(k) is None else flat.get(k)) for k in CSV_COLUMNS})
    quality = compute_quality(records, {"repeat_within_1_min": cfg.repeat_within_1_min,
                                        "max_failed_checks": cfg.max_failed_checks})
    qj = out / "quality.json"
    qj.write_text(json.dumps(quality, ensure_ascii=False, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    manifest = {
        "batch_id": batch["batch_id"], "config_sha256": batch["config_sha256"], "seed": batch["seed"],
        "counts": batch["counts"], "loudness": batch["loudness"], "scale_hash": batch["scale_hash"],
        "corpus_version": batch["corpus_version"], "corpus_sha256": batch["corpus_sha256"],
        "rows": len(rows),
        "files": {n: _sha(out / n) for n in ("annotations.jsonl", "annotations.csv", "quality.json")},
        "environment": {"python": platform.python_version(), "numpy": np.__version__,
                        "os": f"{platform.system()} {platform.release()}", "label_studio": ls_version},
        "command": command,
    }
    (out / "MANIFEST.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=1, sort_keys=True) + "\n",
                                       encoding="utf-8")
    return manifest


def _config(args):
    return load_config(Path("evaluation/batch.toml") if Path("evaluation/batch.toml").exists() else default_config_path())


def run_export(client: LSClient, args) -> int:
    rows, records, batch = collect(client, args.output)
    cmd = "python -m tts_bench.evaluation export" + (f" --out {args.out}" if args.out else "")
    m = write_export(rows, records, batch, _config(args), args.out, cmd, batch["label_studio_version"])
    print(f"exported {m['rows']} annotation rows to {args.out}")
    return 0


def run_quality(client: LSClient, args) -> int:
    rows, records, batch = collect(client, args.output)
    q = compute_quality(records, {"repeat_within_1_min": _config(args).repeat_within_1_min,
                                  "max_failed_checks": _config(args).max_failed_checks})
    print(json.dumps(q, ensure_ascii=False, indent=1))
    return 0

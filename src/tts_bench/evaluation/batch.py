"""`prepare`: build the frozen batch (pure function of config + sources + corpus + seed)."""

from __future__ import annotations

import hashlib
import json
import shutil
from datetime import datetime, timezone
from pathlib import Path

from . import qc, scales, tasks
from .blind import IdGenerator, make_rng, read_mapping, write_mapping
from .config import BatchConfig, ConfigError
from .sources import CorpusInfo, SourceClip


class BatchError(ValueError):
    """Frozen-batch violation or nothing to prepare (CLI exit code 2)."""


class ScaleMismatch(RuntimeError):
    """Scale definitions changed after the batch was frozen (CLI exit code 4)."""


def paths(out_dir: str | Path) -> dict:
    out = Path(out_dir)
    return {"batch": out / "batch.json", "tasks": out / "tasks.json", "served": out / "served",
            "mapping": out / "private" / "mapping.jsonl", "private": out / "private", "archive": out / "archive"}


def _fingerprint(cfg: BatchConfig, corpus: CorpusInfo, clips: list[SourceClip]) -> str:
    h = hashlib.sha256()
    h.update(f"{cfg.sha256}|{corpus.content_sha256}|{cfg.seed}|{scales.scale_hash()}".encode())
    for c in sorted(clips, key=lambda c: (c.condition, c.sentence_id)):
        h.update(f"|{c.condition}:{c.sentence_id}:{c.sample_rate}".encode())
    return h.hexdigest()


def load_batch(out_dir) -> dict | None:
    p = paths(out_dir)["batch"]
    return json.loads(p.read_text(encoding="utf-8")) if p.exists() else None


def prepare(cfg: BatchConfig, clips: list[SourceClip], corpus: CorpusInfo, out_dir: str | Path,
            ls_version: str = "1.23.2", new_batch: bool = False) -> dict:
    p = paths(out_dir)
    existing = load_batch(out_dir)
    fp = _fingerprint(cfg, corpus, clips)
    batch_id = "b-" + fp[:10]
    if existing and not new_batch:
        if existing["config_sha256"] != cfg.sha256 or existing["corpus_sha256"] != corpus.content_sha256:
            raise BatchError("the batch is frozen but batch.toml or the corpus changed; "
                             "keep them as they were or run `make eval-new-batch`")
        if existing["scale_hash"] != scales.scale_hash():
            raise ScaleMismatch("scale definitions changed after the batch was frozen; start a new batch deliberately")
        return existing
    taken: set[str] = set()
    old_rows = []
    if existing:
        if existing["batch_id"] == batch_id:
            raise BatchError("new batch would be identical to the current one; change `seed` in batch.toml first")
        arch = p["archive"] / existing["batch_id"]
        arch.mkdir(parents=True, exist_ok=True)
        for src in (p["batch"], p["tasks"], p["mapping"]):
            if src.exists():
                shutil.copy2(src, arch / src.name)
        old_rows = read_mapping(p["mapping"]) if p["mapping"].exists() else []
        taken = {r.item_id for r in old_rows} | {f[:-4] for r in old_rows for f in r.served_files}

    rng = make_rng(cfg.seed)
    ids = IdGenerator(rng, taken)
    stager = tasks.Stager(p["served"], ids, cfg)
    groups = tasks.build_groups(clips, cfg, rng)
    if not groups:
        raise BatchError("no sentence is shared by all selected conditions; nothing to evaluate")
    items = tasks.build_items(groups, cfg, corpus, rng, ids, stager)
    n_test = {k: sum(1 for i in items if i.project == k) for k in tasks.PROJECTS}
    repeats = qc.make_repeats(items, cfg, rng, ids, stager)
    attention = qc.make_attention(items, cfg, rng, ids, stager, corpus)
    all_items = items + repeats + attention
    rng.shuffle(all_items)
    for i in all_items:
        tasks.check_task_data(i.project, i.data)

    write_mapping(p["mapping"], old_rows + [i.row for i in all_items])
    task_file = {k: [i.data for i in all_items if i.project == k] for k in tasks.PROJECTS}
    p["tasks"].write_text(json.dumps(task_file, ensure_ascii=False, indent=1), encoding="utf-8")
    batch = {
        "batch_id": batch_id,
        "created": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "seed": cfg.seed,
        "corpus_version": corpus.version,
        "corpus_sha256": corpus.content_sha256,
        "scale_hash": scales.scale_hash(),
        "loudness": {"method": "rms", "rms_dbfs": cfg.loudness_rms_dbfs, "peak_limit_dbfs": cfg.peak_limit_dbfs},
        "label_studio_version": ls_version,
        "counts": {**n_test, "repeats": len(repeats), "attention": len(attention)},
        "config_sha256": cfg.sha256,
        "conditions": sorted({c.condition for c in clips}),
    }
    p["batch"].write_text(json.dumps(batch, indent=1, sort_keys=True), encoding="utf-8")
    return batch

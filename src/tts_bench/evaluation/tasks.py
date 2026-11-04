"""Build MOS / CMOS / SIM items from source clips: selection, staging of opaque normalized audio, mapping rows."""

from __future__ import annotations

import itertools
import shutil
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path

from . import scales
from .blind import IdGenerator, MappingRow
from .config import BatchConfig, ConfigError
from .loudness import normalize, read_wav, write_wav
from .sources import CorpusInfo, SourceClip

PROJECTS = ("mos", "cmos", "sim")
AUDIO_KEYS = ("audio", "audio_a", "audio_b", "reference")
URL_PREFIX = "/data/local-files/?d=served/"
TASK_KEYS = {
    "mos": {"item_id", "audio", "text"},
    "cmos": {"item_id", "audio_a", "audio_b", "text"},
    "sim": {"item_id", "reference", "audio", "text"},
}


@dataclass
class Item:
    row: MappingRow
    data: dict

    @property
    def project(self) -> str:
        return self.row.project


def url(name: str) -> str:
    return URL_PREFIX + name


def file_of(data_value: str) -> str:
    return data_value[len(URL_PREFIX):]


class Stager:
    """Writes loudness-normalized WAVs named only by opaque ids into the served directory."""

    def __init__(self, served_dir: str | Path, ids: IdGenerator, cfg: BatchConfig):
        self.dir = Path(served_dir)
        self.dir.mkdir(parents=True, exist_ok=True)
        self.ids = ids
        self.cfg = cfg

    def _put(self, samples, rate) -> str:
        name = self.ids.new() + ".wav"
        write_wav(self.dir / name, samples, rate)
        return name

    def stage_file(self, path: str | Path) -> str:
        x, rate = read_wav(path)
        return self._put(normalize(x, self.cfg.loudness_rms_dbfs, self.cfg.peak_limit_dbfs), rate)

    def stage_samples(self, samples, rate: int) -> str:
        return self._put(normalize(samples, self.cfg.loudness_rms_dbfs, self.cfg.peak_limit_dbfs), rate)

    def read(self, name: str):
        return read_wav(self.dir / name)

    def copy(self, name: str) -> str:
        new = self.ids.new() + ".wav"
        shutil.copyfile(self.dir / name, self.dir / new)
        return new


def stratified_pick(sentence_ids, n: int, rng) -> list[str]:
    """Round-robin over id prefixes (campaigns), seeded shuffle inside each stratum."""
    groups: dict[str, list[str]] = defaultdict(list)
    for sid in sorted(sentence_ids):
        groups[sid.split("-")[0]].append(sid)
    for key in sorted(groups):
        rng.shuffle(groups[key])
    picked: list[str] = []
    for tier in itertools.zip_longest(*(groups[k] for k in sorted(groups))):
        for sid in tier:
            if sid is not None and len(picked) < n:
                picked.append(sid)
    return picked


@dataclass
class Group:
    subset: str
    conditions: dict  # condition -> {sentence_id: SourceClip}
    sentences: list   # picked sentence ids shared by every condition of the group


def build_groups(clips: list[SourceClip], cfg: BatchConfig, rng) -> list[Group]:
    """Same sentences for every condition: intersect per corpus subset, then pick a stratified sample."""
    if cfg.conditions:
        wanted = set(cfg.conditions)
        clips = [c for c in clips if (c.engine, c.voice) in wanted]
    by_subset: dict[str, dict[str, dict[str, SourceClip]]] = defaultdict(lambda: defaultdict(dict))
    for c in clips:
        by_subset[c.corpus_subset][c.condition][c.sentence_id] = c
    groups = []
    for subset in sorted(by_subset):
        conds = dict(sorted(by_subset[subset].items()))
        common = set.intersection(*(set(v) for v in conds.values()))
        if not common:
            continue
        groups.append(Group(subset, conds, stratified_pick(common, cfg.sentences_per_condition, rng)))
    return groups


def _meta(clip: SourceClip, degraded: bool | None = None) -> dict:
    d = {"engine": clip.engine, "voice": clip.voice, "accent": clip.accent, "cloned": clip.cloned}
    if degraded is not None:
        d["degraded"] = degraded
    return d


def build_items(groups: list[Group], cfg: BatchConfig, corpus: CorpusInfo, rng, ids: IdGenerator,
                stager: Stager) -> list[Item]:
    items: list[Item] = []
    staged: dict[tuple, str] = {}  # (condition, sid) -> staged file, reused only to avoid re-normalising

    def clip_file(clip: SourceClip) -> str:
        return stager.stage_file(clip.wav_path)

    for g in groups:
        conds = list(g.conditions)
        # MOS: every condition x every picked sentence
        for cond in conds:
            for sid in g.sentences:
                clip = g.conditions[cond][sid]
                iid, f = ids.new(), clip_file(clip)
                row = MappingRow(iid, "mos", sentence_id=sid, corpus_version=corpus.version, engine=clip.engine,
                                 voice=clip.voice, accent=clip.accent, cloned=clip.cloned, served_files=[f])
                items.append(Item(row, {"item_id": iid, "audio": url(f), "text": corpus.texts[sid]}))
        # CMOS: pairs, A/B swap balanced per pair
        if cfg.cmos_pairs == "all":
            pairs = list(itertools.combinations(conds, 2))
        else:
            pairs = [tuple(p) for p in cfg.cmos_pairs if p[0] in g.conditions and p[1] in g.conditions]
        for c1, c2 in pairs:
            order = list(g.sentences)
            rng.shuffle(order)
            for k, sid in enumerate(order):
                swap = k % 2 == 1
                ca, cb = (c2, c1) if swap else (c1, c2)
                a, b = g.conditions[ca][sid], g.conditions[cb][sid]
                iid, fa, fb = ids.new(), clip_file(a), clip_file(b)
                row = MappingRow(iid, "cmos", sentence_id=sid, corpus_version=corpus.version, a=_meta(a), b=_meta(b),
                                 position="ba" if swap else "ab", served_files=[fa, fb])
                items.append(Item(row, {"item_id": iid, "audio_a": url(fa), "audio_b": url(fb),
                                        "text": corpus.texts[sid]}))
        # SIM: cloned voices with a reference clip
        for cond in conds:
            for sid in g.sentences:
                clip = g.conditions[cond][sid]
                if not (clip.cloned and clip.reference_wav):
                    continue
                iid, f, ref = ids.new(), clip_file(clip), stager.stage_file(clip.reference_wav)
                row = MappingRow(iid, "sim", sentence_id=sid, corpus_version=corpus.version, engine=clip.engine,
                                 voice=clip.voice, accent=clip.accent, cloned=True, served_files=[ref, f])
                items.append(Item(row, {"item_id": iid, "reference": url(ref), "audio": url(f),
                                        "text": corpus.texts[sid]}))
    if not items:
        raise ConfigError("no comparable sentences across the selected conditions (check batch.toml conditions)")
    return items


def check_task_data(project: str, data: dict) -> None:
    if set(data) != TASK_KEYS[project]:
        raise ValueError(f"{project}: task data keys {sorted(data)} differ from the contract")


def cmos_label(value: int) -> str:
    return scales.CMOS["choices"][value]

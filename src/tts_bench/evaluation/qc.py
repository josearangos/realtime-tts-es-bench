"""Quality control items: repeats, instructed-response attention checks, degraded anchors.

QC items carry exactly the same task-data keys as test items; everything that marks them lives in the mapping.
"""

from __future__ import annotations

import numpy as np

from . import scales
from .blind import IdGenerator, MappingRow
from .config import BatchConfig
from .sources import CorpusInfo
from .tasks import AUDIO_KEYS, Item, Stager, cmos_label, file_of, url

TONE_RATE = 16000


def n_qc(n_test: int, rate: float) -> int:
    if rate <= 0 or n_test == 0:
        return 0
    return max(1, round(n_test * rate))


def make_repeats(items: list[Item], cfg: BatchConfig, rng, ids: IdGenerator, stager: Stager) -> list[Item]:
    out = []
    for project in ("mos", "cmos", "sim"):
        pool = [i for i in items if i.project == project and i.row.role == "test"]
        k = n_qc(len(pool), cfg.repeat_rate)
        for src in rng.sample(pool, min(k, len(pool))):
            iid = ids.new()
            files = {f: stager.copy(f) for f in src.row.served_files}
            data = {"item_id": iid}
            for key, val in src.data.items():
                if key == "item_id":
                    continue
                data[key] = url(files[file_of(val)]) if key in AUDIO_KEYS else val
            row = MappingRow(**{**src.row.__dict__, "item_id": iid, "role": "repeat", "repeat_of": src.row.item_id,
                                "served_files": [files[f] for f in src.row.served_files]})
            if row.role == "attention_instructed":
                _synthetic(row)
            out.append(Item(row, data))
    return out


def _tone(rng, seconds: float = 1.5):
    t = np.arange(int(seconds * TONE_RATE)) / TONE_RATE
    return 0.3 * np.sin(2 * np.pi * rng.choice([262, 330, 392, 440, 523]) * t)


def degrade(samples: np.ndarray, rng) -> np.ndarray:
    """Mix white noise at 0 dB SNR (noise RMS equals signal RMS)."""
    nrng = np.random.default_rng(rng.randrange(2**32))
    rms = float(np.sqrt(np.mean(np.square(samples)))) or 1e-3
    return samples + nrng.standard_normal(samples.shape) * rms


SYNTHETIC = {"engine": "synthetic", "voice": "tone", "accent": "n/a", "cloned": False}


def _synthetic(row: MappingRow) -> MappingRow:
    """Instructed checks use generated tones: record that explicitly instead of leaving blanks."""
    row.sentence_id = "attention-check"
    if row.project == "cmos":
        row.a, row.b = dict(SYNTHETIC), dict(SYNTHETIC)
    else:
        row.engine, row.voice, row.accent, row.cloned = (SYNTHETIC[k] for k in ("engine", "voice", "accent", "cloned"))
    return row


def make_attention(items: list[Item], cfg: BatchConfig, rng, ids: IdGenerator, stager: Stager,
                   corpus: CorpusInfo) -> list[Item]:
    out = []
    for project in ("mos", "cmos", "sim"):
        pool = [i for i in items if i.project == project and i.row.role == "test"]
        total = n_qc(len(pool), cfg.attention_rate)
        n_deg = total // 2 if project != "sim" else 0
        for n in range(total):
            degraded = n < n_deg
            src = rng.choice(pool)
            iid = ids.new()
            if project == "mos" and degraded:
                x, rate = stager.read(src.row.served_files[0])
                f = stager.stage_samples(degrade(x, rng), rate)
                row = MappingRow(iid, "mos", role="attention_degraded", sentence_id=src.row.sentence_id,
                                 corpus_version=corpus.version, engine=src.row.engine, voice=src.row.voice,
                                 accent=src.row.accent, cloned=src.row.cloned, served_files=[f],
                                 expected={c: [1, 2] for c in scales.MOS_CRITERIA})
                data = {"item_id": iid, "audio": url(f), "text": src.data["text"]}
            elif project == "cmos" and degraded:
                x, rate = stager.read(src.row.served_files[0])
                clean, bad = stager.copy(src.row.served_files[0]), stager.stage_samples(degrade(x, rng), rate)
                degraded_is_b = rng.random() < 0.5
                fa, fb = (clean, bad) if degraded_is_b else (bad, clean)
                meta = {k: v for k, v in (src.row.a or {}).items() if k != "degraded"}
                row = MappingRow(iid, "cmos", role="attention_degraded", sentence_id=src.row.sentence_id,
                                 corpus_version=corpus.version, a={**meta, "degraded": not degraded_is_b},
                                 b={**meta, "degraded": degraded_is_b}, position="ab" if degraded_is_b else "ba",
                                 served_files=[fa, fb], expected={"cmos": [-3, -2] if degraded_is_b else [2, 3]})
                data = {"item_id": iid, "audio_a": url(fa), "audio_b": url(fb), "text": src.data["text"]}
            else:  # instructed response over a generated tone
                if project == "mos":
                    n_star = rng.randint(1, 5)
                    text = f"Control de atención: marque {n_star} estrellas en todas las preguntas."
                    expected = {c: [n_star] for c in scales.MOS_CRITERIA}
                    f = stager.stage_samples(_tone(rng), TONE_RATE)
                    row = MappingRow(iid, "mos", role="attention_instructed", corpus_version=corpus.version,
                                     served_files=[f], expected=expected)
                    data = {"item_id": iid, "audio": url(f), "text": text}
                elif project == "cmos":
                    value = rng.randint(-3, 3)
                    text = f"Control de atención: seleccione «{cmos_label(value)}»."
                    fa, fb = stager.stage_samples(_tone(rng), TONE_RATE), stager.stage_samples(_tone(rng), TONE_RATE)
                    row = MappingRow(iid, "cmos", role="attention_instructed", corpus_version=corpus.version,
                                     position="ab", served_files=[fa, fb], expected={"cmos": [value]})
                    data = {"item_id": iid, "audio_a": url(fa), "audio_b": url(fb), "text": text}
                else:
                    n_star = rng.randint(1, 5)
                    text = f"Control de atención: marque {n_star} estrellas."
                    fr, fa = stager.stage_samples(_tone(rng), TONE_RATE), stager.stage_samples(_tone(rng), TONE_RATE)
                    row = MappingRow(iid, "sim", role="attention_instructed", corpus_version=corpus.version,
                                     served_files=[fr, fa], expected={"sim": [n_star]})
                    data = {"item_id": iid, "reference": url(fr), "audio": url(fa), "text": text}
            if row.role == "attention_instructed":
                _synthetic(row)
            out.append(Item(row, data))
    return out

import json
from types import SimpleNamespace

import pytest

from tts_bench.evaluation import batch, config, fakes, sources
from tts_bench.evaluation.blind import read_mapping

TOML = """seed = {seed}
sentences_per_condition = {n}
repeat_rate = 0.10
attention_rate = 0.10
conditions = []
cmos_pairs = "all"
[quality_thresholds]
repeat_within_1_min = 0.7
max_failed_checks = 1
"""


def build(tmp_path, seed=11, n=6, name="out"):
    data = fakes.make_fake_dataset(tmp_path / "data")
    toml = tmp_path / f"batch-{seed}.toml"
    toml.write_text(TOML.format(seed=seed, n=n))
    cfg = config.load_config(toml)
    corpus = sources.load_corpus_info(data["corpus"])
    clips = sources.discover(data["output"], corpus, voices_dir=data["voices_dir"])
    out = tmp_path / name
    b = batch.prepare(cfg, clips, corpus, out)
    return SimpleNamespace(cfg=cfg, corpus=corpus, clips=clips, out=out, batch=b, data=data, toml=toml,
                           mapping=read_mapping(out / "private" / "mapping.jsonl"),
                           tasks=json.loads((out / "tasks.json").read_text()))


@pytest.fixture
def prepared(tmp_path):
    return build(tmp_path)


@pytest.fixture
def fake_ls():
    with fakes.FakeLabelStudio() as ls:
        yield ls

import hashlib

import numpy as np
import pytest

from tts_bench.evaluation import config, loudness, scales


def write(tmp_path, text):
    p = tmp_path / "batch.toml"
    p.write_text(text, encoding="utf-8")
    return p


BASE = 'seed = 1\nsentences_per_condition = 5\nrepeat_rate = 0.1\nattention_rate = 0.05\n'


def test_repo_batch_toml_loads():
    cfg = config.load_config()
    assert cfg.sentences_per_condition == 20 and cfg.repeat_rate == 0.10 and cfg.attention_rate == 0.05
    assert cfg.loudness_rms_dbfs == -23 and cfg.peak_limit_dbfs == -1 and cfg.cmos_pairs == "all"
    assert (cfg.repeat_within_1_min, cfg.max_failed_checks) == (0.7, 1)


def test_sha_of_file(tmp_path):
    p = write(tmp_path, BASE)
    assert config.load_config(p).sha256 == hashlib.sha256(p.read_bytes()).hexdigest()


@pytest.mark.parametrize("text", [
    BASE.replace("repeat_rate = 0.1", "repeat_rate = 0.5"),
    BASE.replace("attention_rate = 0.05", "attention_rate = 0.3"),
    BASE.replace("sentences_per_condition = 5", "sentences_per_condition = 0"),
    BASE.replace("seed = 1\n", ""),
    BASE + 'cmos_pairs = "some"\n',
    "not toml [",
])
def test_invalid_config(tmp_path, text):
    with pytest.raises(config.ConfigError):
        config.load_config(write(tmp_path, text))


def test_missing_file(tmp_path):
    with pytest.raises(config.ConfigError):
        config.load_config(tmp_path / "nope.toml")


def test_scale_hash_stable_and_sensitive(monkeypatch):
    h = scales.scale_hash()
    assert h == scales.scale_hash() and len(h) == 64
    monkeypatch.setitem(scales.MOS_CRITERIA["naturalidad"]["anchors"], 3, "otro texto")
    assert scales.scale_hash() != h


def tone(db_rms, n=16000):
    t = np.arange(n) / 16000
    x = np.sin(2 * np.pi * 220 * t)
    return x * 10 ** (db_rms / 20) / np.sqrt(0.5)


def test_loudness_hits_target_within_half_db():
    for src in (-40, -30, -15):
        y = loudness.normalize(tone(src))
        assert abs(loudness.rms_dbfs(y) - (-23)) <= 0.5
        assert loudness.peak_dbfs(y) <= -1 + 1e-6


def test_peak_limit_wins_for_peaky_signal():
    x = np.zeros(16000)
    x[100] = 0.9
    x[:50] = 0.001
    y = loudness.normalize(x)
    assert loudness.peak_dbfs(y) <= -1 + 1e-6


def test_silence_is_safe():
    y = loudness.normalize(np.zeros(100))
    assert not np.any(y) and not np.any(np.isnan(y))
    assert loudness.normalize(np.zeros(0)).size == 0


def test_wav_roundtrip_keeps_rate(tmp_path):
    p = tmp_path / "a.wav"
    loudness.write_wav(p, tone(-20), 24000)
    x, rate = loudness.read_wav(p)
    assert rate == 24000 and abs(loudness.rms_dbfs(x) - (-20)) < 0.2

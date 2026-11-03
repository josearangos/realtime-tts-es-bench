import numpy as np

from tts_bench.intelligibility.audio_check import inspect_wav, is_silent

from .conftest import silent_audio, tone_audio, write_wav


def test_zero_samples_silent(tmp_path):
    p = write_wav(tmp_path / "a.wav", np.zeros(0))
    r = inspect_wav(p)
    assert r["silent"] and r["duration_s"] == 0


def test_digital_silence(tmp_path):
    assert inspect_wav(write_wav(tmp_path / "a.wav", silent_audio()))["silent"]


def test_peak_below_threshold_silent(tmp_path):
    x = silent_audio()
    x[10] = 5e-5
    assert inspect_wav(write_wav(tmp_path / "a.wav", x))["silent"]


def test_peak_above_threshold_not_silent(tmp_path):
    x = silent_audio()
    x[10] = 2e-4
    assert not inspect_wav(write_wav(tmp_path / "a.wav", x))["silent"]


def test_tone_not_silent(tmp_path):
    r = inspect_wav(write_wav(tmp_path / "a.wav", tone_audio(0.5)))
    assert not r["silent"] and r["duration_s"] == 0.5 and r["sample_rate"] == 16000


def test_stereo(tmp_path):
    x = np.stack([silent_audio(), tone_audio()], axis=1)
    assert not inspect_wav(write_wav(tmp_path / "a.wav", x))["silent"]


def test_int16_is_scaled_before_threshold():
    assert is_silent(np.array([1, -2, 0], dtype=np.int16))       # 3/32768 < 1e-4
    assert not is_silent(np.array([0, 100], dtype=np.int16))
    assert is_silent(np.zeros(0, dtype=np.int16))

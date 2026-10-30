import pytest

from tts_bench.voices import audio_check as ac


def test_short_warns_long_does_not(wav_factory):
    assert "too_short" in ac.warnings(ac.analyze(wav_factory("s.wav", 6)))
    assert "too_short" not in ac.warnings(ac.analyze(wav_factory("l.wav", 12)))


def test_noisy_vs_clean(wav_factory):
    assert "noisy" in ac.warnings(ac.analyze(wav_factory("n.wav", 12, noise_db=-20)))
    assert "noisy" not in ac.warnings(ac.analyze(wav_factory("c.wav", 12, noise_db=-70)))


def test_non_16bit_rejected(wav_factory):
    with pytest.raises(ValueError, match="16-bit PCM"):
        ac.analyze(wav_factory("b.wav", 3, bits=8))


def test_write_segment_clamps(wav_factory, tmp_path):
    src = wav_factory("x.wav", 3)  # 6 s file
    ac.write_segment(src, tmp_path / "o.wav", 4.0, 100.0)
    a = ac.analyze(tmp_path / "o.wav")
    assert a["duration_s"] == pytest.approx(2.0, abs=0.01) and a["sample_rate"] == 24000

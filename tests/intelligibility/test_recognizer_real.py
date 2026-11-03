import pytest

from .conftest import tone_audio, write_wav

pytestmark = pytest.mark.engine


def test_recognizer_is_deterministic(tmp_path):
    pytest.importorskip("faster_whisper", reason="run in .venv-asr (pip install -e '.[asr]')")
    from tts_bench.intelligibility.recognizer import FasterWhisperRecognizer, RecognizerUnavailableError

    try:
        rec = FasterWhisperRecognizer()
    except RecognizerUnavailableError as exc:
        pytest.skip(str(exc))
    wav = write_wav(tmp_path / "a.wav", tone_audio(1.0))
    first, second = rec.transcribe(wav), rec.transcribe(wav)
    assert first == second                                   # no cache involved: runs twice
    s = rec.record().settings
    assert (s["language"], s["beam_size"], s["temperature"], s["vad_filter"],
            s["condition_on_previous_text"], s["initial_prompt"]) == ("es", 1, 0, False, False, None)
    assert (s["model"], s["device"], s["compute_type"]) == ("large-v3", "cpu", "int8")

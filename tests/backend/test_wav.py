import io
import struct
import wave

import numpy as np

from tts_bench.backend.wav import float_to_pcm16, pcm16_to_wav


def test_clipping_and_scaling():
    values = struct.unpack("<4h", float_to_pcm16(np.array([2.0, -3.0, 0.5, 0.0], dtype=np.float32)))
    assert values[0] == 32767 and values[1] == -32767 and values[3] == 0
    assert values[2] in (16383, 16384)


def test_wav_reads_back():
    pcm = float_to_pcm16(np.zeros(160, dtype=np.float32))
    with wave.open(io.BytesIO(pcm16_to_wav(pcm, 24000, 1))) as w:
        assert (w.getframerate(), w.getnchannels(), w.getnframes(), w.getsampwidth()) == (24000, 1, 160, 2)

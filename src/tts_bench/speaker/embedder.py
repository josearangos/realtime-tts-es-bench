"""Speaker embedders: the protocol, a fake for tests and the SpeechBrain ECAPA-TDNN model.

Only `SpeechBrainEmbedder` touches `speechbrain` / `torch`, and it imports them lazily.
"""

from __future__ import annotations

import hashlib
from typing import Protocol

import numpy as np

from ..core.errors import TTSBenchError
from .files import sha256_json
from .model import LIMITATION_NOTE, EmbedderRecord

ECAPA_SOURCE = "speechbrain/spkrec-ecapa-voxceleb"
ECAPA_REVISION = "0f99f2d0ebe89ac095bcc5903c4dd8f72b367286"  # Hugging Face commit, pinned 2026-11-03
INSTALL_HINT = "Install the speaker extra in its own environment: `pip install -e \".[speaker]\"` (.venv-spk)."


class EmbedderUnavailableError(TTSBenchError):
    """The embedding model, its library or its weights are missing."""


class Embedder(Protocol):
    def record(self) -> EmbedderRecord: ...

    def embed(self, samples: np.ndarray, sample_rate: int, keys: tuple[str, ...] = ()) -> np.ndarray: ...


def make_record(name: str, checkpoint: str, license: str, library_versions: dict, settings: dict,
                device: str = "cpu", training_data_note: str = "") -> EmbedderRecord:
    return EmbedderRecord(name, checkpoint, license, library_versions, settings, sha256_json(settings)[:16],
                          device, LIMITATION_NOTE, training_data_note)


class FakeEmbedder:
    """Deterministic embedder for tests, never for reported results.

    `scripted` maps a key (audio sha256, `<sentence_id>-r<N>` or `reference`) to a vector;
    any clip without a scripted key gets a vector derived from its dominant tone frequency,
    so clips with different tones give different vectors.
    """

    DIM = 16

    def __init__(self, scripted: dict | None = None) -> None:
        self.scripted = {k: np.asarray(v, dtype=np.float64) for k, v in (scripted or {}).items()}
        self.calls = 0

    def record(self) -> EmbedderRecord:
        settings = {"sample_rate": 16000, "channels": 1, "normalization": "none", "dimension": self.DIM}
        return make_record("fake-embedder", "fake", "n/a", {}, settings)

    def embed(self, samples: np.ndarray, sample_rate: int, keys: tuple[str, ...] = ()) -> np.ndarray:
        self.calls += 1
        for k in keys:
            if k in self.scripted:
                return self.scripted[k]
        x = np.asarray(samples, dtype=np.float64).reshape(-1)
        if x.size == 0:
            return np.zeros(self.DIM)
        spectrum = np.abs(np.fft.rfft(x))
        hz = float(np.argmax(spectrum)) * sample_rate / x.size
        k = np.arange(1, self.DIM // 2 + 1)
        angle = hz * k / 700.0
        return np.concatenate([np.cos(angle), np.sin(angle)])


class SpeechBrainEmbedder:
    """ECAPA-TDNN `speechbrain/spkrec-ecapa-voxceleb` (192-d), CPU, eval mode.

    Input is resampled to 16 kHz mono; peak is not normalized; the whole clip is embedded.
    """

    SAMPLE_RATE = 16000

    def __init__(self, device: str = "cpu", source: str = ECAPA_SOURCE, revision: str = ECAPA_REVISION) -> None:
        try:
            import torch
            import torchaudio
            import speechbrain
            try:
                from speechbrain.inference.speaker import EncoderClassifier
            except ImportError:  # older speechbrain
                from speechbrain.pretrained import EncoderClassifier
        except ImportError as exc:
            raise EmbedderUnavailableError(f"speechbrain/torch not installed ({exc}). {INSTALL_HINT}") from exc
        self._torch, self._torchaudio = torch, torchaudio
        self._versions = {"speechbrain": speechbrain.__version__, "torch": torch.__version__,
                          "torchaudio": torchaudio.__version__}
        self._source, self._revision, self._device = source, revision, device
        try:
            from huggingface_hub import snapshot_download

            local = snapshot_download(source, revision=revision)  # the exact pinned commit
            self._model = EncoderClassifier.from_hparams(
                source=local, run_opts={"device": device},
                savedir=f"output/speaker/.models/{source.replace('/', '_')}")  # git-ignored
        except Exception as exc:  # download or weights problems
            raise EmbedderUnavailableError(f"cannot load {source}: {exc}. {INSTALL_HINT}") from exc
        self._model.eval()

    def record(self) -> EmbedderRecord:
        settings = {"sample_rate": self.SAMPLE_RATE, "channels": 1, "normalization": "none", "dimension": 192}
        return make_record(
            "speechbrain-ecapa", f"{self._source}@{self._revision}",
            "Apache-2.0 (checkpoint card on Hugging Face); trained on VoxCeleb1+2, whose own terms "
            "were not verified for commercial use",
            self._versions, settings, self._device,
            "Trained on VoxCeleb (English-dominant celebrity interviews).")

    def embed(self, samples: np.ndarray, sample_rate: int, keys: tuple[str, ...] = ()) -> np.ndarray:
        torch = self._torch
        wav = torch.from_numpy(np.asarray(samples, dtype=np.float32).reshape(1, -1))
        if sample_rate != self.SAMPLE_RATE:
            wav = self._torchaudio.functional.resample(wav, sample_rate, self.SAMPLE_RATE)
        with torch.no_grad():
            emb = self._model.encode_batch(wav)
        return emb.squeeze().cpu().numpy().astype(np.float64)


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()

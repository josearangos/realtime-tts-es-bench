import builtins

import pytest

from tts_bench.adapters.fake import FakeAdapter
from tts_bench.adapters.phonon import PhononAdapter
from tts_bench.adapters.piper import PiperAdapter
from tts_bench.adapters.pocket_tts import PocketTTSAdapter
from tts_bench.core.errors import EngineNotInstalledError, WeightsMissingError


def _block_import(monkeypatch, name):
    real = builtins.__import__

    def fake(n, *a, **k):
        if n == name:
            raise ImportError(name)
        return real(n, *a, **k)

    monkeypatch.setattr(builtins, "__import__", fake)


def test_default_is_noop():
    FakeAdapter().check_ready()


@pytest.mark.parametrize("cls,mod", [(PhononAdapter, "ptts"), (PocketTTSAdapter, "pocket_tts"), (PiperAdapter, "piper")])
def test_missing_import(monkeypatch, cls, mod):
    _block_import(monkeypatch, mod)
    with pytest.raises(EngineNotInstalledError):
        cls().check_ready()


def test_phonon_missing_weights(monkeypatch, tmp_path):
    monkeypatch.setitem(__import__("sys").modules, "ptts", object())
    with pytest.raises(WeightsMissingError):
        PhononAdapter(model_dir=tmp_path / "absent").check_ready()
    PhononAdapter(model_dir=tmp_path).check_ready()


def test_pocket_cache_check(monkeypatch, tmp_path):
    monkeypatch.setitem(__import__("sys").modules, "pocket_tts", object())
    monkeypatch.setenv("HF_HUB_CACHE", str(tmp_path))
    with pytest.raises(WeightsMissingError):
        PocketTTSAdapter().check_ready()
    (tmp_path / "models--kyutai--pocket-tts").mkdir()
    PocketTTSAdapter().check_ready()

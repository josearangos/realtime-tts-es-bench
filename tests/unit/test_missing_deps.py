import sys

import pytest

import tts_bench  # noqa: F401
from tts_bench.core.errors import EngineNotInstalledError, WeightsMissingError
from tts_bench.core.registry import get_adapter


@pytest.mark.parametrize("name,mod", [("phonon", "ptts"), ("pocket_tts", "pocket_tts"), ("piper", "piper")])
def test_missing_library_gives_hint(name, mod, monkeypatch):
    monkeypatch.setitem(sys.modules, mod, None)  # makes `import mod` fail
    a = get_adapter(name)
    with pytest.raises(EngineNotInstalledError) as ei:
        a.load()
    assert "pip install" in str(ei.value)
    # other engines unaffected
    f = get_adapter("fake")
    f.load()
    f.close()


def test_missing_weights_gives_hint(tmp_path, monkeypatch):
    monkeypatch.setitem(sys.modules, "ptts", type(sys)("ptts"))
    a = get_adapter("phonon", model_dir=tmp_path / "absent")
    with pytest.raises(WeightsMissingError) as ei:
        a.load()
    assert "phonon-40m-es" in str(ei.value)

import pytest

from tts_bench.corpus import load_corpus
from tts_bench.intelligibility.normalize import _finish, _prepare, normalize, normalize_pair

SENTENCES = [s for sub in ("main", "cloning") for s in load_corpus(subset=sub).sentences]


@pytest.mark.parametrize("fold", [True, False])
@pytest.mark.parametrize("s", [s for s in SENTENCES if s.spoken], ids=lambda s: s.id)
def test_written_form_equals_spoken_form(s, fold):
    ref, hyp, _ = normalize_pair(s.spoken, s.text, fold_accents=fold)
    assert ref == hyp


@pytest.mark.parametrize("s", [s for s in SENTENCES if not s.spoken], ids=lambda s: s.id)
def test_sentences_without_spoken_only_use_basic_steps(s):
    # No numerals, currency, times or lexicon entries: only case, punctuation, accents, spaces.
    assert normalize(s.text) == _finish(_prepare(s.text), True)

from fractions import Fraction

import pytest

from tts_bench.intelligibility.align import align, char_error_rate, word_error_rate


def check(b, s, d, i, n):
    assert (b.substitutions, b.deletions, b.insertions, b.reference_length) == (s, d, i, n)
    assert b.rate == float(Fraction(s + d + i, n))


def test_identical():
    check(word_error_rate("el gato negro", "el gato negro"), 0, 0, 0, 3)


def test_one_substitution():
    check(word_error_rate("el gato negro", "el perro negro"), 1, 0, 0, 3)


def test_one_deletion():
    check(word_error_rate("el gato negro", "el negro"), 0, 1, 0, 3)


def test_one_insertion():
    check(word_error_rate("el gato", "el gato negro"), 0, 0, 1, 2)


def test_sub_plus_del():
    b = word_error_rate("el gato negro", "el perro")
    check(b, 1, 1, 0, 3)
    assert b.rate == float(Fraction(2, 3))


def test_hypothesis_empty():
    b = word_error_rate("uno dos tres", "")
    check(b, 0, 3, 0, 3)
    assert b.rate == 1.0


def test_empty_reference_rate_is_none():
    b = word_error_rate("", "algo")
    assert b.rate is None and b.insertions == 1


def test_wer_not_capped():
    b = word_error_rate("hola", "hola uno dos tres cuatro")
    check(b, 0, 0, 4, 1)
    assert b.rate == 4.0


def test_cer_casa_caza():
    check(char_error_rate("casa", "caza"), 1, 0, 0, 4)


def test_cer_counts_spaces():
    b = char_error_rate("a b", "ab")
    check(b, 0, 1, 0, 3)


def test_tie_break_deterministic():
    a = align("a b c".split(), "x c".split())
    b = align("a b c".split(), "x c".split())
    assert a.ops == b.ops
    # backtrace runs from the end, so the substitution is taken at the last tie
    assert [o["op"] for o in a.ops] == ["del", "sub", "match"]


def test_pooled_is_not_mean_of_rates():
    from tts_bench.intelligibility.align import ErrorBreakdown

    p = ErrorBreakdown.pooled([word_error_rate("a", "b"), word_error_rate("a b c d e f g h i j", "a b c d e f g h i j")])
    assert p.rate == pytest.approx(1 / 11)

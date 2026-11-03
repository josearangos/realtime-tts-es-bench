import numpy as np
import pytest

from tts_bench.speaker.similarity import ZeroNormError, cosine_similarity


def test_identical_vectors_score_one():
    v = [0.3, -0.2, 0.9]
    assert cosine_similarity(v, v) == 1.0


def test_orthogonal_vectors_score_zero():
    assert cosine_similarity([1, 0], [0, 1]) == 0.0


def test_opposite_vectors_score_minus_one():
    assert cosine_similarity([1, 2], [-1, -2]) == -1.0


def test_scaling_does_not_change_the_result():
    a, b = np.array([0.2, 0.5, -0.1]), np.array([0.4, 0.1, 0.3])
    assert cosine_similarity(a, b) == pytest.approx(cosine_similarity(10 * a, 0.3 * b))


def test_different_length_raises_value_error():
    with pytest.raises(ValueError):
        cosine_similarity([1, 2, 3], [1, 2])


def test_zero_vector_raises_zero_norm_error():
    with pytest.raises(ZeroNormError):
        cosine_similarity([0, 0], [1, 2])
    with pytest.raises(ZeroNormError):
        cosine_similarity([1, 2], [0, 0])


def test_same_call_twice_is_identical():
    a, b = [0.12, 0.7, -0.3], [0.5, 0.2, 0.1]
    assert cosine_similarity(a, b) == cosine_similarity(a, b)

import statistics

import pytest

from tts_bench.speaker.variation import coefficient_of_variation


def test_durations_give_the_hand_computed_cv():
    cv = coefficient_of_variation((1.0, 1.1, 0.9))
    expected = statistics.stdev((1.0, 1.1, 0.9)) / statistics.fmean((1.0, 1.1, 0.9))
    assert cv.status == "ok" and cv.reason is None
    assert cv.value == pytest.approx(0.1, rel=0.05)
    assert cv.value == pytest.approx(expected)


def test_identical_values_give_zero():
    assert coefficient_of_variation((2.0, 2.0, 2.0)).value == 0.0


def test_near_zero_mean_is_declined_never_a_number():
    cv = coefficient_of_variation((0.01, -0.02, 0.03))
    assert cv.status == "near_zero_mean" and cv.value is None and cv.reason == "near_zero_mean"


def test_guard_is_strictly_below_0_05():
    assert coefficient_of_variation((0.05, 0.05)).status == "ok"
    assert coefficient_of_variation((0.049, 0.049)).status == "near_zero_mean"


def test_fewer_than_two_values():
    assert coefficient_of_variation((1.0,)).status == "fewer_than_two"
    assert coefficient_of_variation(()).status == "fewer_than_two"
    assert coefficient_of_variation(()).value is None


def test_negative_mean_uses_absolute_mean():
    vals = (-0.8, -0.9, -1.0)
    cv = coefficient_of_variation(vals)
    assert cv.status == "ok"
    assert cv.value == pytest.approx(statistics.stdev(vals) / abs(statistics.fmean(vals)))
    assert coefficient_of_variation((-0.01, -0.02)).status == "near_zero_mean"

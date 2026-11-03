import pytest

from tts_bench.speaker.eer import equal_error_rate


def test_perfect_separation_gives_zero():
    r = equal_error_rate([0.9, 0.8, 0.85], [0.2, 0.1, 0.3])
    assert r.available and r.eer == 0.0 and not r.high_eer_warning


def test_identical_distributions_give_half():
    r = equal_error_rate([0.2, 0.8], [0.2, 0.8])
    assert r.eer == pytest.approx(0.5)


def test_hand_calculated_case():
    r = equal_error_rate([0.9, 0.8, 0.4], [0.6, 0.3, 0.2])
    # threshold 0.6: false accepts 1/3 (0.6), false rejects 1/3 (0.4)
    assert r.eer == pytest.approx(1 / 3, abs=1e-8)
    assert r.threshold == pytest.approx(0.6)
    assert (r.n_same, r.n_different) == (3, 3)
    assert r.separation == pytest.approx((0.9 + 0.8 + 0.4) / 3 - (0.6 + 0.3 + 0.2) / 3, abs=1e-8)


def test_interpolates_between_the_two_nearest_thresholds():
    # same [0.8, 0.5], different [0.7, 0.2]: at 0.5 FAR 1/2 FRR 0; at 0.7 FAR 1/2 FRR 1/2 (crossing exact)
    r = equal_error_rate([0.8, 0.5], [0.7, 0.2])
    assert r.eer == pytest.approx(0.5)
    # same [0.9, 0.3], different [0.6, 0.5]: FAR 1 -> 1/2 at 0.5? gap changes sign between thresholds
    r = equal_error_rate([0.9, 0.3], [0.6, 0.5])
    # t=0.5: FAR 1, FRR 1/2 (gap .5); t=0.6: FAR 1/2, FRR 1/2 (gap 0) -> eer 0.5 at 0.6
    assert r.eer == pytest.approx(0.5) and r.threshold == pytest.approx(0.6)
    r = equal_error_rate([0.9, 0.7, 0.3], [0.8, 0.2])
    # t=0.2 FAR1 FRR0; 0.3 FAR 1/2 FRR 0; 0.7 FAR 1/2 FRR 1/3 (gap 1/6); 0.8 FAR 1/2 FRR 2/3 (gap -1/6)
    # interpolation: alpha = (1/6)/(1/6+1/6) = 1/2, eer = 1/2 + 1/2*0 = 0.5, threshold 0.75
    assert r.eer == pytest.approx(0.5) and r.threshold == pytest.approx(0.75)


def test_ties_are_deterministic():
    same, diff = [0.5, 0.5, 0.7], [0.5, 0.4, 0.4]
    assert equal_error_rate(same, diff) == equal_error_rate(same, diff)


def test_fewer_than_two_pairs_is_not_available():
    for same, diff in (([0.9], [0.1, 0.2]), ([0.9, 0.8], [0.1]), ([], [])):
        r = equal_error_rate(same, diff)
        assert r.available is False and r.reason and r.eer is None and not r.gate_passed


def test_high_eer_warning_above_ten_percent_only():
    # 10 pairs of each kind with exactly one error each: EER = 0.10 exactly (no warning)
    same = [0.9] * 9 + [0.4]
    diff = [0.2] * 9 + [0.6]
    r = equal_error_rate(same, diff)
    assert r.eer == pytest.approx(0.10) and r.high_eer_warning is False
    r = equal_error_rate([0.9] * 8 + [0.4, 0.3], [0.2] * 8 + [0.6, 0.7])
    assert r.eer == pytest.approx(0.20) and r.high_eer_warning is True


def test_separation_and_gate():
    ok = equal_error_rate([0.7, 0.7], [0.5, 0.5])        # separation exactly 0.20, EER 0
    assert ok.separation == pytest.approx(0.20) and ok.gate_passed is True
    low = equal_error_rate([0.69, 0.69], [0.5, 0.5])     # 0.19
    assert low.gate_passed is False and low.eer == 0.0
    high_eer = equal_error_rate([0.9, 0.2], [0.6, 0.1])
    assert high_eer.gate_passed is False

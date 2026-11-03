import pytest

from tts_bench.speaker.model import ReferenceQuality
from tts_bench.speaker.pairs import NEEDS_OTHER_VOICE, build_pairs, compute_eer
from tts_bench.speaker.similarity import cosine_similarity

from .conftest import ENGINE, REFERENCE, fixed_embeddings

A_REF, B_REF = (1.0, 0.0, 0.0), (0.0, 1.0, 0.0)
B_QUALITY = ReferenceQuality("rec-b", 15.0, 12.0, 49.0, "es-CO", ())


def voice_a(**kw):
    return fixed_embeddings({"S1": (0.9, 0.1, 0), "S2": (0.8, 0.2, 0)}, reference=A_REF, reference_sha="ref-a", **kw)


def voice_b(**kw):
    return fixed_embeddings({"S1": (0.1, 0.9, 0), "S2": (0.2, 0.8, 0)}, reference=B_REF, reference_sha="ref-b",
                            reference_quality=B_QUALITY, **kw)


def test_same_and_different_pairs_for_two_voices():
    same, diff, text = build_pairs([voice_a(), voice_b()])
    expected_same = [cosine_similarity(A_REF, c) for c in [(0.9, 0.1, 0), (0.8, 0.2, 0)]] + \
                    [cosine_similarity(B_REF, c) for c in [(0.1, 0.9, 0), (0.2, 0.8, 0)]]
    assert same == pytest.approx(expected_same)
    # A vs B's reference and B's two clips (3) plus B vs A's reference and A's two clips (3)
    assert len(diff) == 6 and "Pooled across cloning engines" in text
    assert cosine_similarity(A_REF, B_REF) in diff


def test_one_voice_is_not_available_with_reason():
    r = compute_eer([voice_a()])
    assert r.available is False and r.reason == NEEDS_OTHER_VOICE and r.pair_construction


def test_extras_provide_different_speaker_material():
    r = compute_eer([voice_a(extras=[("emiliano", B_REF), ("otro", (0.0, 0.0, 1.0))])])
    assert r.available and r.n_different == 2 and r.n_same == 2


def test_pooling_across_engines_reports_one_record():
    a2 = fixed_embeddings({"S1": (0.95, 0.05, 0)}, reference=A_REF, reference_sha="ref-a2",
                          engine={**ENGINE, "name": "fake2"})
    r = compute_eer([voice_a(), a2, voice_b()])
    assert r.available and r.n_same == 5            # 2 + 1 + 2 clips pooled
    assert r.eer == 0.0 and r.gate_passed


def test_silent_or_failed_clips_never_form_pairs():
    a = fixed_embeddings({"S1": (0.9, 0.1, 0), "S2": None, "S3": None}, reference=A_REF, reference_sha="ref-a",
                         statuses={"S2": "failed", "S3": "silent"})
    same, diff, _ = build_pairs([a, voice_b()])
    assert len(same) == 3                            # A: S1 only; B: S1, S2
    assert len(diff) == 1 + 2 + 1 + 1                # A vs B ref + 2 B clips; B vs A ref + 1 A clip


def test_only_the_designated_repetition_forms_same_pairs():
    a = fixed_embeddings({("S1", 1): (0.9, 0.1, 0), ("S1", 2): (0.1, 0.9, 0)}, reference=A_REF, repetitions=2)
    same, _, _ = build_pairs([a])
    assert len(same) == 1


def test_an_extra_equal_to_a_pooled_files_reference_is_not_counted_twice():
    a = voice_a(extras=[("b", B_REF)])
    b = voice_b()
    object.__setattr__(a.extras[0], "audio_sha256", b.reference_sha256)
    _, diff, _ = build_pairs([a, b])
    assert len(diff) == 6          # A vs B ref + 2 clips, B vs A ref + 2 clips: 3 + 3, no duplicate

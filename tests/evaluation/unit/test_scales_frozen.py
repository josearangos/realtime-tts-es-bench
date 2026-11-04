from pathlib import Path

from tts_bench.evaluation import scales

GOLDEN = Path(__file__).parent / "fixtures" / "scale_hash.golden"


def test_scale_hash_matches_golden():
    assert scales.scale_hash() == GOLDEN.read_text().strip(), (
        "scales or anchors changed: this invalidates collected data. Start a new batch and update the golden file deliberately.")

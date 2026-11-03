"""Intelligibility metrics: WER and CER from a fixed recognizer (docs/intelligibility.md)."""

from .align import char_error_rate, word_error_rate
from .compare import compare_results
from .normalize import normalize, normalize_pair
from .scoring import score_transcripts

__all__ = [
    "char_error_rate", "compare_results", "normalize", "normalize_pair",
    "score_transcripts", "word_error_rate",
]

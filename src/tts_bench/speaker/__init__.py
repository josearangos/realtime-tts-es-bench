"""Speaker similarity and consistency metrics for cloned voices (feature 006)."""

from .eer import equal_error_rate
from .scoring import score_embeddings
from .similarity import cosine_similarity
from .variation import coefficient_of_variation

__all__ = ["cosine_similarity", "coefficient_of_variation", "equal_error_rate", "score_embeddings"]

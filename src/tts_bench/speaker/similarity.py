"""Cosine similarity of two speaker embeddings (pure, no I/O)."""

from __future__ import annotations

import numpy as np


class ZeroNormError(Exception):
    """A vector has zero norm: a failure flag for the caller, never a score."""


def cosine_similarity(a, b) -> float:
    """Cosine of the angle between two vectors, in [-1, 1]. Same length and non-zero norm required."""
    x = np.asarray(a, dtype=np.float64).reshape(-1)
    y = np.asarray(b, dtype=np.float64).reshape(-1)
    if x.shape != y.shape:
        raise ValueError(f"vectors must have the same length, got {x.size} and {y.size}")
    nx, ny = float(np.linalg.norm(x)), float(np.linalg.norm(y))
    if nx == 0.0 or ny == 0.0:
        raise ZeroNormError("an embedding has zero norm")
    # Rounded to 12 decimals: identical vectors give exactly 1.0 and results do not depend on
    # last-bit differences between machines.
    value = round(float(np.dot(x, y) / (nx * ny)), 12)
    return max(-1.0, min(1.0, value))

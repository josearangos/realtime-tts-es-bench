"""Acronym and unit lexicon (data and lookup).

Lookup is case-insensitive and applied identically to reference and transcript.
Adding an entry requires bumping LEXICON_VERSION.
"""

from __future__ import annotations

LEXICON_VERSION = "1"

LEXICON: dict[str, str] = {
    "pse": "pe ese e",
    "sms": "ese eme ese",
    "pqr": "pe cu erre",
    "tv": "te ve",
    "4g": "cuatro ge",
    "gb": "gigas",
    "nit": "nit",
    "iva": "iva",
}


def lookup(token: str) -> str | None:
    return LEXICON.get(token.lower())

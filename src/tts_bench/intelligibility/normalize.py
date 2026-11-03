"""Spanish text normalization, identical on reference and transcript (pure).

Steps, in order (docs/intelligibility.md): NFC, lowercase, expand written forms
(lexicon, currency, times, percent, ordinal day, numerals), remove punctuation and
symbols, fold accents (á é í ó ú ü, never ñ), collapse whitespace.
"""

from __future__ import annotations

import re
import unicodedata

from .align import word_error_rate
from .lexicon import LEXICON
from .numbers import cardinal_es, digits_es, expand_time, numeral_words

RULESET_VERSION = "1"
STEPS = [
    "unicode_nfc",
    "lowercase",
    "expand_lexicon",
    "expand_currency",
    "expand_times",
    "expand_percent",
    "expand_ordinal_day",
    "expand_numerals",
    "remove_punctuation",
    "fold_accents",
    "collapse_whitespace",
]

_MONTHS = ("enero|febrero|marzo|abril|mayo|junio|julio|agosto|septiembre|setiembre|"
           "octubre|noviembre|diciembre")
_NUM = r"\d+(?:[.,]\d{3})+(?:,\d+)?|\d+(?:,\d+)?"
_FOLD = str.maketrans("áéíóúü", "aeiouu")

_LEXICON_RE = re.compile(r"(?<![\w])(" + "|".join(sorted(map(re.escape, LEXICON), key=len, reverse=True)) + r")(?![\w])")
_CURRENCY_RE = re.compile(r"\$\s?(" + _NUM + ")")
_TIME_RE = re.compile(r"(?<![\w:])(\d{1,2}):(\d{2})(?![\w:])")
_PERCENT_RE = re.compile(r"(" + _NUM + r")\s?%")
_DAY_ONE_RE = re.compile(r"(?<![\w.,])1(?=\s+de\s+(?:" + _MONTHS + r")\b)")
_LETTER_DIGIT_RE = re.compile(r"(?<=[^\W\d_])(?=\d)")
_NUMERAL_SIMPLE_RE = re.compile(_NUM)


_GROUPED_RE = re.compile(r"\d{1,3}(?:[.,]\d{3})+")


def _is_ambiguous(token: str) -> bool:
    """A plain integer of two or more digits without a leading zero, or one written with
    groups of three ('305,872'), can be read as a cardinal or digit by digit. Leading zeros
    and decimals have a single reading."""
    if _GROUPED_RE.fullmatch(token):
        return True
    return token.isdigit() and len(token) >= 2 and token[0] != "0"


def _read(token: str, reading: str) -> str:
    plain = re.sub(r"[.,]", "", token) if _GROUPED_RE.fullmatch(token) else token
    if reading == "digits" or (plain.isdigit() and plain[0] == "0" and len(plain) > 1):
        return digits_es(plain) if plain.isdigit() else numeral_words(token)
    try:
        return numeral_words(token)
    except ValueError:  # beyond the supported range (e.g. a hallucinated digit string)
        return digits_es(plain) if plain.isdigit() else token


def _expand(text: str, readings: list[str] | None = None, sink: list[str] | None = None) -> str:
    """Written forms to words. `readings` picks cardinal/digits per ambiguous numeral in
    order (default cardinal); `sink` collects the ambiguous tokens found."""
    text = _LEXICON_RE.sub(lambda m: LEXICON[m.group(1)], text)
    text = _CURRENCY_RE.sub(lambda m: " " + numeral_words(m.group(1)) + " pesos ", text)
    text = _TIME_RE.sub(lambda m: " " + expand_time(int(m.group(1)), int(m.group(2))) + " ", text)
    text = _PERCENT_RE.sub(lambda m: " " + numeral_words(m.group(1)) + " por ciento ", text)
    text = _DAY_ONE_RE.sub("primero", text)
    text = _LETTER_DIGIT_RE.sub(" ", text)
    idx = [0]

    def numeral(m: re.Match) -> str:
        token = m.group(0)
        if not _is_ambiguous(token):
            return " " + _read(token, "cardinal") + " "
        i = idx[0]
        idx[0] += 1
        if sink is not None:
            sink.append(token)
        reading = readings[i] if readings is not None and i < len(readings) else "cardinal"
        return " " + _read(token, reading) + " "

    return _NUMERAL_SIMPLE_RE.sub(numeral, text)


def _finish(text: str, fold_accents: bool) -> str:
    out = []
    for ch in text:
        cat = unicodedata.category(ch)
        out.append(" " if cat[0] in "PS" else ch)
    text = "".join(out)
    if fold_accents:
        text = text.translate(_FOLD)
    return " ".join(text.split())


def _prepare(text: str) -> str:
    return unicodedata.normalize("NFC", text).lower()


def normalize(text: str, *, fold_accents: bool = True) -> str:
    """Normalize one text. Numerals are read as cardinals."""
    return _finish(_expand(_prepare(text)), fold_accents)


def normalize_pair(
    reference: str, transcript: str, *, fold_accents: bool = True
) -> tuple[str, str, list[str]]:
    """Normalize reference and transcript; return (reference, transcript, readings).

    The reference reads numerals as cardinals. For each ambiguous numeral token in the
    transcript (a plain integer of two or more digits, no leading zero) the reading
    (`cardinal` or `digits`) with the smaller word edit distance to the reference is
    chosen; ties go to `cardinal`. A wrong word differs under both readings, so this
    cannot hide a word error. `readings` has one entry per ambiguous token.
    """
    ref_n = normalize(reference, fold_accents=fold_accents)
    prepared = _prepare(transcript)
    found: list[str] = []
    _expand(prepared, None, found)
    readings = ["cardinal"] * len(found)

    def distance(rs: list[str]) -> int:
        return word_error_rate(ref_n, _finish(_expand(prepared, rs), fold_accents)).errors

    best = distance(readings)
    for i in range(len(readings)):
        trial = readings[:i] + ["digits"] + readings[i + 1:]
        d = distance(trial)
        if d < best:
            best, readings = d, trial
    return ref_n, _finish(_expand(prepared, readings), fold_accents), readings

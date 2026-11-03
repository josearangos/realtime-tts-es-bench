"""Spanish numerals as words (pure, no dependency).

Range 0 to 999 999 999. Covers cardinals, digit-by-digit reading, currency and times.
"""

from __future__ import annotations

import re

_UNITS = ["cero", "uno", "dos", "tres", "cuatro", "cinco", "seis", "siete", "ocho", "nueve",
          "diez", "once", "doce", "trece", "catorce", "quince", "dieciséis", "diecisiete",
          "dieciocho", "diecinueve", "veinte", "veintiuno", "veintidós", "veintitrés",
          "veinticuatro", "veinticinco", "veintiséis", "veintisiete", "veintiocho", "veintinueve"]
_TENS = {30: "treinta", 40: "cuarenta", 50: "cincuenta", 60: "sesenta", 70: "setenta",
         80: "ochenta", 90: "noventa"}
_HUNDREDS = {1: "ciento", 2: "doscientos", 3: "trescientos", 4: "cuatrocientos", 5: "quinientos",
             6: "seiscientos", 7: "setecientos", 8: "ochocientos", 9: "novecientos"}
_DIGITS = _UNITS[:10]


def _below_1000(n: int, *, apocope: bool = False) -> str:
    """0 < n < 1000. `apocope` turns a final 'uno' into 'un' (before 'mil' or 'millones')."""
    if n == 100:
        return "cien"
    parts: list[str] = []
    h, rest = divmod(n, 100)
    if h:
        parts.append(_HUNDREDS[h])
    if rest:
        if rest < 30:
            word = _UNITS[rest]
        else:
            t, u = divmod(rest, 10)
            word = _TENS[t * 10] + (f" y {_UNITS[u]}" if u else "")
        if apocope:
            if word.endswith("veintiuno"):
                word = word[: -len("veintiuno")] + "veintiún"
            elif word.endswith("uno"):
                word = word[:-3] + "un"
        parts.append(word)
    return " ".join(parts)


def cardinal_es(n: int) -> str:
    """Cardinal in words: 0 to 999 999 999 ('un millón', 'mil' without 'un' prefix)."""
    if n < 0 or n > 999_999_999:
        raise ValueError(f"cardinal_es supports 0..999999999, got {n}")
    if n == 0:
        return "cero"
    millions, rest = divmod(n, 1_000_000)
    thousands, units = divmod(rest, 1000)
    parts: list[str] = []
    if millions:
        parts.append("un millón" if millions == 1 else f"{_below_1000(millions, apocope=True)} millones")
    if thousands:
        parts.append("mil" if thousands == 1 else f"{_below_1000(thousands, apocope=True)} mil")
    if units:
        parts.append(_below_1000(units))
    return " ".join(parts)


def digits_es(s: str) -> str:
    """Digit by digit, leading zeros included: '0045' -> 'cero cero cuatro cinco'."""
    return " ".join(_DIGITS[int(c)] for c in s if c.isdigit())


def parse_numeral(token: str) -> tuple[int, str | None]:
    """'1.847.300' -> (1847300, None); '6,5' -> (6, '5'). '.' groups thousands, ',' is decimal, except groups of exactly three digits ('1,847,300', the recognizer's English style) which are thousands."""
    if re.fullmatch(r"\d{1,3}(?:[.,]\d{3})+", token):  # groups of three: thousands ('1,847,300' too)
        return int(re.sub(r"[.,]", "", token)), None
    whole, _, frac = token.partition(",")
    return int(whole.replace(".", "")), (frac or None)


def numeral_words(token: str) -> str:
    """Cardinal reading of a numeral token, with a decimal part read as 'coma' plus its digits."""
    n, frac = parse_numeral(token)
    out = cardinal_es(n)
    if frac is not None:
        out += " coma " + digits_es(frac)
    return out


def expand_currency(token: str) -> str:
    """'1.847.300' (after a '$') -> 'un millón ... trescientos pesos'."""
    return numeral_words(token) + " pesos"


def expand_time(hour: int, minute: int) -> str:
    """3:00 -> 'tres'; 4:30 -> 'cuatro y media'; 4:15 -> 'cuatro y quince'."""
    h = cardinal_es(hour)
    if minute == 0:
        return h
    if minute == 30:
        return f"{h} y media"
    return f"{h} y {cardinal_es(minute)}"

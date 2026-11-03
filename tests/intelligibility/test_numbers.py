import pytest

from tts_bench.intelligibility.normalize import normalize, normalize_pair
from tts_bench.intelligibility.numbers import cardinal_es, digits_es, expand_time


@pytest.mark.parametrize("n,words", [
    (0, "cero"), (1, "uno"), (15, "quince"), (21, "veintiuno"), (100, "cien"),
    (101, "ciento uno"), (123, "ciento veintitrés"), (999, "novecientos noventa y nueve"),
    (1000, "mil"), (2026, "dos mil veintiséis"), (21000, "veintiún mil"),
    (69900, "sesenta y nueve mil novecientos"), (230000, "doscientos treinta mil"),
    (1847300, "un millón ochocientos cuarenta y siete mil trescientos"), (1000000, "un millón"),
])
def test_cardinals(n, words):
    assert cardinal_es(n) == words


def test_currency():
    assert normalize("$1.847.300") == "un millon ochocientos cuarenta y siete mil trescientos pesos"
    assert normalize("$5.000") == "cinco mil pesos"


def test_separators():
    assert normalize("6,5") == "seis coma cinco"
    assert normalize("1.250.000") == "un millon doscientos cincuenta mil"


def test_digits_reading():
    assert digits_es("4821") == "cuatro ocho dos uno"
    assert normalize("0045") == "cero cero cuatro cinco"          # a leading zero forces digits
    ref, hyp, _ = normalize_pair("cero cero cuatro cinco, ocho ocho tres dos", "0045 8832")
    assert ref == hyp


def test_times():
    assert normalize("las 3:00 de la tarde") == "las tres de la tarde"
    assert normalize("a las 4:30") == "a las cuatro y media"
    assert expand_time(4, 15) == "cuatro y quince"


def test_day_one_is_primero_only_before_month():
    assert normalize("el 1 de diciembre") == "el primero de diciembre"
    assert normalize("marque 1 para") == "marque uno para"


def test_percent():
    assert normalize("20%") == "veinte por ciento"


def test_comma_thousands_from_the_recognizer():
    assert normalize("$1,847,300") == normalize("$1.847.300")
    assert normalize("$184,700") == "ciento ochenta y cuatro mil setecientos pesos"
    assert normalize("6,5") == "seis coma cinco"

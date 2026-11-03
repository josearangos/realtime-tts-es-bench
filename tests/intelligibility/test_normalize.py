from tts_bench.intelligibility.normalize import RULESET_VERSION, STEPS, normalize, normalize_pair


def test_case_and_punctuation_ignored():
    assert normalize("¿Hola, Mundo?!") == "hola mundo"


def test_accent_folding():
    assert normalize("está") == normalize("esta") == "esta"
    assert normalize("papá") == "papa"
    assert normalize("año") != normalize("ano")
    assert normalize("año") == "año"


def test_accent_sensitive():
    assert normalize("está", fold_accents=False) != normalize("esta", fold_accents=False)


def test_same_function_for_reference_and_transcript():
    t = "Pague $20.000 antes del 1 de mayo"
    assert normalize_pair(t, t)[0] == normalize_pair(t, t)[1] == normalize(t)


def test_version_and_steps():
    assert RULESET_VERSION == "1" and "expand_numerals" in STEPS


def test_lexicon():
    assert normalize("PSE") == normalize("pe ese e")
    assert normalize("SMS") == normalize("ese eme ese")
    assert normalize("PQR") == normalize("pe cu erre")
    assert normalize("TV") == normalize("te ve")
    assert normalize("4G") == "cuatro ge"
    assert normalize("20 GB") == "veinte gigas"
    assert normalize("NIT") == "nit" and normalize("IVA") == "iva"


def test_reading_selection_digits():
    ref, hyp, readings = normalize_pair("cuenta cuatro ocho dos uno", "cuenta 4821")
    assert ref == hyp and readings == ["digits"]


def test_reading_selection_cardinal():
    ref, hyp, readings = normalize_pair("cuatro mil ochocientos veintiuno", "4821")
    assert ref == hyp and readings == ["cardinal"]


def test_wrong_word_still_an_error_under_both_readings():
    from tts_bench.intelligibility.align import word_error_rate

    ref, hyp, _ = normalize_pair("cuenta cuatro ocho dos uno", "cuenta 4822")
    assert word_error_rate(ref, hyp).errors > 0
    ref, hyp, _ = normalize_pair("cuatro mil ochocientos veintiuno", "4822")
    assert word_error_rate(ref, hyp).errors > 0


def test_tie_goes_to_cardinal():
    _, _, readings = normalize_pair("algo distinto", "15")
    assert readings == ["cardinal"]


def test_grouped_number_is_formatting_not_an_error():
    ref, hyp, readings = normalize_pair("termina en tres cero cinco ocho siete dos", "termina en 305,872")
    assert ref == hyp and readings == ["digits"]


def test_huge_digit_string_does_not_crash():
    assert normalize("1" + "0" * 40).startswith("uno cero")

from pathlib import Path

from tts_bench.corpus.validate import jaccard, normalize, validate
from tests.corpus.conftest import mutate, read_jsonl, write_jsonl


def codes(report):
    return {i.code for i in report.errors}


def test_shipped_copy_is_clean(shipped_copy):
    assert validate(shipped_copy).errors == []


def test_duplicate_id(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[1].update(id=rows[0]["id"]))
    assert "duplicate_id" in codes(validate(shipped_copy))


def test_empty_text(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[0].update(text="  "))
    assert "empty_text" in codes(validate(shipped_copy))


def test_missing_field(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[0].pop("probes"))
    assert "malformed" in codes(validate(shipped_copy))


def test_unknown_enum(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[0].update(scenario="nope"))
    r = validate(shipped_copy)
    assert "malformed" in codes(r) and "unknown scenario" in str(r.errors[0])


def test_fewer_than_100(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows.__delitem__(slice(90, None)))
    assert "too_few" in codes(validate(shipped_copy))


def test_near_duplicate_is_warning_not_error(shipped_copy):
    def f(rows):
        rows[1]["text"] = rows[0]["text"] + " sí"
        rows[1]["spoken"] = rows[0].get("spoken")
        if rows[1]["spoken"] is None:
            del rows[1]["spoken"]
    mutate(shipped_copy, "sentences.jsonl", f)
    r = validate(shipped_copy)
    assert any(w.code == "near_duplicate" for w in r.warnings) or "duplicate_text" in codes(r)


def test_exact_duplicate_text(shipped_copy):
    def f(rows):
        rows[1]["text"] = rows[0]["text"]
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "duplicate_text" in codes(validate(shipped_copy))


def test_hash_mismatch_is_warning_in_0x(shipped_copy):
    import json
    v = shipped_copy / "VERSION.json"
    raw = json.loads(v.read_text(encoding="utf-8"))
    raw["version"] = "0.9.0"
    v.write_text(json.dumps(raw), encoding="utf-8")
    (shipped_copy / "CHANGELOG.md").write_text("## 0.9.0\n", encoding="utf-8")
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[0].update(reviewed=False, tags=rows[0]["tags"]))
    p = shipped_copy / "sentences.jsonl"
    p.write_text(p.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    r = validate(shipped_copy)
    assert any(w.code == "hash_mismatch" for w in r.warnings)
    assert "hash_mismatch" not in codes(r)


def test_hash_mismatch_is_error_from_1_0_0(shipped_copy):
    import json
    v = shipped_copy / "VERSION.json"
    raw = json.loads(v.read_text(encoding="utf-8"))
    raw["version"] = "1.0.0"
    v.write_text(json.dumps(raw), encoding="utf-8")
    (shipped_copy / "CHANGELOG.md").write_text("## 1.0.0\n", encoding="utf-8")
    s = shipped_copy / "sentences.jsonl"
    s.write_text(s.read_text(encoding="utf-8") + "\n", encoding="utf-8")
    assert "hash_mismatch" in codes(validate(shipped_copy))


def test_missing_changelog_heading(shipped_copy):
    (shipped_copy / "CHANGELOG.md").write_text("# Changelog\n\n## 9.9.9\n", encoding="utf-8")
    assert "changelog" in codes(validate(shipped_copy))


def test_campaign_below_25(shipped_copy):
    def f(rows):
        rows[:] = [r for r in rows if r["campaign"] != "collections"][:] + [r for r in rows if r["campaign"] == "collections"][:10]
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "campaign_below" in codes(validate(shipped_copy))


def test_scenario_below_2(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows.__setitem__(slice(None), [r for r in rows if r["scenario"] != "upgrade"]))
    assert "scenario_below" in codes(validate(shipped_copy))


def test_missing_disclosure(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows.__setitem__(slice(None), [r for r in rows if r["scenario"] != "disclosure"]))
    r = validate(shipped_copy)
    assert any("disclosure" in i.message for i in r.errors)


def test_banned_phrase_in_collections(shipped_copy):
    def f(rows):
        for r in rows:
            if r["campaign"] == "collections" and "spoken" not in r:
                r["text"] = "Si no paga le vamos a embargar la cuenta"
                return
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "banned_phrase" in codes(validate(shipped_copy))


def test_banned_phrase_only_checked_for_collections(shipped_copy):
    def f(rows):
        for r in rows:
            if r["campaign"] == "inbound" and "spoken" not in r:
                r["text"] = "Hay una demanda en este caso"
                return
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "banned_phrase" not in codes(validate(shipped_copy))


def test_tag_below_10(shipped_copy):
    def f(rows):
        for r in rows:
            if "hard_word" in r["tags"]:
                r["tags"].remove("hard_word")
                if r["probes"] == "hard_word":
                    r["probes"] = "regionalism"
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "tag_below" in codes(validate(shipped_copy))


def test_long_tag_on_short_text(shipped_copy):
    def f(rows):
        rows[0]["text"] = "Hola."
        rows[0].pop("spoken", None)
        rows[0]["tags"] = ["long"]
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "tag_long" in codes(validate(shipped_copy))


def test_missing_spoken(shipped_copy):
    def f(rows):
        for r in rows:
            if "spoken" in r:
                del r["spoken"]
                return
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "missing_spoken" in codes(validate(shipped_copy))


def test_spoken_with_digit(shipped_copy):
    def f(rows):
        for r in rows:
            if "spoken" in r:
                r["spoken"] += " 5"
                return
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "spoken_symbols" in codes(validate(shipped_copy))


def test_probe_requires_tag(shipped_copy):
    def f(rows):
        for r in rows:
            if r["probes"] == "fast_ack":
                r["tags"].remove("short")
                return
    mutate(shipped_copy, "sentences.jsonl", f)
    assert "probe_tag" in codes(validate(shipped_copy))


def test_unknown_regionalism_id(shipped_copy):
    p = shipped_copy / "REGIONALISMS.md"
    p.write_text(p.read_text(encoding="utf-8") + "\nVEN-999\n", encoding="utf-8")
    assert "regionalism_id" in codes(validate(shipped_copy))


def test_subset_mismatch(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[0].update(subset="cloning"))
    assert "subset_mismatch" in codes(validate(shipped_copy))


# ---- cloning subset and transcript overlap ----

def _transcript(tmp_path, body):
    p = tmp_path / "transcript.txt"
    p.write_text(body, encoding="utf-8")
    return p


def test_no_transcripts_reports_not_run(shipped_copy):
    r = validate(shipped_copy)
    assert r.overlap == "not run"


def test_unrelated_transcript_passes(shipped_copy, tmp_path):
    t = _transcript(tmp_path, "Ayer fui al mercado y compré frutas frescas para toda la semana.")
    r = validate(shipped_copy, transcripts=[t])
    assert r.overlap == "passed" and not r.errors


def test_exact_copy_fails(shipped_copy, tmp_path):
    clo = read_jsonl(shipped_copy / "cloning.jsonl")[1]
    t = _transcript(tmp_path, "Algo antes. " + clo["text"] + " Algo después.")
    r = validate(shipped_copy, transcripts=[t])
    assert r.overlap == "failed" and "cloning_overlap" in codes(r)


def test_near_copy_fails(shipped_copy, tmp_path):
    clo = read_jsonl(shipped_copy / "cloning.jsonl")[1]
    t = _transcript(tmp_path, clo["text"].replace(",", "") + " sí.")
    r = validate(shipped_copy, transcripts=[t])
    assert r.overlap == "failed"


def test_cloning_sentence_also_in_main_fails(shipped_copy):
    clo = read_jsonl(shipped_copy / "cloning.jsonl")[0]
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[0].update(text=clo["text"], tags=[], probes="regionalism"))
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[0].pop("spoken", None))
    assert "cloning_overlap" in codes(validate(shipped_copy))


def test_cloning_campaign_coverage(shipped_copy):
    mutate(shipped_copy, "cloning.jsonl", lambda rows: rows.__setitem__(slice(None), [r for r in rows if r["campaign"] != "inbound"]))
    assert "cloning_campaign_below" in codes(validate(shipped_copy))


# ---- release ----

def test_release_fails_when_unreviewed(shipped_copy):
    mutate(shipped_copy, "sentences.jsonl", lambda rows: rows[0].update(reviewed=False))
    assert "unreviewed" in codes(validate(shipped_copy, release=True))
    assert "unreviewed" not in codes(validate(shipped_copy))


def test_release_passes_when_all_reviewed(shipped_copy):
    for name in ("sentences.jsonl", "cloning.jsonl"):
        mutate(shipped_copy, name, lambda rows: [r.update(reviewed=True) for r in rows])
    assert "unreviewed" not in codes(validate(shipped_copy, release=True))


# ---- helpers ----

def test_normalize_keeps_accents_drops_punctuation():
    assert normalize("¡Hola,  Mundo! Ñandú.") == "hola mundo ñandú"


def test_jaccard():
    assert jaccard("a b c", "a b c") == 1.0
    assert jaccard("a b", "c d") == 0.0

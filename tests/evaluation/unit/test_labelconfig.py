import xml.etree.ElementTree as ET

import pytest

from tts_bench.evaluation import labelconfig, scales


@pytest.mark.parametrize("project", ["mos", "cmos", "sim"])
def test_well_formed(project):
    ET.fromstring(labelconfig.label_config(project))


def test_mos_three_ratings_and_spanish_questions():
    root = ET.fromstring(labelconfig.label_config("mos"))
    ratings = root.findall(".//Rating")
    assert [r.get("name") for r in ratings] == ["naturalidad", "pronunciacion", "prosodia"]
    assert all(r.get("maxRating") == "5" for r in ratings)
    xml = labelconfig.label_config("mos")
    for c in scales.MOS_CRITERIA.values():
        assert c["question"].replace("¿", "¿") in xml
        for a in c["anchors"].values():
            assert a in xml
    assert len(root.findall(".//Audio")) == 1


def test_cmos_seven_choices_and_two_audios():
    root = ET.fromstring(labelconfig.label_config("cmos"))
    assert [a.get("name") for a in root.findall(".//Audio")] == ["audio_a", "audio_b"]
    assert [c.get("alias") for c in root.findall(".//Choice")] == [str(v) for v in range(-3, 4)]


def test_sim_reference_and_rating():
    root = ET.fromstring(labelconfig.label_config("sim"))
    assert [a.get("name") for a in root.findall(".//Audio")] == ["reference", "audio"]
    assert len(root.findall(".//Rating")) == 1


@pytest.mark.parametrize("project", ["mos", "cmos", "sim"])
def test_no_engine_words_and_only_community_tags(project):
    xml = labelconfig.label_config(project).lower()
    for word in ("piper", "phonon", "pocket", "engine", "motor", "modelo"):
        assert word not in xml
    tags = {e.tag for e in ET.fromstring(xml.replace("$", "")).iter()}
    assert tags <= {"view", "header", "audio", "text", "rating", "choices", "choice"}

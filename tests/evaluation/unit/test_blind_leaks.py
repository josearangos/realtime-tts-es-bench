import re

from tts_bench.evaluation import loudness

ENGINE_WORDS = ("fakea", "fakeb", "fakec", "voz1", "voz2", "clon1", "piper", "phonon", "pocket")
WAV = re.compile(r"^[0-9a-f]{12}\.wav$")


def test_no_names_in_task_data(prepared):
    ids = {s for s in prepared.data["main_ids"] + prepared.data["cloning_ids"]}
    for rows in prepared.tasks.values():
        for data in rows:
            for key, value in data.items():
                low = str(value).lower()
                assert not any(w in low for w in ENGINE_WORDS), (key, value)
                if key == "text":
                    continue  # spoken sentence text is required; the id is checked below
                assert not any(s in str(value) for s in ids), (key, value)
                if key in ("audio", "audio_a", "audio_b", "reference"):
                    assert WAV.match(value.rsplit("/", 1)[1]), value
                if key == "item_id":
                    assert re.fullmatch(r"[0-9a-f]{12}", value)


def test_served_dir_has_only_opaque_names(prepared):
    files = list((prepared.out / "served").iterdir())
    assert files and all(WAV.match(f.name) for f in files)
    used = {f for r in prepared.mapping for f in r.served_files}
    assert used == {f.name for f in files}


def test_wav_has_no_metadata_chunks(prepared):
    for f in (prepared.out / "served").iterdir():
        raw = f.read_bytes()
        assert raw[:4] == b"RIFF" and set(re.findall(rb"[A-Za-z ]{4}(?=[\x00-\xff]{4})", raw[12:20])) <= {b"fmt ", b"data"}
        for word in ENGINE_WORDS:
            assert word.encode() not in raw
        loudness.read_wav(f)  # readable


def test_text_field_never_contains_sentence_id(prepared):
    for rows in prepared.tasks.values():
        for data in rows:
            assert not re.search(r"\b(VEN|COB|ENT|CLO)-\d{3}\b", data["text"])


def test_mapping_is_outside_served_and_tasks_json_is_visible_data_only(prepared):
    assert not any("mapping" in f.name for f in (prepared.out / "served").iterdir())
    text = (prepared.out / "tasks.json").read_text().lower()
    assert not any(w in text for w in ENGINE_WORDS)

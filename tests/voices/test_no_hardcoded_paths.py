from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "src" / "tts_bench"
# corpus/validate.py only reads speaker transcripts under cloned_voices/ for an overlap check; it never loads a voice.
# adapters/piper.py only mentions the folder in a download hint text.
ALLOWED = {"smoke.py", str(Path("corpus") / "validate.py"), str(Path("adapters") / "piper.py")}


def test_no_hardcoded_voice_paths():
    for p in SRC.rglob("*.py"):
        rel = p.relative_to(SRC)
        if rel.parts[0] == "voices" or str(rel) in ALLOWED:
            continue
        text = p.read_text()
        for needle in ("cloned_voices", ".safetensors", "voices.toml"):
            assert needle not in text, f"{rel}: {needle}"

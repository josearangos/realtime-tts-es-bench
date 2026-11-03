import socket

from tts_bench.intelligibility.__main__ import main


def test_whole_pipeline_works_without_network(tmp_path, monkeypatch):
    def no_sockets(*a, **k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", no_sockets)
    audio, res = tmp_path / "audio", tmp_path / "res"
    assert main(["synthesize", "fake", "--limit", "4", "--out", str(audio)]) == 0
    assert main(["transcribe", str(audio / "fake-default"), "--model", "fake", "--out", str(res)]) == 0
    t = next(res.glob("fake-transcripts-*.json"))
    assert main(["score", str(t), "--out", str(res)]) == 0
    r = next(p for p in res.glob("fake-*.json") if "transcripts" not in p.name)
    assert main(["compare", str(r)]) == 0
    assert main(["errors", str(r)]) == 0

import socket

from tts_bench.metrics.__main__ import main


def test_run_works_without_network(tmp_path, monkeypatch):
    def no_sockets(*a, **k):
        raise AssertionError("network access attempted")

    monkeypatch.setattr(socket, "socket", no_sockets)
    assert main(["run", "fake", "--mode", "warm", "--limit", "3", "--repetitions", "1", "--out", str(tmp_path)]) == 0
    assert len(list(tmp_path.glob("fake-warm-*.json"))) == 1

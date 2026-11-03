import ipaddress
import socket
import sys

import pytest

from tests.backend.conftest import request_body, ws_collect


@pytest.fixture
def no_remote(monkeypatch):
    attempts = []
    real_connect = socket.socket.connect

    def guarded(self, address, *a, **k):
        host = address[0] if isinstance(address, tuple) else address
        try:
            loop = ipaddress.ip_address(host).is_loopback
        except ValueError:
            loop = host == "localhost"
        if isinstance(address, tuple) and not loop:
            attempts.append(address)
            raise OSError("network access is blocked in this test")
        return real_connect(self, address, *a, **k)

    def create(address, *a, **k):
        attempts.append(address)
        raise OSError("blocked")

    monkeypatch.setattr(socket.socket, "connect", guarded)
    monkeypatch.setattr(socket, "create_connection", create)
    return attempts


def test_no_network_attempts(backend_factory, no_remote):
    b = backend_factory(chunk_interval_s=0.05, chunks=6)
    assert b.client.get("/v1/engines").status_code == 200
    ws_collect(b.client, request_body())
    ws_collect(b.client, request_body(), cancel_after=1)
    assert no_remote == []


def test_import_opens_no_clients(no_remote):
    for mod in [m for m in sys.modules if m.startswith("tts_bench.backend.app")]:
        del sys.modules[mod]
    import tts_bench.backend.app  # noqa: F401

    assert no_remote == []


def test_default_host_and_warning(monkeypatch, capsys):
    from tts_bench.backend import __main__ as cli
    from tts_bench.backend.config import BackendConfig

    assert BackendConfig().host == "127.0.0.1"
    import uvicorn

    called = {}
    monkeypatch.setattr(uvicorn, "run", lambda app, **kw: called.update(kw))
    assert cli.main(["serve", "--host", "0.0.0.0", "--port", "8123"]) == 0
    assert "no authentication" in capsys.readouterr().err
    assert called["host"] == "0.0.0.0"
    assert cli.main(["serve"]) == 0
    assert "no authentication" not in capsys.readouterr().err
    assert cli.main([]) == 1

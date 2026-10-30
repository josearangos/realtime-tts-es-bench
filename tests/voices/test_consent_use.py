import pytest

from tests.voices.conftest import register_fake
from tts_bench.core.errors import ConsentNotPermittedError
from tts_bench.voices import ConsentRecord


@pytest.fixture
def restricted(library, wav_factory):
    library.add_consent(ConsentRecord("bob", "2025", ["internal_benchmarking"], ["outbound_sales"]))
    rec = library.add_recording(wav_factory(), "bob", "es-CO")
    register_fake(library, rec)
    return library


def test_use_not_permitted(restricted):
    with pytest.raises(ConsentNotPermittedError, match="published_results"):
        restricted.resolve("v1", use="published_results")


def test_content_not_permitted(restricted):
    with pytest.raises(ConsentNotPermittedError, match="collections"):
        restricted.resolve("v1", content="collections")


def test_permitted_and_undeclared(restricted):
    assert restricted.resolve("v1", use="internal_benchmarking", content="outbound_sales")
    assert restricted.resolve("v1")


def test_invalid_vocabulary(restricted):
    with pytest.raises(ConsentNotPermittedError, match="publish_results"):
        restricted.resolve("v1", use="publish_results")

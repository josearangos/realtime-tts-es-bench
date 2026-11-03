"""score and compare need no network, no model and no heavy imports (FR-010)."""

import subprocess
import sys
import textwrap


def test_score_and_compare_import_no_model_and_no_network(tmp_path):
    code = textwrap.dedent("""
        import socket, sys
        def blocked(*a, **k):
            raise AssertionError("network access attempted")
        socket.socket = blocked
        socket.create_connection = blocked
        from tts_bench.corpus import load_corpus
        from tts_bench.speaker.scoring import score_embeddings
        from tts_bench.speaker.compare import compare_results
        from tts_bench.speaker.pairs import compute_eer
        from tts_bench.speaker.model import *
        from tts_bench.speaker.model import EmbeddingsFile
        import json
        sys.path.insert(0, %r)
        from tests.speaker.conftest import fixed_embeddings
        corpus = load_corpus(subset="cloning")
        emb = fixed_embeddings({s.id: (1, 0.1, 0) for s in corpus.sentences[:3]})
        compare_results([score_embeddings(emb, corpus, eer=compute_eer([emb]))])
        for heavy in ("speechbrain", "torch", "torchaudio"):
            assert heavy not in sys.modules, heavy
        print("ok")
    """ % str(__import__("pathlib").Path(__file__).resolve().parents[2]))
    out = subprocess.run([sys.executable, "-I", "-c", code], capture_output=True, text=True,
                         env={"PYTHONPATH": str(__import__("pathlib").Path(__file__).resolve().parents[2] / "src")})
    assert out.returncode == 0 and out.stdout.strip() == "ok", out.stderr

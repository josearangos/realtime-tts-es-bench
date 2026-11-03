"""CLI: python -m tts_bench.metrics {run,compare}."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from ..core.errors import TTSBenchError


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m tts_bench.metrics")
    sub = p.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("run", help="measure one engine in one mode")
    r.add_argument("engine")
    r.add_argument("--mode", choices=["cold", "warm"], required=True)
    r.add_argument("--voice")
    r.add_argument("--voices-dir", help="voice library root (default: the library default)")
    r.add_argument("--subset", choices=["main", "cloning"], default="main")
    r.add_argument("--repetitions", type=int, default=5)
    r.add_argument("--warmup", type=int, default=3)
    r.add_argument("--load-threshold", type=float, default=0.25)
    r.add_argument("--limit", type=int)
    r.add_argument("--out", default="results/perf")
    c = sub.add_parser("compare", help="merge results files into Markdown tables")
    c.add_argument("files", nargs="+")
    c.add_argument("--allow-mixed-hardware", action="store_true")
    c.add_argument("--out")
    return p


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(raw)
    except SystemExit as exc:
        return 1 if exc.code else 0
    if args.cmd == "run":
        return _run(args, raw)
    return _compare(args)


def _run(a: argparse.Namespace, raw: list[str]) -> int:
    import tts_bench.adapters  # noqa: F401  (registers engines)
    from ..core.registry import get_adapter
    from ..corpus import Corpus, load_corpus
    from ..voices.library import LocalVoiceLibrary
    from .results import write_results
    from .runner import run_benchmark

    if a.repetitions < 1 or a.warmup < 0 or (a.limit is not None and a.limit < 1):
        print("usage: --repetitions and --limit must be >= 1, --warmup >= 0", file=sys.stderr)
        return 1
    try:
        adapter = get_adapter(a.engine)
    except KeyError as exc:
        print(f"usage: {exc.args[0]}", file=sys.stderr)
        return 1
    corpus = load_corpus(subset=a.subset)
    if a.limit is not None:
        corpus = Corpus(corpus.version, corpus.content_hash, corpus.sentences[: a.limit])

    # The voice is resolved BEFORE timing; consent is enforced by the library.
    try:
        if a.voice is None:
            if a.engine != "fake" and adapter.descriptor.voice_kind != "fixed_voice":
                print("usage: --voice is required for this engine", file=sys.stderr)
                return 1
            from ..core.voices import VoiceReference

            voice, checksum = VoiceReference("default", adapter.descriptor.voice_kind, "default"), None
        else:
            lib = LocalVoiceLibrary(a.voices_dir) if a.voices_dir else LocalVoiceLibrary()
            voice = lib.resolve(a.voice, adapter.descriptor.voice_kind, engine=a.engine, use="internal_benchmarking")
            checksum = next((v["sha256"] for v in lib.public_index() if v["name"] == a.voice), None)
        info = {"name": voice.name, "kind": voice.kind, "checksum": checksum}
        config = {"subset": a.subset, "limit": a.limit}
        results = run_benchmark(
            adapter, corpus, voice, mode=a.mode, repetitions=a.repetitions, warmup=a.warmup,
            voice_info=info, config=config, argv=raw, load_threshold=a.load_threshold,
        )
    except TTSBenchError as exc:
        print(f"cannot run '{a.engine}': {exc}", file=sys.stderr)
        return 2
    path = write_results(results, a.out)
    s = results.summary
    print(path)
    print(f"engine={a.engine} mode={a.mode} ok={s['n_ok']}/{s['n_total']} reliable={s['reliable']}")
    rtf, ttfa = s["rtf"], s["ttfa_ms"]
    if rtf["p50"] is not None:
        print(f"RTF p50={rtf['p50']:.3f} p95={rtf['p95']:.3f}")
    print("TTFA p50={:.1f} ms p95={:.1f} ms".format(ttfa["p50"], ttfa["p95"]) if isinstance(ttfa, dict) else "TTFA not available")
    return 0


def _compare(a: argparse.Namespace) -> int:
    from .compare import CompareRefusedError, compare_results
    from .results import ResultsFileError

    try:
        table = compare_results([Path(f) for f in a.files], allow_mixed_hardware=a.allow_mixed_hardware)
    except CompareRefusedError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    except ResultsFileError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    if a.out:
        Path(a.out).write_text(table, encoding="utf-8")
    print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())

"""CLI: python -m tts_bench.intelligibility {synthesize,transcribe,score,compare,errors}."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..core.errors import TTSBenchError

DEFAULT_OUT_AUDIO = "output/intelligibility"
DEFAULT_OUT_RESULTS = "results/intelligibility"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m tts_bench.intelligibility")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("synthesize", help="one synthesis per main sentence for one engine")
    s.add_argument("engine")
    s.add_argument("--voice")
    s.add_argument("--voices-dir", help="voice library root (default: the library default)")
    s.add_argument("--limit", type=int)
    s.add_argument("--out", default=DEFAULT_OUT_AUDIO)
    t = sub.add_parser("transcribe", help="transcribe an audio directory with one fixed recognizer")
    t.add_argument("audio_dir")
    t.add_argument("--model", default="large-v3", help="large-v3 (default) or fake")
    t.add_argument("--script", help="JSON {sentence_id: text}; replaces the fake recognizer output")
    t.add_argument("--device", default="cpu")
    t.add_argument("--compute-type", default="int8")
    t.add_argument("--cache", help="transcript cache directory")
    t.add_argument("--out", default=DEFAULT_OUT_RESULTS)
    c = sub.add_parser("score", help="compute WER and CER from a transcripts file")
    c.add_argument("transcripts_file")
    c.add_argument("--out", default=DEFAULT_OUT_RESULTS)
    m = sub.add_parser("compare", help="merge results files into Markdown tables")
    m.add_argument("files", nargs="+")
    m.add_argument("--out")
    e = sub.add_parser("errors", help="per-sentence errors with the words involved")
    e.add_argument("results_file")
    e.add_argument("--sentence")
    e.add_argument("--tag")
    e.add_argument("--worst", type=int)
    return p


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(raw)
    except SystemExit as exc:
        return 1 if exc.code else 0
    handler = {"synthesize": _synthesize, "transcribe": _transcribe, "score": _score,
               "compare": _compare, "errors": _errors}[args.cmd]
    return handler(args, raw)


def _synthesize(a: argparse.Namespace, raw: list[str]) -> int:
    import tts_bench.adapters  # noqa: F401  (registers engines)
    from ..core.registry import get_adapter
    from ..core.voices import VoiceReference
    from ..corpus import load_corpus
    from ..voices.library import LocalVoiceLibrary
    from .files import sanitize_path, sanitized_command
    from .synth import synthesize_corpus

    if a.limit is not None and a.limit < 1:
        print("usage: --limit must be >= 1", file=sys.stderr)
        return 1
    try:
        adapter = get_adapter(a.engine)
    except KeyError as exc:
        print(f"usage: {exc.args[0]}", file=sys.stderr)
        return 1
    corpus = load_corpus(subset="main")
    try:
        # Voices are resolved through the library (consent enforced), never from raw paths.
        if a.voice is None:
            if a.engine != "fake" and adapter.descriptor.voice_kind != "fixed_voice":
                print("usage: --voice is required for this engine", file=sys.stderr)
                return 1
            voice, checksum = VoiceReference("default", adapter.descriptor.voice_kind, "default"), None
        else:
            lib = LocalVoiceLibrary(a.voices_dir) if a.voices_dir else LocalVoiceLibrary()
            voice = lib.resolve(a.voice, adapter.descriptor.voice_kind, engine=a.engine,
                                use="internal_benchmarking")
            checksum = next((v["sha256"] for v in lib.public_index() if v["name"] == a.voice), None)
        info = {"name": voice.name, "kind": voice.kind, "checksum": checksum}
        out_dir = Path(a.out) / f"{a.engine}-{voice.name}"
        manifest = synthesize_corpus(adapter, corpus, voice, out_dir, limit=a.limit, voice_info=info,
                                     command=sanitized_command("synthesize", ["synthesize", *raw[1:]]))
    except TTSBenchError as exc:
        print(f"cannot run '{a.engine}': {exc}", file=sys.stderr)
        return 2
    counts = {s: sum(1 for i in manifest.items if i.status == s) for s in ("ok", "failed", "silent")}
    print(sanitize_path(out_dir))
    print(f"engine={a.engine} ok={counts['ok']} failed={counts['failed']} silent={counts['silent']}")
    return 0


def _transcribe(a: argparse.Namespace, raw: list[str]) -> int:
    from ..corpus import load_corpus
    from .files import FileFormatError, read_manifest, sanitize_path, sanitized_command, utc_stamp, write_transcripts
    from .recognizer import FakeRecognizer, FasterWhisperRecognizer, RecognizerUnavailableError
    from .transcribe import transcribe_manifest

    try:
        manifest = read_manifest(a.audio_dir)
    except FileFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    if a.model == "fake":
        corpus = load_corpus(subset="main")
        scripted = {s.id: (s.spoken if s.spoken is not None else s.text) for s in corpus.sentences}
        if a.script:
            try:
                scripted.update(json.loads(Path(a.script).read_text(encoding="utf-8")))
            except (OSError, ValueError) as exc:
                print(f"error: cannot read --script: {exc}", file=sys.stderr)
                return 1
        recognizer = FakeRecognizer(scripted)
    else:
        try:
            recognizer = FasterWhisperRecognizer(a.model, a.device, a.compute_type)
        except RecognizerUnavailableError as exc:
            print(f"cannot run recognizer: {exc}", file=sys.stderr)
            return 2
    result = transcribe_manifest(manifest, a.audio_dir, recognizer, a.cache,
                                 command=sanitized_command("transcribe", ["transcribe", *raw[1:]]))
    path = Path(a.out) / f"{manifest.engine['name']}-transcripts-{utc_stamp()}.json"
    write_transcripts(result, path)
    print(sanitize_path(path))
    return 0


def _score(a: argparse.Namespace, raw: list[str]) -> int:
    from ..corpus import Corpus, load_corpus
    from .files import FileFormatError, environment_block, read_transcripts, sanitize_path, sanitized_command, utc_stamp, write_results
    from .scoring import score_transcripts

    try:
        transcripts = read_transcripts(a.transcripts_file)
    except FileFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    corpus = load_corpus(subset=transcripts.corpus.get("subset", "main"))
    if transcripts.corpus.get("corpus_hash") != corpus.content_hash:
        print("error: the transcripts were made against a different corpus (corpus_hash differs)",
              file=sys.stderr)
        return 1
    limit = transcripts.corpus.get("limit")
    if limit is not None:
        corpus = Corpus(corpus.version, corpus.content_hash, corpus.sentences[:limit])
    results = score_transcripts(transcripts, corpus, command=sanitized_command("score", ["score", *raw[1:]]),
                                environment=environment_block())
    path = Path(a.out) / f"{results.engine['name']}-{utc_stamp()}.json"
    write_results(results, path)
    o = results.overall
    print(sanitize_path(path))
    print(f"engine={results.engine['name']} WER={o.primary['word'].rate:.4f} "
          f"CER={o.primary['char'].rate:.4f} flagged={o.n_flagged}/{o.n_sentences} reliable={results.reliable}")
    return 0


def _compare(a: argparse.Namespace, raw: list[str]) -> int:
    from .compare import MixedResultsError, compare_results
    from .files import FileFormatError

    try:
        table = compare_results(_read_all(a.files))
    except (MixedResultsError, FileFormatError) as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    if a.out:
        Path(a.out).write_text(table, encoding="utf-8")
    print(table)
    return 0


def _read_all(files):
    from .files import read_results

    return [read_results(f) for f in files]


def _errors(a: argparse.Namespace, raw: list[str]) -> int:
    from .compare import error_report
    from .files import FileFormatError, read_results

    try:
        results = read_results(a.results_file)
    except FileFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    print(error_report(results, sentence=a.sentence, tag=a.tag, worst=a.worst))
    return 0


if __name__ == "__main__":
    sys.exit(main())

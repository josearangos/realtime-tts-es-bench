"""CLI: python -m tts_bench.speaker {synthesize,embed,score,compare}."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

from ..core.errors import TTSBenchError
from .model import NOTICE

DEFAULT_OUT_AUDIO = "output/speaker"
DEFAULT_OUT_RESULTS = "results/speaker"
CONTENT = "cloning_prompts"


def _parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(prog="python -m tts_bench.speaker")
    sub = p.add_subparsers(dest="cmd", required=True)
    s = sub.add_parser("synthesize", help="the cloning subset, N repetitions, for one cloning engine")
    s.add_argument("engine")
    s.add_argument("--voice")
    s.add_argument("--voices-dir", help="voice library root (default: the library default)")
    s.add_argument("--repetitions", type=int, default=5)
    s.add_argument("--limit", type=int)
    s.add_argument("--out", default=DEFAULT_OUT_AUDIO)
    e = sub.add_parser("embed", help="embed the reference and every clip with one fixed model")
    e.add_argument("audio_dir")
    e.add_argument("--model", default="ecapa", help="ecapa (default) or fake")
    e.add_argument("--script", help="JSON {audio sha256 or '<sentence_id>-r<N>' or 'reference': vector} for the fake model")
    e.add_argument("--device", default="cpu")
    e.add_argument("--voices-dir")
    e.add_argument("--reference", help="reference WAV to use instead of the voice library (tests and the fake engine)")
    e.add_argument("--extras-from", nargs="*", default=[], help="other voices' audio dirs (already embedded)")
    e.add_argument("--cache", help="embedding cache directory")
    e.add_argument("--out", default=DEFAULT_OUT_AUDIO)
    c = sub.add_parser("score", help="similarity, consistency and optional EER from an embeddings file")
    c.add_argument("embeddings_file")
    c.add_argument("--eer", action="store_true")
    c.add_argument("--eer-from", nargs="*", default=[], help="other embeddings files pooled into the EER")
    c.add_argument("--out", default=DEFAULT_OUT_RESULTS)
    m = sub.add_parser("compare", help="merge results files into Markdown tables")
    m.add_argument("files", nargs="+")
    m.add_argument("--out")
    return p


def main(argv: list[str] | None = None) -> int:
    raw = list(sys.argv[1:] if argv is None else argv)
    try:
        args = _parser().parse_args(raw)
    except SystemExit as exc:
        return 1 if exc.code else 0
    handler = {"synthesize": _synthesize, "embed": _embed, "score": _score, "compare": _compare}[args.cmd]
    return handler(args, raw)


def _synthesize(a: argparse.Namespace, raw: list[str]) -> int:
    import tts_bench.adapters  # noqa: F401  (registers engines)
    from ..core.registry import get_adapter
    from ..corpus import load_corpus
    from ..voices.library import LocalVoiceLibrary
    from .files import sanitize_path, sanitized_command
    from .reference import USE, resolve_reference
    from .synth import not_applicable_message, synthesize_cloning

    if a.repetitions < 1 or (a.limit is not None and a.limit < 1):
        print("usage: --repetitions and --limit must be >= 1", file=sys.stderr)
        return 1
    try:
        # The fake engine is cloning-capable here so the pipeline can be tested end to end.
        adapter = get_adapter(a.engine, **({"supports_cloning": True} if a.engine == "fake" else {}))
    except KeyError as exc:
        print(f"usage: {exc.args[0]}", file=sys.stderr)
        return 1
    if not adapter.descriptor.supports_cloning:
        print(not_applicable_message(a.engine))
        return 0
    if not a.voice and a.engine != "fake":
        print("usage: --voice is required (a cloned voice from the voice library)", file=sys.stderr)
        return 1
    corpus = load_corpus(subset="cloning")
    try:
        if not a.voice:  # fake engine only: a placeholder voice and no real reference
            from ..core.voices import VoiceReference
            from .model import ReferenceQuality

            voice = VoiceReference("default", "fixed_voice", "default")
            quality = ReferenceQuality("fake-reference", 0.0, 0.0, 0.0, "none", ("placeholder reference",))
            info = {"name": "default", "kind": "fixed_voice", "recording_id": quality.recording_id,
                    "accent_label": "none"}
        else:
            lib = LocalVoiceLibrary(a.voices_dir) if a.voices_dir else LocalVoiceLibrary()
            # Voices and their reference audio come only through the library (consent enforced).
            import tempfile
            with tempfile.TemporaryDirectory(prefix="speaker-ref-") as tmp:
                _, quality = resolve_reference(lib, a.voice, engine=a.engine, use=USE, content=CONTENT,
                                               work_dir=tmp)
            kind = None if a.engine == "fake" else adapter.descriptor.voice_kind
            voice = lib.resolve(a.voice, kind, engine=a.engine, use=USE, content=CONTENT)
            info = {"name": voice.name, "kind": voice.kind, "recording_id": quality.recording_id,
                    "accent_label": lib.show(a.voice)["accent_label"]}
        out_dir = Path(a.out) / f"{a.engine}-{voice.name}"
        manifest = synthesize_cloning(
            adapter, corpus, voice, out_dir, repetitions=a.repetitions, limit=a.limit, voice_info=info,
            reference_quality=quality, command=sanitized_command(["synthesize", *raw[1:]]))
    except TTSBenchError as exc:
        print(f"cannot run '{a.engine}': {exc}", file=sys.stderr)
        return 2
    counts = {s: sum(1 for i in manifest.items if i.status == s) for s in ("ok", "failed", "silent")}
    print(sanitize_path(out_dir))
    print(f"engine={a.engine} repetitions={a.repetitions} ok={counts['ok']} failed={counts['failed']} "
          f"silent={counts['silent']}")
    return 0


def _embed(a: argparse.Namespace, raw: list[str]) -> int:
    import tempfile

    from ..voices.library import LocalVoiceLibrary
    from .embed import embed_directory
    from .embedder import EmbedderUnavailableError, FakeEmbedder, SpeechBrainEmbedder
    from .files import FileFormatError, read_embeddings, read_manifest, sanitize_path, sanitized_command
    from .model import ExtraEmbedding
    from .reference import USE, resolve_reference

    try:
        manifest = read_manifest(a.audio_dir)
    except FileFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    extras = []
    for d in a.extras_from:
        try:
            other = read_embeddings(d)
        except FileFormatError as exc:
            print(f"error: --extras-from {sanitize_path(d)} needs an embedded directory: {exc}", file=sys.stderr)
            return 1
        extras.append(ExtraEmbedding(other.engine["voice"]["name"], "other_voice_reference",
                                     other.reference_sha256, other.reference_vector))
    if a.model == "fake":
        scripted = {}
        if a.script:
            try:
                scripted = json.loads(Path(a.script).read_text(encoding="utf-8"))
            except (OSError, ValueError) as exc:
                print(f"error: cannot read --script: {exc}", file=sys.stderr)
                return 1
        embedder = FakeEmbedder(scripted)
    else:
        try:
            embedder = SpeechBrainEmbedder(a.device)
        except EmbedderUnavailableError as exc:
            print(f"cannot run embedder: {exc}", file=sys.stderr)
            return 2
    try:
        with tempfile.TemporaryDirectory(prefix="speaker-ref-") as tmp:
            if a.reference:
                ref_wav = a.reference
            else:
                lib = LocalVoiceLibrary(a.voices_dir) if a.voices_dir else LocalVoiceLibrary()
                ref_wav, _ = resolve_reference(lib, manifest.engine["voice"]["name"],
                                               engine=manifest.engine["name"], use=USE, content=CONTENT,
                                               work_dir=tmp)
            result = embed_directory(a.audio_dir, embedder, reference_wav=ref_wav, cache_dir=a.cache,
                                     extras=tuple(extras), command=sanitized_command(["embed", *raw[1:]]))
    except TTSBenchError as exc:
        print(f"cannot embed: {exc}", file=sys.stderr)
        return 2
    print(sanitize_path(Path(a.audio_dir) / "embeddings.json"))
    print(f"embedder={result.embedder.name} clips={len(result.clips)} extras={len(result.extras)}")
    return 0


def _score(a: argparse.Namespace, raw: list[str]) -> int:
    from ..corpus import load_corpus
    from .files import (
        FileFormatError, environment_block, read_embeddings, sanitize_path, sanitized_command, utc_stamp,
        write_results,
    )
    from .pairs import compute_eer
    from .scoring import score_embeddings

    try:
        emb = read_embeddings(a.embeddings_file)
        others = [read_embeddings(f) for f in a.eer_from]
    except FileFormatError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    corpus = load_corpus(subset=emb.corpus.get("subset", "cloning"))
    if emb.corpus.get("corpus_hash") != corpus.content_hash:
        print("error: the embeddings were made against a different corpus (corpus_hash differs)", file=sys.stderr)
        return 1
    eer = compute_eer([emb, *others]) if (a.eer or others) else None
    results = score_embeddings(emb, corpus, command=sanitized_command(["score", *raw[1:]]),
                               environment=environment_block(), eer=eer)
    path = Path(a.out) / f"{results.engine['name']}-{utc_stamp()}.json"
    write_results(results, path)
    print(NOTICE)
    print(sanitize_path(path))
    s = results.summary
    if s.status == "not_applicable":
        print(f"engine={results.engine['name']} not applicable")
    else:
        m = (s.similarity or {}).get("mean")
        print(f"engine={results.engine['name']} similarity={'n/a' if m is None else f'{m:.4f}'} "
              f"scored={s.n_scored}/{s.n_sentences} flagged={s.n_flagged}")
        for w in s.warnings:
            print(f"warning: {w}")
    if eer is not None:
        print(f"eer={'n/a' if eer.eer is None else f'{eer.eer:.4f}'} gate_passed={eer.gate_passed}"
              + ("" if eer.available else f" ({eer.reason})"))
        if eer.high_eer_warning:
            print("warning: similarity scores should be interpreted cautiously (EER above 10%)")
    return 0


def _compare(a: argparse.Namespace, raw: list[str]) -> int:
    from .compare import MergeRefused, compare_results
    from .files import FileFormatError, read_results

    try:
        table = compare_results([read_results(f) for f in a.files])
    except MergeRefused as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    except FileFormatError as exc:
        print(f"refused: {exc}", file=sys.stderr)
        return 3
    if a.out:
        Path(a.out).write_text(table, encoding="utf-8")
    print(table)
    return 0


if __name__ == "__main__":
    sys.exit(main())

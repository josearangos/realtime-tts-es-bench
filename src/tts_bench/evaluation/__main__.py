"""python -m tts_bench.evaluation prepare|provision|inspect|annotator|purge-voice|export|quality

Exit codes: 0 ok, 2 usage/config error, 3 Label Studio unreachable/timeout, 4 scale-hash mismatch.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from . import batch as batch_mod
from . import provision as prov
from .config import ConfigError, default_config_path, load_config
from .lsclient import LSClient, LSError, LSUnreachable
from .sources import SourceError, discover, load_corpus_info


def _client(args) -> LSClient:
    if not args.token:
        raise prov.UsageError("missing API token (--token or LS_API_TOKEN)")
    return LSClient(args.url, args.token)


def _cmd_prepare(args) -> int:
    cfg_path = Path(args.config) if args.config else (Path("evaluation/batch.toml") if Path("evaluation/batch.toml").exists() else default_config_path())
    cfg = load_config(cfg_path)
    corpus = load_corpus_info(args.corpus)
    manifests = list(args.source_manifest or [])
    if os.environ.get("EVAL_SOURCE_MANIFEST"):
        manifests.append(os.environ["EVAL_SOURCE_MANIFEST"])
    clips = discover(args.output_root, corpus, manifests, voices_dir=args.voices_dir)
    if not clips:
        raise batch_mod.BatchError("no synthesized audio found under output/speaker or output/intelligibility; "
                                   "synthesize clips first or pass --source-manifest")
    b = batch_mod.prepare(cfg, clips, corpus, args.output, os.environ.get("LS_VERSION", "1.23.2"), args.new_batch)
    print(f"batch {b['batch_id']}: {b['counts']}")
    return 0


def _cmd_provision(args) -> int:
    report = prov.provision(_client(args), args.output, args.storage_path, args.wait)
    for k, v in report.items():
        print(f"{k}: created {v['created']}, skipped {v['skipped']}")
    return 0


def _cmd_inspect(args) -> int:
    print(json.dumps(prov.inspect(_client(args)), ensure_ascii=False, indent=1))
    return 0


def _cmd_annotator(args) -> int:
    email, password = prov.create_annotator(_client(args), args.id, reset=args.reset_password)
    print(f"annotator {args.id} created\nlogin: {email}\npassword: {password}\n(shown once; store it now)")
    return 0


def _cmd_purge(args) -> int:
    client = _client(args) if args.token else None
    rec = prov.purge_voice(client, args.output, args.voice)
    print(f"purged {args.voice}: {rec['items']} items, {rec['files']} files, {rec['ls_tasks']} Label Studio tasks")
    return 0


def _cmd_export(args) -> int:
    from . import export
    return export.run_export(_client(args), args)


def _cmd_quality(args) -> int:
    from . import export
    return export.run_quality(_client(args), args)


def build_parser() -> argparse.ArgumentParser:
    ap = argparse.ArgumentParser(prog="python -m tts_bench.evaluation")
    ap.add_argument("--url", default=os.environ.get("LS_URL", "http://127.0.0.1:8080"))
    ap.add_argument("--token", default=os.environ.get("LS_API_TOKEN"))
    ap.add_argument("--output", default="output/evaluation", help="evaluation data directory")
    sub = ap.add_subparsers(dest="command", required=True)
    p = sub.add_parser("prepare")
    p.add_argument("--config")
    p.add_argument("--corpus")
    p.add_argument("--output-root", default="output")
    p.add_argument("--voices-dir", default=None, help="voice library root (default: the repository library)")
    p.add_argument("--source-manifest", action="append")
    p.add_argument("--new-batch", action="store_true")
    p.set_defaults(fn=_cmd_prepare)
    p = sub.add_parser("provision")
    p.add_argument("--storage-path", default="/label-studio/files/served")
    p.add_argument("--wait", type=float, default=120.0)
    p.set_defaults(fn=_cmd_provision)
    sub.add_parser("inspect").set_defaults(fn=_cmd_inspect)
    p = sub.add_parser("annotator")
    p.add_argument("id")
    p.add_argument("--reset-password", action="store_true", help="issue a new password for an existing annotator")
    p.set_defaults(fn=_cmd_annotator)
    p = sub.add_parser("purge-voice")
    p.add_argument("voice")
    p.set_defaults(fn=_cmd_purge)
    for name, fn in (("export", _cmd_export), ("quality", _cmd_quality)):
        p = sub.add_parser(name)
        p.add_argument("--out", default="results/human")
        p.set_defaults(fn=fn)
    return ap


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.fn(args)
    except (ConfigError, SourceError, batch_mod.BatchError, prov.UsageError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    except LSUnreachable as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 3
    except batch_mod.ScaleMismatch as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 4
    except LSError as exc:
        print(f"error: Label Studio: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

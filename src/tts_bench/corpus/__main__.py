"""python -m tts_bench.corpus validate|stamp"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from .loader import CorpusError, default_corpus_dir
from .validate import stamp, validate


def _print_counts(counts: dict) -> None:
    print(f"main sentences: {counts['main']}   cloning sentences: {counts['cloning']}   reviewed: {counts['reviewed']}")
    for title in ("campaign", "scenario", "tag", "probe", "address", "cloning_campaign"):
        items = ", ".join(f"{k}={v}" for k, v in counts[title].items())
        print(f"{title}: {items}")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tts_bench.corpus")
    sub = parser.add_subparsers(dest="command", required=True)
    v = sub.add_parser("validate", help="check the corpus against the coverage and consistency rules")
    v.add_argument("--path", type=Path, default=None, help="corpus directory (default: repository corpus/)")
    v.add_argument("--transcripts", nargs="*", type=Path, default=None, help="reference transcripts to check cloning overlap")
    v.add_argument("--release", action="store_true", help="also fail if any sentence is not reviewed")
    s = sub.add_parser("stamp", help="recompute counts and content_sha256 in VERSION.json")
    s.add_argument("--path", type=Path, default=None)
    args = parser.parse_args(argv)
    directory = args.path or default_corpus_dir()

    if args.command == "stamp":
        try:
            raw = stamp(directory)
        except (CorpusError, OSError) as exc:
            print(f"error: {exc}", file=sys.stderr)
            return 1
        print(f"stamped {raw['version']}: {raw['counts']} sha256={raw['content_sha256']}")
        return 0

    report = validate(directory, transcripts=args.transcripts, release=args.release)
    _print_counts(report.counts)
    print(f"transcript overlap: {report.overlap}")
    for w in report.warnings:
        print(f"warning {w}")
    for e in report.errors:
        print(f"error {e}")
    print(f"{len(report.errors)} error(s), {len(report.warnings)} warning(s)")
    return 0 if report.ok else 1


if __name__ == "__main__":
    sys.exit(main())

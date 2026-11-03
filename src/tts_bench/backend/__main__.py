"""CLI: python -m tts_bench.backend serve [--host --port --config --voices-dir --log-text]"""

from __future__ import annotations

import argparse
import sys

LOOPBACK = {"127.0.0.1", "localhost", "::1"}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="python -m tts_bench.backend")
    sub = parser.add_subparsers(dest="command")
    serve = sub.add_parser("serve", help="start the real-time backend")
    serve.add_argument("--host")
    serve.add_argument("--port", type=int)
    serve.add_argument("--config")
    serve.add_argument("--voices-dir")
    serve.add_argument("--log-text", action="store_true")
    try:
        args = parser.parse_args(argv)
    except SystemExit as exc:
        return 1 if exc.code not in (0, None) else 0
    if args.command != "serve":
        parser.print_usage(sys.stderr)
        return 1
    try:
        import fastapi  # noqa: F401
        import uvicorn
    except ImportError:
        print("fastapi/uvicorn are not installed: pip install -e '.[backend]'", file=sys.stderr)
        return 2
    from .app import create_app
    from .config import BackendConfig

    config = BackendConfig.load(args.config)
    if args.host:
        config.host = args.host
    if args.port:
        config.port = args.port
    if args.voices_dir:
        config.voices_dir = args.voices_dir
    if args.log_text:
        config.log_text = True
    if config.host not in LOOPBACK:
        print("warning: the backend has no authentication; only expose it on trusted networks", file=sys.stderr)
    app = create_app(config)
    uvicorn.run(app, host=config.host, port=config.port, log_level="info")
    for sup in app.state.supervisors.values():
        sup.shutdown()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

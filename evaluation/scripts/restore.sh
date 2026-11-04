#!/usr/bin/env bash
# Restore a backup made by backup.sh. Refuses when data exists unless CONFIRM=RESTORE is set or typed.
# Test mode (no Docker): EVAL_VOLUME_DIR=<dir standing in for the volume>.
set -euo pipefail
FILE="${1:?usage: restore.sh <backup.tar.gz>}"
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="${EVAL_OUTPUT_DIR:-$ROOT/output/evaluation}"
VOLUME="${EVAL_VOLUME_NAME:-tts-bench-eval_ls-data}"
IMAGE="tts-bench-label-studio:${LS_VERSION:-1.23.2}"
HOST_MODE=0; [ -n "${EVAL_VOLUME_DIR:-}" ] && HOST_MODE=1
[ -f "$FILE" ] || { echo "error: $FILE not found" >&2; exit 1; }

TMP="$(mktemp -d)"; trap 'rm -rf "$TMP"' EXIT
gzip -t "$FILE" 2>/dev/null || { echo "error: $FILE is corrupted (gzip check failed); nothing was changed" >&2; exit 1; }
tar -xzf "$FILE" -C "$TMP" 2>/dev/null || { echo "error: $FILE cannot be extracted; nothing was changed" >&2; exit 1; }
[ -f "$TMP/MANIFEST.json" ] || { echo "error: MANIFEST.json missing in archive; nothing was changed" >&2; exit 1; }
python3 - "$TMP" <<'PY' || { echo "error: checksum mismatch in archive; nothing was changed" >&2; exit 1; }
import hashlib, json, os, sys
root = sys.argv[1]
m = json.load(open(os.path.join(root, "MANIFEST.json")))
for rel, want in m["members"].items():
    p = os.path.join(root, rel)
    if not os.path.isfile(p) or hashlib.sha256(open(p, "rb").read()).hexdigest() != want:
        sys.exit(1)
PY

has_data=0
[ -d "$OUT_DIR" ] && [ -n "$(ls -A "$OUT_DIR" 2>/dev/null)" ] && has_data=1
if [ "$HOST_MODE" = 1 ]; then
  [ -d "$EVAL_VOLUME_DIR" ] && [ -n "$(ls -A "$EVAL_VOLUME_DIR" 2>/dev/null)" ] && has_data=1
else
  if docker volume inspect "$VOLUME" >/dev/null 2>&1 && \
     [ -n "$(docker run --rm --user root --entrypoint ls -v "$VOLUME:/src:ro" "$IMAGE" -A /src 2>/dev/null)" ]; then has_data=1; fi
fi
if [ "$has_data" = 1 ] && [ "${CONFIRM:-}" != "RESTORE" ]; then
  if [ -t 0 ]; then
    read -r -p "Existing evaluation data will be REPLACED. Type RESTORE to continue: " a
    [ "$a" = "RESTORE" ] || { echo "aborted, nothing changed"; exit 1; }
  else
    echo "error: evaluation data already exists; rerun with CONFIRM=RESTORE to replace it" >&2; exit 1
  fi
fi

if [ "$HOST_MODE" = 0 ]; then
  ${COMPOSE:?COMPOSE must be set} stop label-studio >/dev/null 2>&1 || true
  docker volume create "$VOLUME" >/dev/null
  docker run --rm --user root --entrypoint sh -v "$VOLUME:/dst" -v "$TMP/ls-data:/src:ro" "$IMAGE" \
    -c 'find /dst -mindepth 1 -delete && cp -a /src/. /dst/'
else
  rm -rf "${EVAL_VOLUME_DIR:?}"/* "$EVAL_VOLUME_DIR"/.[!.]* 2>/dev/null || true
  mkdir -p "$EVAL_VOLUME_DIR" && cp -a "$TMP/ls-data/." "$EVAL_VOLUME_DIR/"
fi
rm -rf "$OUT_DIR"; mkdir -p "$OUT_DIR"
cp -a "$TMP/evaluation-output/." "$OUT_DIR/"
[ "$HOST_MODE" = 0 ] && $COMPOSE up -d --no-build --wait label-studio
echo "restore complete from $FILE"

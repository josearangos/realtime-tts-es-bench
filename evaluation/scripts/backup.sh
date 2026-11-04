#!/usr/bin/env bash
# Back up the Label Studio data volume and output/evaluation/ into backups/evaluation/<UTC>.tar.gz.
# Test mode (no Docker): EVAL_VOLUME_DIR=<dir standing in for the volume>.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
OUT_DIR="${EVAL_OUTPUT_DIR:-$ROOT/output/evaluation}"
BACKUP_DIR="${EVAL_BACKUP_DIR:-$ROOT/backups/evaluation}"
VOLUME="${EVAL_VOLUME_NAME:-tts-bench-eval_ls-data}"
IMAGE="tts-bench-label-studio:${LS_VERSION:-1.23.2}"
HOST_MODE=0; [ -n "${EVAL_VOLUME_DIR:-}" ] && HOST_MODE=1
TS="$(date -u +%Y%m%dT%H%M%SZ)"
[ -d "$OUT_DIR" ] || { echo "error: $OUT_DIR does not exist; nothing to back up" >&2; exit 1; }

STAGE="$(mktemp -d)"; trap 'rm -rf "$STAGE"' EXIT
mkdir -p "$STAGE/ls-data" "$STAGE/evaluation-output" "$BACKUP_DIR"

if [ "$HOST_MODE" = 0 ]; then
  echo "stopping Label Studio briefly for a consistent copy..."
  ${COMPOSE:?COMPOSE must be set} stop label-studio >/dev/null
  trap '${COMPOSE} start label-studio >/dev/null 2>&1 || true; rm -rf "$STAGE"' EXIT
  docker run --rm --user root --entrypoint cp -v "$VOLUME:/src:ro" -v "$STAGE/ls-data:/dst" "$IMAGE" -a /src/. /dst/
else
  cp -a "$EVAL_VOLUME_DIR/." "$STAGE/ls-data/"
fi
cp -a "$OUT_DIR/." "$STAGE/evaluation-output/"

python3 - "$STAGE" "${LS_VERSION:-1.23.2}" <<'PY'
import hashlib, json, os, sys
stage, ls_version = sys.argv[1], sys.argv[2]
members = {}
for top in ("ls-data", "evaluation-output"):
    for dp, _, fs in os.walk(os.path.join(stage, top)):
        for f in fs:
            p = os.path.join(dp, f)
            members[os.path.relpath(p, stage)] = hashlib.sha256(open(p, "rb").read()).hexdigest()
batch = os.path.join(stage, "evaluation-output", "batch.json")
batch_id = json.load(open(batch)).get("batch_id") if os.path.exists(batch) else None
json.dump({"batch_id": batch_id, "label_studio_version": ls_version, "members": members},
          open(os.path.join(stage, "MANIFEST.json"), "w"), indent=1, sort_keys=True)
PY
FILE="$BACKUP_DIR/$TS.tar.gz"
COPYFILE_DISABLE=1 tar -czf "$FILE" -C "$STAGE" .
echo "backup written: $FILE"

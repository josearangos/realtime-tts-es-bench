#!/usr/bin/env bash
# Upgrade guard: refuse to start when LS_VERSION differs from the version that created the data.
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${EVAL_ENV_FILE:-$ROOT/evaluation/.env}"
MARKER="${EVAL_VERSION_MARKER:-$ROOT/output/evaluation/ls-version}"
WANT="${LS_VERSION:-}"
if [ -z "$WANT" ] && [ -f "$ENV_FILE" ]; then
  WANT="$(grep -E '^LS_VERSION=' "$ENV_FILE" | tail -n1 | cut -d= -f2-)"
fi
WANT="${WANT:-1.23.2}"
mkdir -p "$(dirname "$MARKER")"
if [ -f "$MARKER" ]; then
  HAVE="$(tr -d '[:space:]' < "$MARKER")"
  if [ "$HAVE" != "$WANT" ] && [ "${EVAL_ALLOW_UPGRADE:-0}" != 1 ]; then
    echo "error: the data volume was created with Label Studio $HAVE but LS_VERSION is $WANT." >&2
    echo "Changing versions can migrate the database irreversibly. Make a backup first (make eval-backup)," >&2
    echo "then retry with EVAL_ALLOW_UPGRADE=1, or set LS_VERSION=$HAVE to keep the current version." >&2
    exit 1
  fi
fi
echo "$WANT" > "$MARKER"
exit 0

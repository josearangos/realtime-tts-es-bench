#!/usr/bin/env bash
# Preflight for every eval-* target. Prints actionable messages and exits non-zero on the first problem.
# Usage: preflight.sh [--no-runtime]   (--no-runtime skips the Docker checks, used by tests)
set -u
ROOT="$(cd "$(dirname "$0")/../.." && pwd)"
ENV_FILE="${EVAL_ENV_FILE:-$ROOT/evaluation/.env}"
CHECK_RUNTIME=1
[ "${1:-}" = "--no-runtime" ] && CHECK_RUNTIME=0

fail() { echo "error: $*" >&2; exit 1; }

if [ "$CHECK_RUNTIME" = 1 ]; then
  command -v docker >/dev/null 2>&1 || fail "docker is not installed. Install Docker (Desktop or Engine) with Compose v2."
  docker compose version >/dev/null 2>&1 || fail "Docker Compose v2 is missing ('docker compose version' fails). Update Docker."
  docker info >/dev/null 2>&1 || fail "the Docker daemon is not running. Start Docker and retry."
fi

[ -f "$ENV_FILE" ] || fail "evaluation/.env not found. Run: cp evaluation/.env.example evaluation/.env"

get() { grep -E "^$1=" "$ENV_FILE" | tail -n1 | cut -d= -f2- | sed -e 's/^["'"'"']//' -e 's/["'"'"']$//'; }
LS_BIND="$(get LS_BIND)"; LS_BIND="${LS_BIND:-127.0.0.1}"
LS_PORT="$(get LS_PORT)"; LS_PORT="${LS_PORT:-8080}"
PASS="$(get LS_ADMIN_PASSWORD)"; TOKEN="$(get LS_API_TOKEN)"

[ -n "$PASS" ] || fail "LS_ADMIN_PASSWORD is empty in evaluation/.env"
[ -n "$TOKEN" ] || fail "LS_API_TOKEN is empty in evaluation/.env"

case "$LS_BIND" in
  127.0.0.1|localhost|::1) ;;
  *)
    if [ "$PASS" = "change-me" ] || [ "$TOKEN" = "change-me-token" ]; then
      fail "LS_BIND=$LS_BIND exposes Label Studio beyond this machine but the password/token are still the placeholders. Change LS_ADMIN_PASSWORD and LS_API_TOKEN in evaluation/.env."
    fi
    echo "warning: Label Studio is exposed on $LS_BIND:$LS_PORT over plain HTTP. Use a trusted network or a TLS reverse proxy." >&2
    ;;
esac

# port busy? (skip when our own stack already owns it)
if [ "${EVAL_SKIP_PORT_CHECK:-0}" != 1 ]; then
  OWN=0
  if [ "$CHECK_RUNTIME" = 1 ] && docker ps --format '{{.Names}}' 2>/dev/null | grep -q '^tts-bench-eval-label-studio'; then OWN=1; fi
  if [ "$OWN" = 0 ]; then
    BUSY=0
    if command -v lsof >/dev/null 2>&1; then
      lsof -nP -iTCP:"$LS_PORT" -sTCP:LISTEN >/dev/null 2>&1 && BUSY=1
    elif command -v nc >/dev/null 2>&1; then
      nc -z 127.0.0.1 "$LS_PORT" >/dev/null 2>&1 && BUSY=1
    fi
    [ "$BUSY" = 0 ] || fail "port $LS_PORT is already in use. Free it or choose another one: LS_PORT=8081 (in evaluation/.env)."
  fi
fi

# volume permission problems (served dir must be readable by the container user)
SERVED="$ROOT/output/evaluation/served"
if [ -d "$SERVED" ] && [ ! -r "$SERVED" ]; then
  fail "$SERVED is not readable. Fix with: chmod -R u+rwX,go+rX output/evaluation"
fi
exit 0

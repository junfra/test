#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
ORACLE_CLI="${ORACLE_CLI:-/home/user01/project/oracle/.venv/bin/oracle-plus}"
HOST=""
PORT=""
ARGS=()

while (($#)); do
  case "$1" in
    --host)
      HOST="${2:-}"
      shift 2
      ;;
    --port)
      PORT="${2:-}"
      shift 2
      ;;
    --cwd)
      cd "${2:-$ROOT_DIR}"
      shift 2
      ;;
    --)
      shift
      ARGS=("$@")
      break
      ;;
    *)
      ARGS+=("$1")
      shift
      ;;
  esac
done

if [[ -z "$HOST" ]]; then
  echo "oracle-remote-host: --host is required" >&2
  exit 1
fi

if [[ -n "$PORT" ]]; then
  export ORACLE_REMOTE_HOST="${HOST}:${PORT}"
else
  export ORACLE_REMOTE_HOST="$HOST"
fi

exec "$ORACLE_CLI" "${ARGS[@]}"

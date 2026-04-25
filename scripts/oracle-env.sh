#!/usr/bin/env bash
set -euo pipefail

PORT="${1:-9473}"
HOST="${ORACLE_REMOTE_HOST_HOST:-127.0.0.1}"

export ORACLE_CLI="${ORACLE_CLI:-/home/user01/project/oracle/.venv/bin/oracle-plus}"
export ORACLE_REMOTE_HOST="${ORACLE_REMOTE_HOST:-${HOST}:${PORT}}"
export ORACLE_REMOTE_TOKEN="${ORACLE_REMOTE_TOKEN:-1234abcd}"

printf 'ORACLE_CLI=%s\n' "$ORACLE_CLI"
printf 'ORACLE_REMOTE_HOST=%s\n' "$ORACLE_REMOTE_HOST"
printf 'ORACLE_REMOTE_TOKEN=%s\n' "$ORACLE_REMOTE_TOKEN"

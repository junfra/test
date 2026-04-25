#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_FILE="$ROOT_DIR/live-SKILL.md"
OUTPUT_FILE="$ROOT_DIR/output/SKILL.md"

install_path=""
install_codex="0"

while (($#)); do
  case "$1" in
    --install-path)
      install_path="${2:-}"
      shift 2
      ;;
    --install-codex)
      install_codex="1"
      shift
      ;;
    *)
      shift
      ;;
  esac
done

mkdir -p "$ROOT_DIR/output"
cp "$SOURCE_FILE" "$OUTPUT_FILE"

if [[ -n "$install_path" ]]; then
  mkdir -p "$(dirname "$install_path")"
  cp "$SOURCE_FILE" "$install_path"
fi

if [[ "$install_codex" == "1" ]]; then
  CODEx_PATH="${HOME}/.codex/skills/oracle-browser/SKILL.md"
  mkdir -p "$(dirname "$CODEx_PATH")"
  cp "$SOURCE_FILE" "$CODEx_PATH"
fi

#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
DEST="${RESEARCH_AUTOPILOT_DIR:-$ROOT/.tools/research-autopilot}"
REPO="https://github.com/crabin/research-autopilot.git"

mkdir -p "$(dirname "$DEST")"

if [ -d "$DEST/.git" ]; then
  git -C "$DEST" fetch --prune origin
  git -C "$DEST" checkout main
  git -C "$DEST" reset --hard origin/main
else
  rm -rf "$DEST"
  git clone --depth 1 "$REPO" "$DEST"
fi

test -f "$DEST/SKILL.md"

printf 'RESEARCH_AUTOPILOT_READY=%s\n' "$DEST"
printf 'RESEARCH_AUTOPILOT_COMMIT=%s\n' "$(git -C "$DEST" rev-parse HEAD)"

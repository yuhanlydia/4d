#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
SOURCE_DIR="${RESEARCH_AUTOPILOT_SOURCE:-$ROOT/.tools/Research_Autopilot}"
SKILL_INSTALL_ROOT="${RESEARCH_AUTOPILOT_SKILL_ROOT:-$ROOT/.agents/skills}"
REPO="https://github.com/Yunbo-max/Research_Autopilot.git"

mkdir -p "$(dirname "$SOURCE_DIR")" "$SKILL_INSTALL_ROOT"

if [ -d "$SOURCE_DIR/.git" ]; then
  git -C "$SOURCE_DIR" fetch --prune origin
  git -C "$SOURCE_DIR" checkout main
  git -C "$SOURCE_DIR" reset --hard origin/main
else
  rm -rf "$SOURCE_DIR"
  git clone "$REPO" "$SOURCE_DIR"
fi

UPSTREAM_COMMIT="$(git -C "$SOURCE_DIR" rev-parse HEAD)"
SKILLS=(
  research-autopilot
  writing-top-tier-papers
  designing-pipeline-figures
  designing-experiment-figures
)

for skill_name in "${SKILLS[@]}"; do
  src="$SOURCE_DIR/skills/$skill_name"
  dst="$SKILL_INSTALL_ROOT/$skill_name"
  test -f "$src/SKILL.md"
  rm -rf "$dst"
  cp -R "$src" "$dst"
done

python3 "$SKILL_INSTALL_ROOT/research-autopilot/scripts/research_nodes.py" check

mkdir -p "$ROOT/.tools"
cat > "$ROOT/.tools/research-autopilot-version.txt" <<EOF
source=$REPO
branch=main
commit=$UPSTREAM_COMMIT
installed_root=$SKILL_INSTALL_ROOT
EOF

printf 'RESEARCH_AUTOPILOT_SOURCE=%s\n' "$SOURCE_DIR"
printf 'RESEARCH_AUTOPILOT_SKILL_ROOT=%s\n' "$SKILL_INSTALL_ROOT"
printf 'RESEARCH_AUTOPILOT_COMMIT=%s\n' "$UPSTREAM_COMMIT"
printf 'RESEARCH_AUTOPILOT_SKILL=%s\n' "$SKILL_INSTALL_ROOT/research-autopilot/SKILL.md"

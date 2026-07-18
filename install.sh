#!/usr/bin/env bash
# Compass one-shot install (Unix / Git Bash / WSL)
set -euo pipefail
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

echo "== Compass install =="
PY="$(command -v python3 || command -v python || true)"
if [[ -z "${PY}" ]]; then echo "Need Python 3.10+"; exit 1; fi

echo "-- pip editable compass-core + compass-mcp"
"$PY" -m pip install -e "packages/compass-core[dev,studio]"
"$PY" -m pip install -e "packages/compass-mcp" || true
"$PY" -m pip install "mcp>=1.0" || true
"$PY" -m pip install -r apps/studio/requirements.txt || true

SKILL_SRC="$ROOT/skill"
# Cursor project skills
DEST_PROJECT="$(cd "$ROOT/../.." 2>/dev/null && pwd)/.cursor/skills/compass"
# Also try relative from monorepo
if [[ -d "$(dirname "$ROOT")/../.cursor/skills" ]]; then
  DEST_PROJECT="$(cd "$ROOT/../.." && pwd)/.cursor/skills/compass"
fi
# User-level
DEST_USER="${HOME}/.cursor/skills/compass"

install_skill() {
  local dest="$1"
  mkdir -p "$(dirname "$dest")"
  rm -rf "$dest"
  cp -R "$SKILL_SRC" "$dest"
  echo "Skill installed -> $dest"
}

# Prefer workspace .cursor/skills if present
WS_SKILLS="d:/PycharmProjects/pythonProject/.cursor/skills/compass"
if [[ -d "d:/PycharmProjects/pythonProject/.cursor/skills" ]]; then
  install_skill "d:/PycharmProjects/pythonProject/.cursor/skills/compass"
elif [[ -d "$ROOT/../../.cursor/skills" ]]; then
  install_skill "$(cd "$ROOT/../.." && pwd)/.cursor/skills/compass"
else
  install_skill "$DEST_USER"
fi

echo
echo "Done. Try: python -m compass_core.cli --help"
echo "Set COMPASS_ROOT=$ROOT/content"

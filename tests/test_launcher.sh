#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! grep -q -- '--skill "$repo_root/src"' podguy; then
  echo "error: launcher should load the src skill directory so all repo skills are available" >&2
  exit 1
fi

if grep -q 'src/podguy-post-production/SKILL.md' podguy || grep -q 'src/podguy-clip-cutter/SKILL.md' podguy; then
  echo "error: launcher should not hard-code individual repo skills" >&2
  exit 1
fi

for skill in src/podguy-post-production/SKILL.md src/podguy-clip-cutter/SKILL.md; do
  if [[ ! -f "$skill" ]]; then
    echo "error: missing skill: $skill" >&2
    exit 1
  fi
done

echo "ok: launcher skill loading smoke test passed"

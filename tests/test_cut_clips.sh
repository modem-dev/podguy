#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "skipping: ffmpeg is required for clip cutting smoke test"
  exit 0
fi

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/podguy-cut-test.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

fixture="$TMP_DIR/source.mp4"
clips_file="$TMP_DIR/clips.md"
output_dir="$TMP_DIR/cuts"

DURATION_SECONDS=5 SIZE=320x180 RATE=10 scripts/make_test_fixture.sh "$fixture" >/dev/null

cat >"$clips_file" <<'EOF'
# Clip candidates

## Strong opening thought
- 00:00:01 - 00:00:03 — The guest gives a concise hook with a clean payoff.
EOF

uv run python scripts/cut_clips.py "$fixture" "$clips_file" "$output_dir" --limit 1

uv run python - "$output_dir" <<'PY'
import json
import sys
from pathlib import Path

output_dir = Path(sys.argv[1])
manifest_path = output_dir / "manifest.json"
assert manifest_path.is_file(), manifest_path
manifest = json.loads(manifest_path.read_text())
assert manifest["schema_version"] == 1
assert len(manifest["clips"]) == 1
clip = manifest["clips"][0]
assert clip["start_timecode"] == "00:00:01"
assert clip["end_timecode"] == "00:00:03"
output = Path(clip["output"])
assert output.is_file(), output
assert output.stat().st_size > 0
print("clip cut assertions passed")
PY

echo "ok: clip cutting smoke test passed"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

# Pure parsing coverage via --dry-run: no ffmpeg or real media required.

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/podguy-cut-parse-test.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

media="$TMP_DIR/source with spaces.mp4"
printf 'fake media bytes' >"$media"

# Markdown with mixed range separators, fractional seconds, and a duplicate.
cat >"$TMP_DIR/clips.md" <<'EOF'
# Clip candidates

## Arrow separator
- 00:00:01 --> 00:00:03 — arrow range

## Dash separator
- 00:01:12.5 - 00:02:03 — fractional start

## Word separator
- 00:03:00 to 00:03:30 — word range

## Duplicate of the arrow range
- 00:00:01 - 00:00:03 — should be deduped
EOF

uv run python scripts/cut_clips.py "$media" "$TMP_DIR/clips.md" "$TMP_DIR/md" --dry-run >/dev/null

cat >"$TMP_DIR/clips.json" <<'EOF'
{
  "clips": [
    { "title": "JSON clip", "start": "00:00:05", "end": "00:00:09" }
  ]
}
EOF

uv run python scripts/cut_clips.py "$media" "$TMP_DIR/clips.json" "$TMP_DIR/json" --dry-run >/dev/null

cat >"$TMP_DIR/clips.csv" <<'EOF'
title,start,end
CSV clip,00:00:10,00:00:14
EOF

uv run python scripts/cut_clips.py "$media" "$TMP_DIR/clips.csv" "$TMP_DIR/csv" --dry-run >/dev/null

uv run python - "$TMP_DIR" <<'PY'
import json
import sys
from pathlib import Path

tmp = Path(sys.argv[1])

md = json.loads((tmp / "md" / "manifest.json").read_text())
clips = md["clips"]
assert len(clips) == 3, f"expected 3 deduped markdown clips, got {len(clips)}"
starts = [clip["start"] for clip in clips]
assert starts == [1.0, 72.5, 180.0], starts
assert clips[1]["end"] == 123.0, clips[1]

js = json.loads((tmp / "json" / "manifest.json").read_text())
assert len(js["clips"]) == 1
assert js["clips"][0]["start"] == 5.0
assert js["clips"][0]["title"] == "JSON clip"

csv = json.loads((tmp / "csv" / "manifest.json").read_text())
assert len(csv["clips"]) == 1
assert csv["clips"][0]["start"] == 10.0
assert csv["clips"][0]["end"] == 14.0

# The dry-run command list must keep the spaced media path as one argument.
assert any("source with spaces.mp4" in part for part in md["clips"][0]["command"])

print("cut_clips parsing assertions passed")
PY

echo "ok: cut_clips parsing smoke test passed"

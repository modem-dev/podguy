#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/podguy-transcript-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT

if [[ $# -gt 1 ]]; then
  echo "usage: tests/test_transcribe_video.sh [fixture-media]" >&2
  exit 1
fi

fixture=${1:-$work_dir/podguy-fixture.mp4}
if [[ $# -eq 0 ]]; then
  scripts/make_test_fixture.sh "$fixture" >/dev/null
elif [[ ! -f "$fixture" ]]; then
  echo "error: fixture not found: $fixture" >&2
  exit 1
fi

out_dir="$work_dir/transcript"

uv run python scripts/transcribe_video.py "$fixture" "$out_dir" --backend mock >/dev/null

for file in summary.txt segments.json transcript.txt transcript.srt transcript.vtt; do
  if [[ ! -f "$out_dir/$file" ]]; then
    echo "error: missing output file: $file" >&2
    exit 1
  fi
done

uv run python - "$out_dir" <<'PY'
import json
import sys
from pathlib import Path

out_dir = Path(sys.argv[1])
summary = (out_dir / "summary.txt").read_text()
text = (out_dir / "transcript.txt").read_text()
vtt = (out_dir / "transcript.vtt").read_text()
srt = (out_dir / "transcript.srt").read_text()
data = json.loads((out_dir / "segments.json").read_text())

assert "Backend: mock" in summary
assert data["backend"] == "mock"
assert data["model"] == "mock"
assert len(data["segments"]) == 3
assert data["segments"][0]["text"] == "Mock transcript segment one."
assert "Mock transcript segment two." in text
assert vtt.startswith("WEBVTT\n")
assert "00:00:00,000 --> 00:00:04,500" in srt
print("transcript fixture assertions passed")
PY

echo "ok: transcript smoke test passed"

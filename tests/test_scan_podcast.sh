#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/podguy-scan-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT

if [[ $# -gt 1 ]]; then
  echo "usage: tests/test_scan_podcast.sh [fixture-video]" >&2
  exit 1
fi

fixture=${1:-$work_dir/podguy-fixture.mp4}
if [[ $# -eq 0 ]]; then
  scripts/make_test_fixture.sh "$fixture" >/dev/null
elif [[ ! -f "$fixture" ]]; then
  echo "error: fixture not found: $fixture" >&2
  exit 1
fi

out_dir="$work_dir/scan"

swift scripts/scan_podcast.swift "$fixture" "$out_dir" 0.5 >/dev/null

for file in summary.txt boundaries.csv interstitial_candidates.csv non_host_candidates.csv report.html; do
  if [[ ! -f "$out_dir/$file" ]]; then
    echo "error: missing output file: $file" >&2
    exit 1
  fi
done

thumb_count=$(find "$out_dir/thumbs" -type f | wc -l | tr -d ' ')
if [[ "$thumb_count" -lt 1 ]]; then
  echo "error: expected thumbnails to be generated" >&2
  exit 1
fi

python3 - "$out_dir/boundaries.csv" <<'PY'
import csv
import sys

boundaries_csv = sys.argv[1]
with open(boundaries_csv, newline="") as f:
    rows = list(csv.DictReader(f))

assert rows, "expected at least one boundary row"
for column in ["time_seconds", "timecode", "label", "thumb_path"]:
    assert column in rows[0], column

print("scan fixture assertions passed")
PY

# Degenerate inputs must fail with a clean error, not a Swift crash.

if swift scripts/scan_podcast.swift "$work_dir/does-not-exist.mp4" "$work_dir/scan-missing" 0.5 >/dev/null 2>"$work_dir/missing.err"; then
  echo "error: expected missing input to fail" >&2
  exit 1
fi
grep -q "error: input file not found" "$work_dir/missing.err"

if swift scripts/scan_podcast.swift "$fixture" "$work_dir/scan-interval" 0 >/dev/null 2>"$work_dir/interval.err"; then
  echo "error: expected zero interval to fail" >&2
  exit 1
fi
grep -q "error: sample interval must be greater than 0" "$work_dir/interval.err"

if command -v ffmpeg >/dev/null 2>&1; then
  audio_fixture="$work_dir/audio-only.wav"
  ffmpeg -hide_banner -loglevel error -y -f lavfi -i "sine=frequency=440:duration=3" "$audio_fixture"
  if swift scripts/scan_podcast.swift "$audio_fixture" "$work_dir/scan-audio" 0.5 >/dev/null 2>"$work_dir/audio.err"; then
    echo "error: expected audio-only input to fail cleanly" >&2
    exit 1
  fi
  grep -q "error:" "$work_dir/audio.err"
fi

echo "ok: scan smoke test passed"

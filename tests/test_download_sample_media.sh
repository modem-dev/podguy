#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/podguy-sample-download-test.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

scripts/download_sample_media.sh "$TMP_DIR/sample" --dry-run >/dev/null

for file in "$TMP_DIR/sample/ATTRIBUTION.md" "$TMP_DIR/sample/ffmpeg-command.txt"; do
  if [[ ! -f "$file" ]]; then
    echo "error: missing output file: $file" >&2
    exit 1
  fi
done

if [[ -f "$TMP_DIR/sample/cordkillers-572-excerpt.mp4" ]]; then
  echo "error: dry run should not create media" >&2
  exit 1
fi

grep -q "Cordkillers 572: Podcasting and Chill" "$TMP_DIR/sample/ATTRIBUTION.md"
grep -q "CC BY-SA 4.0" "$TMP_DIR/sample/ATTRIBUTION.md"
grep -q "00:08:00" "$TMP_DIR/sample/ATTRIBUTION.md"
grep -q "00:03:50" "$TMP_DIR/sample/ATTRIBUTION.md"
grep -q "ck_527_fe.mp4" "$TMP_DIR/sample/ffmpeg-command.txt"

echo "ok: sample media downloader dry-run smoke test passed"

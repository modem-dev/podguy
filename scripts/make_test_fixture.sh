#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
usage: scripts/make_test_fixture.sh [output-video]

Create a small synthetic video fixture for local smoke tests.

Defaults:
  output-video: dist/test-fixtures/podguy-scan-fixture.mp4

Environment overrides:
  DURATION_SECONDS  default: 4
  SIZE              default: 640x360
  RATE              default: 10

Example:
  scripts/make_test_fixture.sh /tmp/podguy-fixture.mp4
EOF
}

if [[ $# -gt 1 ]]; then
  usage
  exit 1
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "error: ffmpeg is required to create the synthetic test fixture" >&2
  exit 1
fi

output_video=${1:-dist/test-fixtures/podguy-scan-fixture.mp4}
duration_seconds=${DURATION_SECONDS:-4}
size=${SIZE:-640x360}
rate=${RATE:-10}

mkdir -p "$(dirname "$output_video")"

ffmpeg \
  -hide_banner \
  -loglevel error \
  -y \
  -f lavfi \
  -i "testsrc2=size=${size}:rate=${rate}:duration=${duration_seconds}" \
  -pix_fmt yuv420p \
  "$output_video"

ls -lh "$output_video"

#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

bash tests/test_transcribe_video.sh
bash tests/test_prepare_transcript_analysis.sh
bash tests/test_scan_podcast.sh
bash tests/test_cut_clips.sh
bash tests/test_download_sample_media.sh
bash tests/test_launcher.sh

#!/usr/bin/env bash
set -euo pipefail

usage() {
  cat <<'EOF'
usage: scripts/download_sample_media.sh [output-dir] [--dry-run]

Download and cut an open-license podcast video excerpt for local evaluation.

Default output:
  dist/test-fixtures/open-license/cordkillers-572/

The default sample is a 3m50s excerpt from Cordkillers 572: Podcasting and Chill.
It starts at 00:08:00 because that section includes a three-person podcast layout,
lower thirds, a Patreon bumper, and an outro/interstitial graphic.

Environment overrides:
  SAMPLE_SOURCE_URL   source MP4 URL
  SAMPLE_START        default: 00:08:00
  SAMPLE_DURATION     default: 00:03:50
  SAMPLE_BASENAME     default: cordkillers-572-excerpt
  SAMPLE_SCALE        default: scale=-2:720
  SAMPLE_CRF          default: 23

Examples:
  scripts/download_sample_media.sh
  scripts/download_sample_media.sh /tmp/podguy-sample
  SAMPLE_START=00:00:00 SAMPLE_DURATION=00:02:30 scripts/download_sample_media.sh
EOF
}

output_dir="dist/test-fixtures/open-license/cordkillers-572"
dry_run=0

for arg in "$@"; do
  case "$arg" in
    -h|--help)
      usage
      exit 0
      ;;
    --dry-run)
      dry_run=1
      ;;
    --*)
      echo "error: unknown option: $arg" >&2
      usage >&2
      exit 1
      ;;
    *)
      output_dir="$arg"
      ;;
  esac
done

source_url=${SAMPLE_SOURCE_URL:-https://archive.org/download/ck_527/ck_527_fe.mp4}
source_page="https://archive.org/details/ck_527"
title="Cordkillers 572: Podcasting and Chill"
creator="Cordkillers"
license_name="Creative Commons Attribution-ShareAlike 4.0 International (CC BY-SA 4.0)"
license_url="https://creativecommons.org/licenses/by-sa/4.0/"
source_file="ck_527_fe.mp4"
source_file_note="The FULL Speed Racer Experience: Ultimate (120 - The Fastest Car on Earth, Part 1)"
excerpt_start=${SAMPLE_START:-00:08:00}
excerpt_duration=${SAMPLE_DURATION:-00:03:50}
basename=${SAMPLE_BASENAME:-cordkillers-572-excerpt}
scale_filter=${SAMPLE_SCALE:-scale=-2:720}
crf=${SAMPLE_CRF:-23}

mkdir -p "$output_dir"
output_video="$output_dir/${basename}.mp4"
attribution_file="$output_dir/ATTRIBUTION.md"
command_file="$output_dir/ffmpeg-command.txt"

ffmpeg_command=(
  ffmpeg
  -hide_banner
  -loglevel error
  -y
  -ss "$excerpt_start"
  -i "$source_url"
  -t "$excerpt_duration"
  -vf "$scale_filter"
  -c:v libx264
  -preset veryfast
  -crf "$crf"
  -c:a aac
  -b:a 128k
  -movflags +faststart
  "$output_video"
)

cat >"$attribution_file" <<EOF
# Open-license sample media attribution

This directory contains a locally generated excerpt for podguy evaluation. The
media file is intentionally generated under \`dist/\`, which is gitignored, and
should not be committed to the repository.

## Source

- Title: ${title}
- Creator: ${creator}
- Source page: ${source_page}
- Source file: ${source_file}
- Source file note: ${source_file_note}
- Source URL: ${source_url}
- License: ${license_name}
- License URL: ${license_url}

## Excerpt

- Output file: ${output_video}
- Start: ${excerpt_start}
- Duration: ${excerpt_duration}
- Transform: excerpted and re-encoded to 720p for local testing

The default excerpt starts at 00:08:00 because it includes a useful mix of video
podcast elements for podguy testing: multiple camera/person layouts, lower-third
labels, chat/sidebar graphics, a Patreon bumper, and an outro/interstitial card.

## Attribution note

Cordkillers 572: Podcasting and Chill by Cordkillers is licensed under CC BY-SA
4.0. This excerpt is a transformed sample for local software testing. If you
redistribute the generated excerpt, preserve this attribution and comply with the
share-alike license terms.
EOF

printf '%q ' "${ffmpeg_command[@]}" >"$command_file"
printf '\n' >>"$command_file"

if [[ "$dry_run" -eq 1 ]]; then
  echo "dry run: wrote attribution and command files to $output_dir"
  echo "dry run: would write video to $output_video"
  printf '%q ' "${ffmpeg_command[@]}"
  printf '\n'
  exit 0
fi

if ! command -v ffmpeg >/dev/null 2>&1; then
  echo "error: ffmpeg is required to download and cut sample media" >&2
  exit 1
fi

"${ffmpeg_command[@]}"

if command -v ffprobe >/dev/null 2>&1; then
  ffprobe -v error -show_entries format=duration,size -of default=noprint_wrappers=1 "$output_video"
else
  ls -lh "$output_video"
fi

echo "wrote sample video: $output_video"
echo "wrote attribution: $attribution_file"

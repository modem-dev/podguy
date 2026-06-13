#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT_DIR"

TMP_DIR="$(mktemp -d "${TMPDIR:-/tmp}/podguy-youtube-test.XXXXXX")"
trap 'rm -rf "$TMP_DIR"' EXIT

# Help should work without google API dependencies installed.
uv run python scripts/youtube_publish.py --help >/dev/null
uv run python scripts/youtube_publish.py upload --help >/dev/null

# Build a fake media file, description, chapters, and profile for a dry run.
media="$TMP_DIR/episode.bin"
printf 'fake video bytes' >"$media"

cat >"$TMP_DIR/description.md" <<'EOF'
A great episode about markets.
EOF

cat >"$TMP_DIR/chapters.md" <<'EOF'
00:00 Intro
12:14 Why this market flipped
EOF

cat >"$TMP_DIR/profile.toml" <<'EOF'
show_name = "Test Show"

[youtube]
default_privacy = "unlisted"
default_category = "28"
default_tags = ["podcast", "markets"]
description_footer = "Subscribe for more. #podcast" # trailing comment
EOF

uv run python scripts/youtube_publish.py upload "$media" \
  --title "Test Episode" \
  --description-file "$TMP_DIR/description.md" \
  --chapters-file "$TMP_DIR/chapters.md" \
  --profile "$TMP_DIR/profile.toml" \
  --dry-run >"$TMP_DIR/dry-run.json"

uv run python - "$TMP_DIR/dry-run.json" <<'PY'
import json
import sys
from pathlib import Path

payload = json.loads(Path(sys.argv[1]).read_text())
body = payload["body"]
assert body["snippet"]["title"] == "Test Episode"
assert body["snippet"]["categoryId"] == "28"
assert body["snippet"]["tags"] == ["podcast", "markets"]
assert body["status"]["privacyStatus"] == "unlisted"
assert body["status"]["selfDeclaredMadeForKids"] is False
description = body["snippet"]["description"]
assert "A great episode about markets." in description
assert "Chapters:\n00:00 Intro" in description
# Hashtag in a quoted footer must survive the TOML fallback parser's
# comment stripping, while the real trailing comment is removed.
assert description.endswith("Subscribe for more. #podcast"), description
print("youtube publish dry-run assertions passed")
PY

# publish-at validation: bad format and non-private privacy must fail.
if uv run python scripts/youtube_publish.py upload "$media" \
  --title "Bad" --publish-at "tomorrow" --dry-run >/dev/null 2>&1; then
  echo "expected invalid --publish-at to fail" >&2
  exit 1
fi

if uv run python scripts/youtube_publish.py upload "$media" \
  --title "Bad" --privacy public --publish-at "2026-06-20T16:00:00Z" \
  --profile "$TMP_DIR/profile.toml" --dry-run >/dev/null 2>&1; then
  echo "expected --publish-at with public privacy to fail" >&2
  exit 1
fi

echo "ok: youtube publish smoke test passed"

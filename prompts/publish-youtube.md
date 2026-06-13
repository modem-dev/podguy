---
description: Upload an episode video to YouTube with metadata drafted from analysis artifacts
---

Publish to YouTube: $@

Workflow:

1. Identify the episode slug and the final episode video file (a real export, not a review cut).
2. Check auth: if `~/.config/podguy/youtube/token.json` is missing, walk through the one-time setup in the `podguy-youtube-publisher` skill before anything else.
3. Draft metadata from existing artifacts and the `[youtube]` section of `podguy.toml`:
   - Title (max 100 characters) from show notes or the user's wording.
   - Description body written to `dist/analysis/<slug>/youtube-description.md`.
   - Chapters from `dist/analysis/<slug>/chapters.md` when present (first chapter must start at `00:00`).
   - Tags from proper-noun review or profile `default_tags`.
4. Show the user the drafted metadata and confirm privacy/timing (private default, unlisted, public, or `--publish-at`).
5. Preview the request with `--dry-run`, then upload:
   `uv run --group youtube python scripts/youtube_publish.py upload <video> --title "<title>" --description-file dist/analysis/<slug>/youtube-description.md --chapters-file dist/analysis/<slug>/chapters.md`
6. Add `--thumbnail`, `--caption <transcript.srt>`, `--playlist-id`, or `--publish-at` as requested.
7. Confirm with `status <video-id>` and report the YouTube Studio link.

Output expectations:

- Never upload without the user confirming the final metadata.
- State the resulting privacy status plainly (private/scheduled/public) and link YouTube Studio.
- Surface quota or processing errors directly instead of retrying silently.

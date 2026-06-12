---
name: podguy-youtube-publisher
description: Use when the user wants to upload, schedule, or manage podcast episode videos on YouTube. Compose upload metadata from existing podguy analysis artifacts and publish with scripts/youtube_publish.py.
compatibility: Requires a Google Cloud OAuth client with the YouTube Data API v3 enabled, plus the youtube uv dependency group. Works from repo root.
---

# podguy YouTube Publisher

Use this skill when the user asks to upload an episode to YouTube, schedule a premiere/publish time, set thumbnails or captions, add uploads to a playlist, or check upload status.

This skill complements `podguy-post-production`:

- pi does editorial judgment: drafting the title, description, tags, and chapter list
- `scripts/youtube_publish.py` does deterministic YouTube Data API calls
- uploads default to **private** so publishing stays a deliberate, reviewable step

## One-time setup

If the user has never authenticated, walk them through it:

1. Create a Google Cloud project and enable **YouTube Data API v3**.
2. Create an OAuth client of type **Desktop app** (APIs & Services > Credentials).
3. Save the downloaded JSON to `~/.config/podguy/youtube/client_secret.json`.
4. Run the auth flow (opens a browser):

```bash
uv run --group youtube python scripts/youtube_publish.py auth
```

The token is cached at `~/.config/podguy/youtube/token.json`. Both paths can be overridden with `--client-secrets` / `--token` or `PODGUY_YT_CLIENT_SECRETS` / `PODGUY_YT_TOKEN`.

Personal-channel projects can stay in OAuth "testing" mode with the user's account added as a test user. Warn the user: videos uploaded through unverified API projects may be locked private until the project passes a YouTube API audit, so verify scheduling behavior before relying on it.

## Inputs to gather

1. Final episode video path (a real export, not a review cut).
2. Episode slug, e.g. `ep006`, to find existing analysis artifacts.
3. Title — draft from show notes if not provided; max 100 characters.
4. Description — prefer composing a `dist/analysis/<slug>/youtube-description.md` from show notes.
5. Chapters — reuse `dist/analysis/<slug>/chapters.md` when it exists (YouTube parses `00:00 Title` lines; the first chapter must start at `00:00`).
6. Privacy and timing — private (default), unlisted, public, or scheduled via `--publish-at`.
7. Optional: thumbnail image, SRT captions from the transcript run, playlist.

Reuse existing analysis outputs when they match the episode. If chapters or show notes are missing and the user wants them in the description, run the normal post-production workflow first.

## Workflow

1. Draft the title, description, and tags from the episode's analysis artifacts and the `[youtube]` section of `podguy.toml`.
2. Write the description body to `dist/analysis/<slug>/youtube-description.md`.
3. Show the user the metadata and confirm before uploading.
4. Preview the exact request first:

```bash
uv run --group youtube python scripts/youtube_publish.py upload \
  <episode-video> \
  --title "<title>" \
  --description-file dist/analysis/<slug>/youtube-description.md \
  --chapters-file dist/analysis/<slug>/chapters.md \
  --dry-run
```

5. Upload for real by dropping `--dry-run`. Add `--thumbnail`, `--caption`, `--playlist-id`, or `--publish-at` as requested.
6. Report the YouTube Studio link and remind the user the video is private until they (or the schedule) publish it.

## Commands

Scheduled publish (YouTube flips it public at the given time):

```bash
uv run --group youtube python scripts/youtube_publish.py upload \
  <episode-video> \
  --title "<title>" \
  --description-file dist/analysis/<slug>/youtube-description.md \
  --privacy private \
  --publish-at 2026-06-20T16:00:00Z
```

Manage an existing upload:

```bash
uv run --group youtube python scripts/youtube_publish.py status <video-id>
uv run --group youtube python scripts/youtube_publish.py set-thumbnail <video-id> thumb.jpg
uv run --group youtube python scripts/youtube_publish.py set-caption <video-id> dist/analysis/<slug>/transcript.srt
uv run --group youtube python scripts/youtube_publish.py add-to-playlist <video-id> <playlist-id>
uv run --group youtube python scripts/youtube_publish.py update <video-id> --title "<new title>"
uv run --group youtube python scripts/youtube_publish.py list-uploads --limit 10
```

## Profile defaults

The `[youtube]` section of `podguy.toml` supplies defaults (see `podguy.example.toml`):

- `default_privacy` — used when `--privacy` is omitted (falls back to `private`)
- `default_category` — YouTube category id (falls back to `22`, People & Blogs)
- `default_tags` — used when `--tags` is omitted
- `playlist_id` — uploads are added here automatically
- `description_footer` — appended to every composed description
- `made_for_kids` — self-declared made-for-kids flag

## Safety guidance

- Never upload without explicit user confirmation of the final metadata; always offer a `--dry-run` preview first.
- Default to `private`; only use `public` when the user explicitly says to publish now.
- Treat `--publish-at` as the preferred way to "go live at <time>"; it requires private privacy.
- Each upload costs 1600 of the default 10000 daily quota units — surface quota errors plainly and suggest retrying after the Pacific-midnight reset.
- Do not commit OAuth secrets or tokens; they live outside the repo by default.

## References

- Publisher CLI: [../../scripts/youtube_publish.py](../../scripts/youtube_publish.py)
- Publish prompt: [../../prompts/publish-youtube.md](../../prompts/publish-youtube.md)
- Chapters prompt: [../../prompts/chapters.md](../../prompts/chapters.md)
- Show notes prompt: [../../prompts/show-notes.md](../../prompts/show-notes.md)

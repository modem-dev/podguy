# podguy

Pi-first post-production tooling for podcast and video-podcast editors who want transcripts, chapters, clip candidates, cuts, and social review exports from local media.

[![CI](https://github.com/modem-dev/podguy/actions/workflows/ci.yml/badge.svg)](https://github.com/modem-dev/podguy/actions/workflows/ci.yml)

## What it does

- Launches `pi` with podcast-specific skills, prompts, and a startup widget.
- Transcribes local audio/video files with Whisper-compatible backends.
- Prepares long transcripts into timecoded chunks for editorial review.
- Scans video episodes for likely interstitials and non-host inserts.
- Generates chapters, clip candidates, cut reports, show notes, quotes, and proper noun checks.
- Cuts selected highlight ranges into review exports for TikTok, Reels, YouTube Shorts, trailers, or social posts.

Generated transcripts, scans, thumbnails, notes, and clip exports go under gitignored `dist/` by default.

## Install

Clone the repo and install the local Node tooling:

```bash
git clone https://github.com/modem-dev/podguy.git
cd podguy
npm install
```

Install the required system tools:

```bash
brew install uv ffmpeg
```

Notes:

- `ffmpeg` is used for fixtures, transcription backends, and clip cutting.
- `uv` runs the Python scripts and optional transcription dependency groups.
- The video scanner is macOS-only and uses Swift / AVFoundation / Vision.

Before first use, authenticate pi with `/login` or your usual provider API key setup.

Set up a real transcription backend when you are ready to transcribe episodes:

```bash
uv sync --group transcribe-mlx      # Apple Silicon
uv sync --group transcribe-faster   # Cross-platform
uv sync --group transcribe-whisper  # OpenAI Whisper package
```

## Quick start

Create an optional show profile:

```bash
cp podguy.example.toml podguy.toml
```

Start podguy from the repo root:

```bash
./podguy
```

Then ask pi for a concrete episode task:

```text
Analyze "episode-006-draft.mp4" as ep006.

Generate chapters for ep006 in timestamp-title format.

Find likely TikTok/Shorts clips for ep006 and cut vertical review exports.
```

For broad requests, podguy should clarify between:

- **quick pass**: optional video scan + transcript + prepared transcript artifacts + short summary
- **full review**: quick pass + chapters + clips + cuts + show notes + quotes + proper noun review

## Common workflows

### Scan a video

```bash
swift scripts/scan_podcast.swift "episode-006-draft.mp4" dist/analysis/ep006/scan 0.5
open dist/analysis/ep006/scan/report.html
```

Key outputs:

- `interstitial_candidates.csv`
- `non_host_candidates.csv`
- `report.html`
- `thumbs/`

Scanner results are heuristic review aids, not exact edit points.

### Transcribe media

```bash
uv run python scripts/transcribe_video.py --list-backends

uv run --group transcribe-mlx python scripts/transcribe_video.py \
  "episode-006-draft.mp4" \
  dist/analysis/ep006/transcript \
  --backend mlx-whisper
```

Key outputs:

- `segments.json`
- `transcript.txt`
- `transcript.srt`
- `transcript.vtt`
- `summary.txt`

Use `--backend mock` only for tests and setup validation.

### Prepare transcript artifacts

```bash
uv run python scripts/prepare_transcript_analysis.py \
  dist/analysis/ep006/transcript \
  --output-dir dist/analysis/ep006 \
  --slug ep006 \
  --plain-output-names
```

Key outputs:

- `dist/analysis/ep006/transcript_chunks.md`
- `dist/analysis/ep006/transcript_index.json`

These are the main inputs for chaptering and editorial analysis.

### Cut selected clips

After pi writes `dist/analysis/ep006/clips.md`, cut original-aspect review exports:

```bash
uv run python scripts/cut_clips.py \
  "episode-006-draft.mp4" \
  dist/analysis/ep006/clips.md \
  dist/analysis/ep006/clips/cuts
```

For simple vertical Shorts/TikTok/Reels review exports:

```bash
uv run python scripts/cut_clips.py \
  "episode-006-draft.mp4" \
  dist/analysis/ep006/clips.md \
  dist/analysis/ep006/clips/shorts \
  --aspect vertical \
  --pad-start 1 \
  --pad-end 1
```

The cutter writes generated media plus `manifest.json`. Vertical and square modes use center-crop framing, so treat them as review exports unless the framing has been checked.

### Download real sample media

Use the Cordkillers open-license video-podcast excerpt for local evaluation:

```bash
scripts/download_sample_media.sh
```

This writes to:

```text
dist/test-fixtures/open-license/cordkillers-572/
```

The default sample is a 3m50s excerpt from `00:08:00` of Cordkillers 572, licensed CC BY-SA 4.0. The range includes multiple podcast layouts, lower thirds, chat/sidebar graphics, a Patreon bumper, and an outro/interstitial card. The script writes `ATTRIBUTION.md` next to the generated media.

## Configuration

`podguy.toml` lets you define show-specific context without changing the workflow:

```toml
show_name = "Example Podcast"
show_slug = "example"
hosts = ["Host One", "Host Two"]
tone = "curious, direct, practical"
audience = "builders and technical operators"
chapter_style = "concise descriptive titles"
preferred_review = "quick pass"
```

`podcast.toml` is also accepted as a compatible profile name.

## Project layout

- [`podguy`](podguy): launcher for pi with repo-local skills, prompts, and startup extension.
- [`src/podguy-post-production/SKILL.md`](src/podguy-post-production/SKILL.md): main editorial workflow skill.
- [`src/podguy-clip-cutter/SKILL.md`](src/podguy-clip-cutter/SKILL.md): social clip export workflow skill.
- [`src/podguy-startup.ts`](src/podguy-startup.ts): pi startup widget.
- [`prompts/`](prompts): optional prompt shortcuts.
- [`scripts/`](scripts): deterministic scanner, transcript, prep, fixture, sample, and clip-cutting tools.
- [`tests/`](tests): smoke tests wrapped by Vitest.
- [`AGENTS.md`](AGENTS.md): repo guidance for coding agents.

## Development

Run the full validation surface:

```bash
npm run format:check
npm run lint
npm run typecheck
npm test
```

Run the shell smoke tests directly:

```bash
bash scripts/test.sh
```

CI runs the same checks on macOS because the scanner depends on macOS media APIs.

## Contributing

Small, focused PRs are welcome. Before opening a PR, run the validation commands above.

For workflow or heuristic changes, include:

- media type and OS/backend details
- expected vs actual output
- relevant transcript, scan, or manifest paths when available

See [`CHANGELOG.md`](CHANGELOG.md) for user-visible changes and [`AGENTS.md`](AGENTS.md) for repo maintenance guidance.

## Security

This repo does not have a published security policy yet. If you find a sensitive issue, do not open a public issue. Contact the maintainers privately first.

## Sponsor

Sponsored by [Modem](https://modem.dev?utm_source=github&utm_medium=oss&utm_campaign=podguy).

<a href="https://modem.dev?utm_source=github&utm_medium=oss&utm_campaign=podguy">
  <picture>
    <source media="(prefers-color-scheme: dark)" srcset="https://modem.dev/images/logo/svg/modem-combined-white.svg">
    <source media="(prefers-color-scheme: light)" srcset="https://modem.dev/images/logo/svg/modem-combined-black.svg">
    <img src="https://modem.dev/images/logo/svg/modem-combined-black.svg" alt="Modem" width="220">
  </picture>
</a>

## License

MIT. See [`LICENSE`](LICENSE).

## Support

Use [GitHub issues](https://github.com/modem-dev/podguy/issues) for bugs, questions, and workflow discussion.

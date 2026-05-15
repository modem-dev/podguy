# podguy

Pi-first post-production workflow for podcasts and video podcasts. Run `./podguy` to open pi in a focused editing mode for this repo.

## Why podguy

- Launch `./podguy` and work through a repo-local pi skill.
- Generate transcripts and subtitle files from local audio or video media.
- Prepare long transcript artifacts for reliable editorial review.
- Find likely interstitial and inserted-content timecodes from episode videos.
- Ask the agent for chapters, clip candidates, cut suggestions, show notes, quotes, and proper noun cleanup.
- Configure show-specific context with `podguy.toml` without changing the workflow.

## Install

This project is designed to be operated through `pi`, with `./podguy` as the main entrypoint.

Install the required tools:

```bash
npm install -g @mariozechner/pi-coding-agent
brew install uv
# optional, only for local transcription backends and video scanning
brew install ffmpeg
```

You can install pi globally or as a repo-local dev dependency. The `./podguy` launcher uses `node_modules/.bin/pi` when present and falls back to a global `pi` install.

Before first use, authenticate pi with `/login` or your usual provider API key setup.

Set up one transcript backend if you want real transcription:

```bash
uv sync --group transcribe-mlx      # Apple Silicon
uv sync --group transcribe-faster   # Cross-platform
uv sync --group transcribe-whisper  # OpenAI Whisper
```

Notes:

- `scripts/scan_podcast.swift` is macOS-only and requires `swift`.
- `scripts/transcribe_video.py` requires Python 3.9+ and `uv`.
- The `mock` backend exists for tests and setup validation, not real transcription.

## Configure a show

Copy the example profile and customize it for your podcast:

```bash
cp podguy.example.toml podguy.toml
```

The profile can define the show name, hosts, tone, audience, chapter style, and default output preferences. Podguy also accepts `podcast.toml` as a compatible profile name.

You can use podguy without a profile; the agent will only ask for show-specific context when it matters.

## Quick start

Start the dedicated launcher from the repo root:

```bash
cd podguy
./podguy
```

The launcher starts pi with only the podguy repo skill and startup widget loaded, adds a podguy-specific system hint, and stores sessions under `.pi/sessions`.

If you want the raw pi command instead, `./podguy` is a thin wrapper around pi for this repo.

You should see a short help widget above the editor with example actions.

Then ask pi to work the episode. For example:

```text
Analyze "episode-006-draft.mp4" as ep006.

Generate chapters for ep006 in timestamp-title format.

Review this episode and suggest cuts, highlight moments, and weak sections.
```

## Episode workflow

The intended flow is:

1. Start with a new episode recording, draft export, or preview export. Audio and video files are both supported for transcription.
2. For video episodes, generate timecodes for likely interstitials and inserted content so they are easy to review.
3. Generate a transcript for the current cut of the episode.
4. Prepare transcript chunks and an index for pi-driven editorial work.
5. Use the transcript to propose chapters in this format:

```text
00:00 Intro
05:34 Section title
```

6. Use the transcript to suggest:
   - cuts for time
   - strong and weak sections
   - highlight-worthy clips
   - show notes and references
   - quote candidates
   - proper noun or spelling issues
   - places where interstitials or inserts would help, when video is available

## Quick pass vs full review

When an ask is broad, podguy should clarify between:

- **quick pass** = optional video scan + transcript + prepared transcript artifacts + short summary
- **full review** = quick pass + chapters + clips + cuts + show notes + quotes + proper noun review

If you ask for one specific deliverable, podguy should do that directly.

## Output location

Podguy writes generated episode artifacts under `dist/analysis/` by default. The entire `dist/` directory is gitignored so transcripts, scans, thumbnails, notes, and local media-derived files stay out of version control.

## Repo skill

The repo-local skill is the main interface for this project:

- Launcher: [podguy](podguy)
- Skill: [src/podguy-post-production/SKILL.md](src/podguy-post-production/SKILL.md)
- Startup widget extension: [src/podguy-startup.ts](src/podguy-startup.ts)
- Prompt templates: [prompts](prompts)
- Profile example: [podguy.example.toml](podguy.example.toml)
- Discovery: [package.json](package.json)
- Project instructions: [AGENTS.md](AGENTS.md)
- Underlying tools: [scripts/scan_podcast.swift](scripts/scan_podcast.swift), [scripts/transcribe_video.py](scripts/transcribe_video.py), [scripts/prepare_transcript_analysis.py](scripts/prepare_transcript_analysis.py)

The launcher and skill explain the user workflow and tell pi how to run the software stack.

## Manual tool reference

You normally use this repo through pi, but the underlying commands are:

### Scan a video

```bash
swift scripts/scan_podcast.swift <input-video> <output-dir> [sample-interval-seconds]
```

Example:

```bash
swift scripts/scan_podcast.swift "episode-006-draft.mp4" dist/analysis/ep006/scan 0.5
open dist/analysis/ep006/scan/report.html
```

### Transcribe media

```bash
uv run python scripts/transcribe_video.py --list-backends
uv run python scripts/transcribe_video.py <input-media> <output-dir> [options]
```

Example:

```bash
uv run --group transcribe-mlx python scripts/transcribe_video.py \
  "episode-006-draft.mp4" \
  dist/analysis/ep006/transcript \
  --backend mlx-whisper
```

### Prepare transcript artifacts

```bash
uv run python scripts/prepare_transcript_analysis.py \
  dist/analysis/ep006/transcript \
  --output-dir dist/analysis/ep006 \
  --slug ep006 \
  --plain-output-names
```

## Docs

- Launcher: [podguy](podguy)
- Skill: [src/podguy-post-production/SKILL.md](src/podguy-post-production/SKILL.md)
- Startup widget extension: [src/podguy-startup.ts](src/podguy-startup.ts)
- Project instructions: [AGENTS.md](AGENTS.md)
- Profile example: [podguy.example.toml](podguy.example.toml)
- Scanner CLI: [scripts/scan_podcast.swift](scripts/scan_podcast.swift)
- Transcript CLI: [scripts/transcribe_video.py](scripts/transcribe_video.py)
- Transcript prep CLI: [scripts/prepare_transcript_analysis.py](scripts/prepare_transcript_analysis.py)
- Fixture builder: [scripts/make_test_fixture.sh](scripts/make_test_fixture.sh)
- Smoke tests: [tests/test_scan_podcast.sh](tests/test_scan_podcast.sh), [tests/test_transcribe_video.sh](tests/test_transcribe_video.sh), [tests/test_prepare_transcript_analysis.sh](tests/test_prepare_transcript_analysis.sh)

## Contributing

Small, focused PRs are welcome.

Before opening a PR:

```bash
bash tests/test_transcribe_video.sh
bash tests/test_scan_podcast.sh
bash tests/test_prepare_transcript_analysis.sh
```

For larger workflow or heuristic changes, open an issue first with the media type, expected vs actual output, and your OS/backend/model details.

## Security

This repo does not have a published security policy yet. If you find a sensitive issue, do not open a public issue.

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

MIT. See [LICENSE](LICENSE).

## Support

Use GitHub issues for bugs, questions, and workflow discussion once this repo has a public issue tracker.

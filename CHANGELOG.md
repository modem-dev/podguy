# Changelog

All notable user-visible changes to this project are documented in this file.

## [Unreleased]

### Added

- Add CI and local maintenance scripts for formatting, linting, typechecking, and smoke tests.
- Add YouTube publishing: `scripts/youtube_publish.py` CLI (OAuth, resumable uploads, thumbnails, captions, playlists, scheduled publishing), the `podguy-youtube-publisher` skill, a `/publish-youtube` prompt shortcut, and a `[youtube]` profile section.

### Changed

- Discover skills dynamically in the startup header and show analyzed episodes from `dist/analysis/`, so returning users can see what already exists.
- Remove the unused `[outputs]`, `[transcription]`, and `[video_scan]` sections from `podguy.example.toml`; document which sections are read by code vs. by the agent.

### Fixed

- Standardize the chapters artifact on `dist/analysis/<slug>/chapters.md` so the chapters and YouTube publish workflows agree.
- Correct the launcher's "pi is not installed" message to point at `npm install` and the renamed `@earendil-works/pi-coding-agent` package.
- Document the OAuth test-user requirement, testing-mode token expiry, uv first-run behavior, and the macOS-only scanner skip rule.
- Give the "no transcription backend found" error actionable `uv sync --group ...` commands.
- Make the visual scanner fail with clean errors instead of crashing on missing inputs, zero sample intervals, and audio-only files.
- Download sample media atomically so interrupted downloads no longer leave truncated files that look complete.
- Report ffmpeg clip-cut failures cleanly and still write the manifest for clips that already succeeded.

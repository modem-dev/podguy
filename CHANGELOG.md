# Changelog

All notable user-visible changes to this project are documented in this file.

## [Unreleased]

### Added

- Add CI and local maintenance scripts for formatting, linting, typechecking, and smoke tests.
- Add YouTube publishing: `scripts/youtube_publish.py` CLI (OAuth, resumable uploads, thumbnails, captions, playlists, scheduled publishing), the `podguy-youtube-publisher` skill, a `/publish-youtube` prompt shortcut, and a `[youtube]` profile section.

### Changed

### Fixed

- Standardize the chapters artifact on `dist/analysis/<slug>/chapters.md` so the chapters and YouTube publish workflows agree.
- Correct the launcher's "pi is not installed" message to point at `npm install` and the renamed `@earendil-works/pi-coding-agent` package.
- Document the OAuth test-user requirement, testing-mode token expiry, uv first-run behavior, and the macOS-only scanner skip rule.
- Give the "no transcription backend found" error actionable `uv sync --group ...` commands.

---
name: podguy-post-production
description: Use for generic podcast and video-podcast post-production. Run the repo's transcript and optional visual scanner tools on episode media, prepare transcript artifacts, propose YouTube/podcast chapters, and give editorial feedback such as cuts, clips, show notes, quotes, highlights, and proper noun cleanup.
compatibility: Launch pi from the repository root. The visual scanner requires macOS and Swift. The transcript CLI requires Python 3.9+, uv, and an installed transcription backend.
---

# podguy Post Production

This repository is meant to be operated through pi from the repo root.

## Goal

Help with repeatable post-recording podcast editing for any podcast or video podcast.

Use this workflow when the user wants any of the following:

- analyze a new episode recording, draft export, or preview media file
- generate a transcript for the current cut of the episode
- prepare transcript artifacts for long-context editorial review
- find likely interstitial or inserted-content timecodes in video episodes
- propose YouTube or podcast chapter markers
- review the episode for cuts, highlights, clips, weak sections, and publishing assets
- cut/export selected clip candidates for TikTok, Reels, YouTube Shorts, trailers, or social review

## Podcast profile

Prefer show-specific context from `podguy.toml` when it exists. If only `podcast.toml` exists, use that as a compatible profile file.

Use profile fields such as:

- `show_name`
- `show_slug`
- `hosts`
- `tone`
- `audience`
- `chapter_style`
- `preferred_review`
- `[outputs]` toggles

Do not assume a specific show, hosts, audience, tone, domain, or episode naming pattern unless the user or profile provides it.

If profile context is missing, only ask for it when it affects the requested deliverable. For example, chapters usually do not need a full show profile; publishable show notes might.

## Natural-language UX

Assume the user will ask in plain English and may not know or remember slash commands.

Prompt templates such as `/prepare-analysis`, `/phase1`, `/full-review`, `/chapters`, and `/cuts` are optional shortcuts for power users, not required vocabulary.

When the request is ambiguous, ask one short clarifying question before deciding how much work to do.

Use this default clarification:

- **quick pass** = optional video scan + transcript + prepared transcript artifacts + short summary
- **full review** = quick pass + chapters + clips + cuts + show notes + quotes + proper noun review

If the user already clearly asked for a specific deliverable, do that directly instead of asking.

For synthetic or test fixture inputs, default to a leaner evaluation mindset and prefer a quick pass unless the user explicitly asks for the full editorial bundle.

## Default workflow

### Quick pass

1. Start from the input media file. It can be audio or video as long as `scripts/transcribe_video.py` can process it.
2. If the input is video and you are on macOS, optionally run the visual scanner to find likely interstitials and other non-host inserts. Skip this for audio-only inputs and on non-macOS systems (say why when skipping).
3. Run the transcript tool on the same media file.
4. Prepare deterministic transcript artifacts for pi with `scripts/prepare_transcript_analysis.py`.
5. Return a short grounded summary with:
   - scan status and likely interstitials / non-host inserts when applicable
   - transcript status
   - prepared artifact paths
   - suggested next step if the user wants more

### Full review

After the quick pass, use the prepared transcript artifacts to generate episode outputs with pi-driven judgment:

- chapters
- clip candidates
- cuts for time
- show notes and likely links
- quote sheet
- proper noun review

Write the outputs under `dist/analysis/` and summarize what was produced.

## Scripts vs pi

Keep this boundary clear:

- **repo scripts** should do deterministic work such as scanning, transcribing, chunking, indexing, and formatting support
- **pi** should do editorial judgment such as chapter selection, clip selection, cut suggestions, show notes, quotes, and proper noun review

Do not build a second heuristic editorial brain in local scripts when pi can reason over prepared artifacts directly.

## Output locations

Unless the user asks for different paths or the profile config says otherwise, write generated artifacts under `dist/analysis/`.

Recommended single-show pattern:

- `dist/analysis/<episode>/scan/`
- `dist/analysis/<episode>/transcript/`
- `dist/analysis/<episode>/transcript_large/` when keeping multiple transcript variants
- `dist/analysis/<episode>/transcript_chunks.md`
- `dist/analysis/<episode>/transcript_index.json`
- `dist/analysis/<episode>/chapters.md`
- `dist/analysis/<episode>/clips.md`
- `dist/analysis/<episode>/clips/cuts/`
- `dist/analysis/<episode>/clips/shorts/`
- `dist/analysis/<episode>/cut_report.md`
- `dist/analysis/<episode>/show_notes.md`
- `dist/analysis/<episode>/quotes.md`
- `dist/analysis/<episode>/proper_nouns.md`
- `dist/analysis/fixtures/<fixture>/...` for test-media outputs
- `dist/test-fixtures/open-license/cordkillers-572/` for the optional downloaded Cordkillers sample

For multi-show usage, prefer:

- `dist/analysis/<show-slug>/<episode>/...`

If the repo already has outputs for the same episode and media version, prefer reusing them unless the user asks for a fresh run.

## Visual scan

Run this only for video inputs.

Command:

```bash
swift scripts/scan_podcast.swift <input-video> <output-dir> [sample-interval-seconds]
```

Example:

```bash
swift scripts/scan_podcast.swift "episode-006-draft.mp4" dist/analysis/ep006/scan 0.5
```

Key outputs:

- `interstitial_candidates.csv`
- `non_host_candidates.csv`
- `report.html`
- `thumbs/`

Important: the scanner is heuristic. Use it to narrow review work, not to claim exact edit points.

## Transcript generation

Check available backends first if needed:

```bash
uv run python scripts/transcribe_video.py --list-backends
```

Preferred order:

1. `mlx-whisper` on Apple Silicon
2. `faster-whisper` on other machines
3. `whisper` if that is the installed option
4. `mock` only for tests or setup validation

Command:

```bash
uv run python scripts/transcribe_video.py <input-media> <output-dir> [options]
```

Examples:

```bash
uv run --group transcribe-mlx python scripts/transcribe_video.py \
  "episode-006-draft.mp4" \
  dist/analysis/ep006/transcript \
  --backend mlx-whisper

uv run --group transcribe-faster python scripts/transcribe_video.py \
  "episode-006-draft.mp4" \
  dist/analysis/ep006/transcript \
  --backend faster-whisper
```

Key outputs:

- `segments.json`
- `transcript.txt`
- `transcript.srt`
- `transcript.vtt`
- `summary.txt`

## Transcript analysis prep

Command:

```bash
uv run python scripts/prepare_transcript_analysis.py <transcript-dir> [options]
```

Example:

```bash
uv run python scripts/prepare_transcript_analysis.py \
  dist/analysis/ep006/transcript \
  --output-dir dist/analysis/ep006 \
  --slug ep006 \
  --plain-output-names
```

Key outputs:

- `dist/analysis/<episode>/transcript_chunks.md`
- `dist/analysis/<episode>/transcript_index.json`

Use these prepared artifacts as the main input for chaptering and editorial analysis.

Prefer reusing prepared artifacts when they already match the requested transcript and slug.

## Prompt templates

When prompt templates are available, treat them as optional shortcuts for the repo-local workflow:

- `/prepare-analysis`
- `/phase1`
- `/full-review`
- `/chapters`
- `/clips`
- `/cuts`
- `/cut-clips`
- `/show-notes`
- `/quotes`
- `/proper-nouns`

Do not assume the user knows these names. Prefer natural-language clarification first, and mention the shortcut only if it would help.

## Required deliverables

### For a quick pass

1. **Scan status**
   - whether visual scanning was run, skipped for audio-only input, or unavailable
   - likely interstitial timecodes when applicable
   - likely non-host insert timecodes when applicable
   - any scan caveats

2. **Transcript status**
   - transcript output path
   - backend and model used, if relevant

3. **Prepared transcript status**
   - prepared artifact paths
   - whether they were reused or freshly generated

4. **Short editorial summary**
   - strongest moment or two
   - biggest obvious cut or cleanup opportunity
   - suggested next step if the user wants a full review

### For a full review

Include the quick-pass deliverables plus:

5. **Chapters**
   - derive from the prepared transcript artifacts and overall episode flow
   - keep titles concise and descriptive

6. **Editorial outputs**
   - `dist/analysis/<episode>/clips.md`
   - `dist/analysis/<episode>/cut_report.md`
   - `dist/analysis/<episode>/show_notes.md`
   - `dist/analysis/<episode>/quotes.md`
   - `dist/analysis/<episode>/proper_nouns.md`

## Chapter format

When the user asks for sections or chapters, return them as one timestamp-and-title per line.

Format:

```text
00:00 Intro
05:34 Main topic begins
01:12:10 Final takeaways
```

Rules:

- first line must start at `00:00`
- no bullets or numbering inside the chapter list
- use `HH:MM:SS` when a timestamp goes past one hour
- keep titles short enough to paste directly into YouTube or podcast platforms
- follow `chapter_style` from `podguy.toml` when present

## Editorial analysis guidance

Use the prepared transcript artifacts as the primary source for transcript-heavy analysis, and use raw transcript files only when you need additional detail.

Use transcript evidence and timecodes whenever possible.

Focus on:

- what to cut for time
- where the episode gets stronger or weaker
- where the speakers repeat the same point
- which segments are most likely to make good clips
- what belongs in show notes or a quote sheet
- which names, products, or terms look suspicious and should be reviewed
- where interstitials or inserted visuals would help pacing or context, when video is available

## Clip cutting

When the user wants actual media files for likely clippable moments, use the `podguy-clip-cutter` skill and `scripts/cut_clips.py` after clip candidates have been selected.

Default original-aspect command:

```bash
uv run python scripts/cut_clips.py \
  <input-media> \
  dist/analysis/<episode>/clips.md \
  dist/analysis/<episode>/clips/cuts
```

Vertical Shorts/TikTok/Reels review export:

```bash
uv run python scripts/cut_clips.py \
  <input-media> \
  dist/analysis/<episode>/clips.md \
  dist/analysis/<episode>/clips/shorts \
  --aspect vertical \
  --pad-start 1 \
  --pad-end 1
```

Treat generated clips as review exports, not final edit points. Warn when simple center-crop vertical framing may cut off speakers, slides, or screen shares.

If you suggest cuts, explain why:

- repetitive
- speculative without payoff
- low energy
- too niche relative to the main thesis
- setup chatter that should not survive the final edit

## References

- Scanner: [../../scripts/scan_podcast.swift](../../scripts/scan_podcast.swift)
- Transcript CLI: [../../scripts/transcribe_video.py](../../scripts/transcribe_video.py)
- Transcript prep CLI: [../../scripts/prepare_transcript_analysis.py](../../scripts/prepare_transcript_analysis.py)
- Clip cutter CLI: [../../scripts/cut_clips.py](../../scripts/cut_clips.py)
- Fixture builder: [../../scripts/make_test_fixture.sh](../../scripts/make_test_fixture.sh)
- Open-license sample downloader: [../../scripts/download_sample_media.sh](../../scripts/download_sample_media.sh)
- Smoke tests: [../../tests/test_scan_podcast.sh](../../tests/test_scan_podcast.sh), [../../tests/test_transcribe_video.sh](../../tests/test_transcribe_video.sh), [../../tests/test_prepare_transcript_analysis.sh](../../tests/test_prepare_transcript_analysis.sh), [../../tests/test_cut_clips.sh](../../tests/test_cut_clips.sh)

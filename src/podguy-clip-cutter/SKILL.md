---
name: podguy-clip-cutter
description: Use when the user wants to cut/export likely clippable podcast moments for TikTok, Reels, YouTube Shorts, trailers, or social review. Turn pi-selected clip candidates into media files with scripts/cut_clips.py.
compatibility: Requires ffmpeg for actual cutting. Works from repo root after transcript prep and clip candidate selection.
---

# podguy Clip Cutter

Use this skill when the user asks to cut, export, render, or prepare short-form/social clips from a podcast or video podcast.

This skill complements `podguy-post-production`:

- pi does editorial judgment and chooses candidate moments
- `scripts/cut_clips.py` does deterministic ffmpeg cutting
- generated media stays under gitignored `dist/analysis/`

## Sample media

When a real video-podcast fixture is useful, run:

```bash
scripts/download_sample_media.sh
```

This downloads a local excerpt from Cordkillers 572 under `dist/test-fixtures/open-license/cordkillers-572/` with attribution. The default 00:08:00-00:11:50 excerpt includes a three-person podcast layout, lower thirds, chat/sidebar graphics, a Patreon bumper, and an outro/interstitial card.

## Inputs to gather

Identify:

1. Source media path: original recording, draft export, or preview export.
2. Episode slug: e.g. `ep006`.
3. Clip candidate file:
   - default: `dist/analysis/<slug>/clips.md`
   - also supported: `.txt`, `.csv`, or `.json` with start/end ranges
4. Output intent:
   - review cuts in original aspect
   - vertical Shorts/TikTok/Reels exports
   - square or horizontal variants

If the user has not selected clip candidates yet, run the normal clip workflow first and write `dist/analysis/<slug>/clips.md`.

## Clip candidate format

The cutter accepts ranges in Markdown/plain text, CSV, or JSON.

Markdown example:

```md
## Why this market flipped
- 00:12:14 - 00:13:08 — Strong contrarian claim with a clean payoff.
```

CSV example:

```csv
title,start,end
Why this market flipped,00:12:14,00:13:08
```

JSON example:

```json
{
  "clips": [
    { "title": "Why this market flipped", "start": "00:12:14", "end": "00:13:08" }
  ]
}
```

## Commands

Original-aspect review cuts:

```bash
uv run python scripts/cut_clips.py \
  <input-media> \
  dist/analysis/<slug>/clips.md \
  dist/analysis/<slug>/clips/cuts
```

Vertical review exports for TikTok/Reels/YouTube Shorts:

```bash
uv run python scripts/cut_clips.py \
  <input-media> \
  dist/analysis/<slug>/clips.md \
  dist/analysis/<slug>/clips/shorts \
  --aspect vertical \
  --pad-start 1 \
  --pad-end 1
```

Useful options:

- `--limit N` cuts only the first N parsed clips
- `--pad-start SECONDS` and `--pad-end SECONDS` add review handles
- `--aspect source|vertical|square|horizontal` controls simple framing
- `--copy` is faster for original-aspect cuts but may be less frame-accurate
- `--dry-run` writes/prints commands without producing media

## Output locations

Recommended paths:

- `dist/analysis/<slug>/clips.md` — selected candidates
- `dist/analysis/<slug>/clips/cuts/` — original-aspect review exports
- `dist/analysis/<slug>/clips/shorts/` — vertical review exports
- `dist/analysis/<slug>/clips/*/manifest.json` — machine-readable export manifest

## Quality guidance

For social/short-form exports, prefer candidates that:

- start with a hook or clear tension
- make sense with minimal prior context
- contain a payoff, reversal, punchline, or memorable phrase
- land in roughly 20-90 seconds for Shorts/TikTok, unless the user asks otherwise
- have a clean ending or can be padded slightly for handles

Avoid exporting moments that:

- depend heavily on an earlier setup
- are mainly housekeeping or sponsor reads
- require lots of visual context that a center crop will lose
- contain unresolved cross-talk or dead air

## Caveats

- The script can center-crop vertical/square versions, but it does not track speakers or intelligently reframe shots.
- Treat outputs as review exports, not final mastered social edits.
- If vertical crop might cut off slides or side-by-side speakers, explicitly warn the user and suggest manual reframing in the editor.

## References

- Cutter: [../../scripts/cut_clips.py](../../scripts/cut_clips.py)
- Open-license sample downloader: [../../scripts/download_sample_media.sh](../../scripts/download_sample_media.sh)
- Clip prompt: [../../prompts/clips.md](../../prompts/clips.md)
- Cut-clips prompt: [../../prompts/cut-clips.md](../../prompts/cut-clips.md)

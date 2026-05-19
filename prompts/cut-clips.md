---
description: Cut selected social/highlight clips from an episode media file
---

Cut social/highlight clips for: $@

Workflow:

1. Identify the target episode slug, source media file, and clip-candidate file.
   - Default candidate file: `dist/analysis/<slug>/clips.md`.
   - If clip candidates do not exist yet, first create them with the `/clips` workflow.
2. Review the candidate ranges before cutting. Prefer clips with a clear hook, standalone context, and clean ending.
3. Run the deterministic cutter:
   `uv run python scripts/cut_clips.py <input-media> dist/analysis/<slug>/clips.md dist/analysis/<slug>/clips/cuts`
4. For TikTok/Reels/YouTube Shorts review exports, use vertical framing when appropriate:
   `uv run python scripts/cut_clips.py <input-media> dist/analysis/<slug>/clips.md dist/analysis/<slug>/clips/shorts --aspect vertical --pad-start 1 --pad-end 1`
5. Inspect `dist/analysis/<slug>/clips/cuts/manifest.json` or `dist/analysis/<slug>/clips/shorts/manifest.json` and summarize what was cut.

Output expectations:

- Do not claim the clips are final edit points; call them review exports.
- Include the output directory and manifest path.
- List the strongest exported clips with start/end timecodes.
- Mention any caveats, especially if vertical center-crop may cut off speakers or slides.

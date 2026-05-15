---
description: Build a quote sheet from prepared transcript artifacts
---
Build a quote sheet for: $@

Workflow:
1. Identify the target episode slug and the matching transcript directory or prepared transcript artifacts.
2. If `dist/analysis/<slug>/transcript_chunks.md` or `dist/analysis/<slug>/transcript_index.json` do not exist yet, run:
   `uv run python scripts/prepare_transcript_analysis.py <transcript-dir> --output-dir dist/analysis/<slug> --slug <slug> --plain-output-names`
3. Read the prepared transcript artifacts. For long transcripts, use the chunk index first and then inspect the strongest-sounding or most opinionated chunk sections.
4. Use pi-driven judgment to extract the strongest one-liners and quotable moments.
5. Write the final quote sheet to `dist/analysis/<slug>/quotes.md`.
6. Reply with the output path and a brief summary of the best quotes.

Output expectations:
- include the quote text with exact timecodes
- include a short rationale for why each quote is strong, memorable, or useful for promotion
- prefer a smaller set of high-signal quotes over a long weak list
- include speaker attribution when it is clear from the transcript or context
- keep the output useful for social posts, thumbnails, clips, or episode promotion

Quality bar:
- prioritize lines with punch, clarity, novelty, or strong wording
- avoid quotes that require too much surrounding context to land
- avoid filler, throat-clearing, or repetitive setup lines

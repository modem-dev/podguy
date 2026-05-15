---
description: Generate podcast/YouTube chapters from prepared transcript artifacts
---
Generate podcast/YouTube chapters for: $@

Workflow:
1. Identify the target episode slug and the matching transcript directory or prepared transcript artifacts.
2. If `dist/analysis/<slug>/transcript_chunks.md` or `dist/analysis/<slug>/transcript_index.json` do not exist yet, run:
   `uv run python scripts/prepare_transcript_analysis.py <transcript-dir> --output-dir dist/analysis/<slug> --slug <slug> --plain-output-names`
3. Read the prepared transcript artifacts. For long transcripts, use the chunk index first and then inspect the most relevant chunk sections.
4. Decide chapter boundaries and titles with pi-driven judgment. Use `chapter_style` from `podguy.toml` or `podcast.toml` when present.
5. Write the final chapter block to `dist/analysis/<slug>/chapters.txt`.
6. Reply with the output path and the final chapter block.

Formatting rules:
- first line must start at `00:00`
- use one `timestamp title` line per chapter
- no bullets or numbering in the final chapter block
- use `HH:MM:SS` when the episode goes past one hour
- keep titles concise enough to paste directly into YouTube or podcast platforms

Quality bar:
- optimize for topic shifts and listener usefulness
- avoid tiny micro-chapters unless they are genuinely useful
- prefer clear, plain-English titles over clever ones

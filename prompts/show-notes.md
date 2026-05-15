---
description: Draft show notes and likely links from prepared transcript artifacts
---
Draft show notes and likely links for: $@

Workflow:
1. Identify the target episode slug and the matching transcript directory or prepared transcript artifacts.
2. If `dist/analysis/<slug>/transcript_chunks.md` or `dist/analysis/<slug>/transcript_index.json` do not exist yet, run:
   `uv run python scripts/prepare_transcript_analysis.py <transcript-dir> --output-dir dist/analysis/<slug> --slug <slug> --plain-output-names`
3. Read the prepared transcript artifacts. For long transcripts, use the chunk index first and then inspect chunks that mention products, people, companies, repos, papers, tweets, or other references.
4. Use pi-driven judgment to draft publishable show notes.
5. Write the final draft to `dist/analysis/<slug>/show_notes.md`.
6. Reply with the output path and a brief summary of the most important references.

Output expectations:
- organize the notes clearly for later cleanup and publishing
- capture likely links, references, and named entities mentioned in the episode
- attach timecodes where they help an editor or producer verify the reference
- distinguish confirmed references from likely-but-uncertain ones when needed
- include a short episode summary if useful for the final notes package

Quality bar:
- prioritize what would actually help publish the episode
- avoid noisy over-extraction of every minor noun
- prefer a smaller, cleaner list of useful references over a giant dump

---
description: Find highlight clip candidates from prepared transcript artifacts
---
Find highlight clip candidates for: $@

Workflow:
1. Identify the target episode slug and the matching transcript directory or prepared transcript artifacts.
2. If `dist/analysis/<slug>/transcript_chunks.md` or `dist/analysis/<slug>/transcript_index.json` do not exist yet, run:
   `uv run python scripts/prepare_transcript_analysis.py <transcript-dir> --output-dir dist/analysis/<slug> --slug <slug> --plain-output-names`
3. Read the prepared transcript artifacts. For long transcripts, use the chunk index first and then inspect the most promising chunk sections.
4. Use pi-driven judgment to identify clip candidates with a hook, payoff, and clean ending.
5. Write the final report to `dist/analysis/<slug>/clips.md`.
6. Reply with the output path and a brief summary of the strongest candidates.

Output expectations:
- prioritize clips that would work for social, trailers, or cold opens
- prefer clips in the 30-120 second range unless there is a strong reason to go outside it
- include a short title for each clip
- include exact start and end timecodes plus approximate duration
- include a short rationale for why the clip works
- optionally include a key quote or excerpt if it helps the editor

Quality bar:
- avoid repetitive or context-heavy moments that will not stand alone
- prefer moments with tension, surprise, a strong opinion, or a clear payoff
- rank or clearly label the best few candidates

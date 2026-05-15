---
description: Generate a cut-for-time report from prepared transcript artifacts
---
Generate a cut-for-time report for: $@

Workflow:
1. Identify the target episode slug and the matching transcript directory or prepared transcript artifacts.
2. If `dist/analysis/<slug>/transcript_chunks.md` or `dist/analysis/<slug>/transcript_index.json` do not exist yet, run:
   `uv run python scripts/prepare_transcript_analysis.py <transcript-dir> --output-dir dist/analysis/<slug> --slug <slug> --plain-output-names`
3. Read the prepared transcript artifacts. For long transcripts, use the chunk index first and then inspect the weakest or most repetitive chunk sections.
4. Use pi-driven judgment to identify sections that can be trimmed or cut.
5. Write the final report to `dist/analysis/<slug>/cut_report.md`.
6. Reply with the output path and a short summary of the biggest cut opportunities.

Output expectations:
- include exact time ranges for each suggested cut or trim
- explain why each section is weak, repetitive, speculative, low-energy, or too niche
- estimate likely time savings when possible
- distinguish between hard cuts and lighter trims when useful
- mention especially strong sections that should definitely stay if that helps the edit

Quality bar:
- optimize for a tighter, stronger episode rather than maximizing total cuts
- avoid cutting sections only because they are technical if they still have clear payoff
- prefer cuts that reduce repetition, dead setup, or low-signal wandering

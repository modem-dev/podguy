---
description: Review likely proper noun and name issues from prepared transcript artifacts
---

Review likely proper noun issues for: $@

Workflow:

1. Identify the target episode slug and the matching transcript directory or prepared transcript artifacts.
2. If `dist/analysis/<slug>/transcript_chunks.md` or `dist/analysis/<slug>/transcript_index.json` do not exist yet, run:
   `uv run python scripts/prepare_transcript_analysis.py <transcript-dir> --output-dir dist/analysis/<slug> --slug <slug> --plain-output-names`
3. Read the prepared transcript artifacts. Focus on names, products, repos, companies, technologies, and suspicious spellings.
4. Use pi-driven judgment to flag proper nouns that look wrong, inconsistent, low-confidence, or worth manual review.
5. Write the review to `dist/analysis/<slug>/proper_nouns.md`.
6. Reply with the output path and a brief summary of the most important corrections or open questions.

Output expectations:

- include the suspicious term, its timecode, and surrounding context
- suggest the likely correct spelling or identity when you have a strong guess
- clearly label uncertain guesses as uncertain
- note repeated inconsistencies when the same term appears multiple times
- optimize for cleaning transcripts, chapter titles, and show notes

Quality bar:

- prioritize likely real transcription mistakes over stylistic nitpicks
- avoid pretending to know the right answer when the evidence is weak
- focus on names and terms that are likely to matter in publishing or editing

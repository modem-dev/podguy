---
description: Run the full podguy transcript and editorial review workflow for an episode
---

Run the full podguy review workflow for: $@

Goal:

- use pi for editorial judgment
- use repo scripts only for deterministic prep and formatting support
- use `podguy.toml` or `podcast.toml` show context when present

Workflow:

1. Identify the media file, transcript output directory, prepared transcript artifacts, and target episode slug.
2. If the transcript does not exist yet, ask for the media file/transcript directory or offer the exact `scripts/transcribe_video.py` command needed.
3. Ensure prepared transcript artifacts exist. If needed, run:
   `uv run python scripts/prepare_transcript_analysis.py <transcript-dir> --output-dir dist/analysis/<slug> --slug <slug> --plain-output-names`
4. Ground all editorial work in the prepared artifacts:
   - `dist/analysis/<slug>/transcript_chunks.md`
   - `dist/analysis/<slug>/transcript_index.json`
5. Produce these outputs under `dist/analysis/<slug>/`:
   - `dist/analysis/<slug>/chapters.txt`
   - `dist/analysis/<slug>/clips.md`
   - `dist/analysis/<slug>/cut_report.md`
   - `dist/analysis/<slug>/show_notes.md`
   - `dist/analysis/<slug>/quotes.md`
   - `dist/analysis/<slug>/proper_nouns.md`
6. Write the outputs to disk and summarize what was generated.

Rules:

- Keep judgment in pi; do not try to replace it with repo-local heuristics.
- Reuse existing prepared artifacts when they already match the requested transcript.
- If something is ambiguous, ask a short clarifying question before writing files.

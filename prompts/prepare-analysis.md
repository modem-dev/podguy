---
description: Prepare deterministic transcript artifacts for pi from a transcript output directory
---

Prepare transcript analysis artifacts for: $@

Workflow:

- Identify the transcript output directory produced by `scripts/transcribe_video.py`.
- Derive a stable episode slug from the argument or transcript directory name. If the slug is ambiguous, ask one brief clarifying question.
- Run:
  `uv run python scripts/prepare_transcript_analysis.py <transcript-dir> --output-dir dist/analysis/<slug> --slug <slug> --plain-output-names`
- Keep outputs under `dist/analysis/<slug>/` unless the user or profile requests a different layout.
- After the script finishes, report the exact output paths that were written.

Rules:

- Do not do editorial analysis in this step.
- Do not invent missing transcript inputs.
- Prefer reusing existing prepared artifacts when they already match the requested transcript and slug.

# podguy project instructions

This repository is primarily operated through `pi` for podcast post-production work.

Default to the `podguy-post-production` workflow unless the user explicitly asks for something else.

## Primary tasks

- scan episode videos for likely interstitials and non-host inserts when video is available
- generate transcripts for draft, preview, or final episode exports
- derive YouTube/podcast chapters in timestamp-title format
- give editorial feedback such as cuts, highlights, weak sections, and insert opportunities
- draft publishing assets such as show notes, quote sheets, and proper noun review

## Podcast profile

- Prefer show-specific settings from `podguy.toml` when present.
- Use `podguy.example.toml` as the template for new shows.
- Do not assume a specific show, hosts, audience, tone, or episode naming convention unless the profile or user provides it.

## Working guidance

- prefer writing generated outputs under `dist/analysis/`
- reuse existing analysis outputs when they already match the requested episode/version
- treat scanner results as heuristic review aids, not exact edit points
- support audio-only files, video drafts, preview exports, and final renders
- skip the visual scanner for audio-only inputs
- use transcript evidence and timecodes whenever possible when giving editorial feedback

## Interaction guidance

- assume the user will speak in natural language, not remember slash commands
- treat prompt templates as optional shortcuts, not required UX knowledge
- if the user asks for something ambiguous like "analyze this" or "review this episode", ask one short clarifying question before deciding how much to generate
- prefer offering simple natural-language choices rather than command names

Default clarification for ambiguous episode requests:
- **quick pass** = optional video scan + transcript + prepared transcript artifacts + short summary
- **full review** = quick pass + chapters + clips + cuts + show notes + quotes + proper noun review

If the user request already clearly asks for one specific deliverable, do that directly instead of asking.

For synthetic or test fixture inputs, default to a leaner evaluation mindset:
- prefer a quick pass unless the user explicitly asks for a full editorial bundle
- treat fixtures as test media, not normal production exports, unless the user says otherwise

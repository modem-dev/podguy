#!/usr/bin/env bash
set -euo pipefail

repo_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$repo_root"

work_dir=$(mktemp -d "${TMPDIR:-/tmp}/podguy-prep-test.XXXXXX")
trap 'rm -rf "$work_dir"' EXIT

if [[ $# -gt 1 ]]; then
  echo "usage: tests/test_prepare_transcript_analysis.sh [fixture-media]" >&2
  exit 1
fi

fixture=${1:-$work_dir/podguy-fixture.mp4}
if [[ $# -eq 0 ]]; then
  scripts/make_test_fixture.sh "$fixture" >/dev/null
elif [[ ! -f "$fixture" ]]; then
  echo "error: fixture not found: $fixture" >&2
  exit 1
fi

transcript_dir="$work_dir/ep005_transcript"
analysis_dir="$work_dir/analysis"
split_dir="$work_dir/analysis_split"

uv run python scripts/transcribe_video.py "$fixture" "$transcript_dir" --backend mock >/dev/null
uv run python scripts/prepare_transcript_analysis.py "$transcript_dir" --output-dir "$analysis_dir" --slug ep005 >/dev/null
uv run python scripts/prepare_transcript_analysis.py \
  "$transcript_dir" \
  --output-dir "$split_dir" \
  --slug ep005_split \
  --max-chunk-segments 1 >/dev/null

for file in \
  "$analysis_dir/ep005_transcript_index.json" \
  "$analysis_dir/ep005_transcript_chunks.md" \
  "$split_dir/ep005_split_transcript_index.json" \
  "$split_dir/ep005_split_transcript_chunks.md"; do
  if [[ ! -f "$file" ]]; then
    echo "error: missing output file: $file" >&2
    exit 1
  fi
done

uv run python - "$analysis_dir" "$split_dir" <<'PY'
import json
import sys
from pathlib import Path

analysis_dir = Path(sys.argv[1])
split_dir = Path(sys.argv[2])

def load(path: Path):
    return json.loads(path.read_text())

def assert_timecode(value: str):
    assert len(value) >= 8 and value[2] == ':' and value[5] == ':', value

def check_markdown(path: Path, chunk_count: int):
    text = path.read_text()
    assert '# Prepared transcript chunks for ' in text
    assert '## Chunk index' in text
    for idx in range(1, chunk_count + 1):
        assert f'## Chunk {idx}' in text

index = load(analysis_dir / 'ep005_transcript_index.json')
assert index['schema_version'] == 1
assert index['slug'] == 'ep005'
assert index['summary']['segment_count'] == 3
assert index['summary']['chunk_count'] == 1
assert index['outputs']['transcript_index_json'].endswith('ep005_transcript_index.json')
assert index['outputs']['transcript_chunks_markdown'].endswith('ep005_transcript_chunks.md')
assert index['segments'][0]['text'] == 'Mock transcript segment one.'
assert_timecode(index['segments'][0]['start_timecode'])
assert_timecode(index['segments'][0]['end_timecode'])
check_markdown(analysis_dir / 'ep005_transcript_chunks.md', 1)

split_index = load(split_dir / 'ep005_split_transcript_index.json')
assert split_index['slug'] == 'ep005_split'
assert split_index['summary']['segment_count'] == 3
assert split_index['summary']['chunk_count'] == 3
assert split_index['chunking']['max_chunk_segments'] == 1
for chunk in split_index['chunks']:
    assert chunk['segment_count'] == 1
check_markdown(split_dir / 'ep005_split_transcript_chunks.md', 3)

pkg = json.loads(Path('package.json').read_text())
assert pkg['pi']['prompts'] == ['./prompts']
for prompt_path in ['prompts/prepare-analysis.md', 'prompts/phase1.md']:
    text = Path(prompt_path).read_text()
    assert text.startswith('---\n')

skill = Path('src/podguy-post-production/SKILL.md').read_text()
for needle in [
    'scripts/prepare_transcript_analysis.py',
    'dist/analysis/<episode>/transcript_chunks.md',
    'dist/analysis/<episode>/transcript_index.json',
    '/prepare-analysis',
    '/phase1',
    '/full-review',
]:
    assert needle in skill, needle

print('prepare transcript analysis assertions passed')
PY

echo "ok: transcript prep smoke test passed"

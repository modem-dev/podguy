#!/usr/bin/env python3
"""
Prepare deterministic transcript artifacts for pi-driven editorial workflows.

Purpose
- Turn transcript outputs into chunked, timecoded artifacts that pi can reason over.
- Keep editorial judgment in pi while this script handles stable formatting and indexing.
- Standardize output names under dist/analysis/.

Usage
  uv run python scripts/prepare_transcript_analysis.py <transcript-dir> [options]

Example
  uv run python scripts/prepare_transcript_analysis.py \
    dist/analysis/005/transcript \
    --output-dir dist/analysis/005 \
    --slug ep005 \
    --plain-output-names

Outputs
- dist/analysis/<episode>/transcript_chunks.md
- dist/analysis/<episode>/transcript_index.json
"""

from __future__ import annotations

import argparse
import json
import math
import re
from pathlib import Path
from typing import Any

DEFAULT_OUTPUT_DIR = "dist/analysis"
DEFAULT_MAX_CHUNK_SECONDS = 300.0
DEFAULT_MAX_CHUNK_CHARS = 3500
DEFAULT_MAX_CHUNK_SEGMENTS = 80


def seconds_to_timecode(seconds: float) -> str:
    total_ms = int(round(seconds * 1000.0))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    m = (total_s // 60) % 60
    h = total_s // 3600
    if ms == 0:
        return f"{h:02d}:{m:02d}:{s:02d}"
    return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"


def duration_to_label(seconds: float) -> str:
    whole_seconds = int(math.floor(seconds + 0.5))
    s = whole_seconds % 60
    m = (whole_seconds // 60) % 60
    h = whole_seconds // 3600
    return f"{h:02d}:{m:02d}:{s:02d}"


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def sanitize_slug(value: str) -> str:
    slug = re.sub(r"[^a-zA-Z0-9]+", "_", value).strip("_").lower()
    if not slug:
        raise SystemExit("could not derive a slug; pass --slug explicitly")
    return slug


def derive_slug(transcript_dir: Path) -> str:
    name = transcript_dir.name
    for suffix in ("_transcript", "-transcript", " transcript"):
        if name.lower().endswith(suffix):
            name = name[: -len(suffix)]
            break
    return sanitize_slug(name)


def load_segments(transcript_dir: Path) -> dict[str, Any]:
    segments_path = transcript_dir / "segments.json"
    if not segments_path.is_file():
        raise SystemExit(f"segments.json not found in transcript dir: {transcript_dir}")
    return json.loads(segments_path.read_text(encoding="utf-8"))


def normalize_segments(raw_segments: list[dict[str, Any]]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for idx, segment in enumerate(raw_segments, start=1):
        start = float(segment.get("start", 0.0))
        end = float(segment.get("end", start))
        text = normalize_text(str(segment.get("text", "")))
        if not text:
            continue
        segments.append(
            {
                "index": idx,
                "start": start,
                "end": end,
                "start_timecode": seconds_to_timecode(start),
                "end_timecode": seconds_to_timecode(end),
                "duration_seconds": round(max(0.0, end - start), 3),
                "text": text,
                "char_count": len(text),
            }
        )
    return segments


def chunk_segments(
    segments: list[dict[str, Any]],
    max_chunk_seconds: float,
    max_chunk_chars: int,
    max_chunk_segments: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []
    current: list[dict[str, Any]] = []

    def flush() -> None:
        if not current:
            return
        start = float(current[0]["start"])
        end = float(current[-1]["end"])
        text = "\n".join(
            f"[{segment['start_timecode']} -> {segment['end_timecode']}] {segment['text']}" for segment in current
        )
        chunks.append(
            {
                "chunk_index": len(chunks) + 1,
                "start": start,
                "end": end,
                "start_timecode": seconds_to_timecode(start),
                "end_timecode": seconds_to_timecode(end),
                "duration_seconds": round(max(0.0, end - start), 3),
                "segment_start_index": int(current[0]["index"]),
                "segment_end_index": int(current[-1]["index"]),
                "segment_count": len(current),
                "char_count": sum(int(segment["char_count"]) for segment in current),
                "text": text,
            }
        )
        current.clear()

    for segment in segments:
        candidate = current + [segment]
        start = float(candidate[0]["start"])
        end = float(candidate[-1]["end"])
        candidate_duration = end - start
        candidate_chars = sum(int(item["char_count"]) for item in candidate)
        candidate_count = len(candidate)

        would_exceed = (
            current
            and (
                candidate_duration > max_chunk_seconds
                or candidate_chars > max_chunk_chars
                or candidate_count > max_chunk_segments
            )
        )
        if would_exceed:
            flush()
        current.append(segment)

    flush()
    return chunks


def build_index(
    transcript_dir: Path,
    slug: str,
    data: dict[str, Any],
    segments: list[dict[str, Any]],
    chunks: list[dict[str, Any]],
    index_path: Path,
    chunks_path: Path,
    max_chunk_seconds: float,
    max_chunk_chars: int,
    max_chunk_segments: int,
) -> dict[str, Any]:
    duration_seconds = max((float(segment["end"]) for segment in segments), default=0.0)
    return {
        "schema_version": 1,
        "slug": slug,
        "source": {
            "transcript_dir": str(transcript_dir),
            "segments_json": str(transcript_dir / "segments.json"),
            "transcript_txt": str(transcript_dir / "transcript.txt"),
            "input_media": data.get("input"),
            "backend": data.get("backend"),
            "model": data.get("model"),
            "language": data.get("language"),
        },
        "outputs": {
            "transcript_chunks_markdown": str(chunks_path),
            "transcript_index_json": str(index_path),
        },
        "chunking": {
            "max_chunk_seconds": max_chunk_seconds,
            "max_chunk_chars": max_chunk_chars,
            "max_chunk_segments": max_chunk_segments,
        },
        "summary": {
            "segment_count": len(segments),
            "chunk_count": len(chunks),
            "duration_seconds": round(duration_seconds, 3),
            "duration_timecode": duration_to_label(duration_seconds),
        },
        "segments": segments,
        "chunks": chunks,
    }


def render_chunks_markdown(index: dict[str, Any]) -> str:
    summary = index["summary"]
    chunking = index["chunking"]
    chunks = index["chunks"]

    lines = [
        f"# Prepared transcript chunks for {index['slug']}",
        "",
        "This file is deterministic prep for pi-driven editorial analysis.",
        "",
        f"- Source transcript dir: `{index['source']['transcript_dir']}`",
        f"- Source segments: `{index['source']['segments_json']}`",
        f"- Backend: `{index['source'].get('backend') or 'unknown'}`",
        f"- Model: `{index['source'].get('model') or 'unknown'}`",
        f"- Language: `{index['source'].get('language') or 'unknown'}`",
        f"- Segment count: {summary['segment_count']}",
        f"- Chunk count: {summary['chunk_count']}",
        f"- Total duration: {summary['duration_timecode']}",
        f"- Chunking: {chunking['max_chunk_seconds']}s / {chunking['max_chunk_chars']} chars / {chunking['max_chunk_segments']} segments max",
        "",
        "## Chunk index",
        "",
    ]

    for chunk in chunks:
        lines.append(
            "- "
            f"Chunk {chunk['chunk_index']} — {chunk['start_timecode']} to {chunk['end_timecode']} "
            f"(segments {chunk['segment_start_index']}-{chunk['segment_end_index']}, {chunk['char_count']} chars)"
        )

    for chunk in chunks:
        lines.extend(
            [
                "",
                f"## Chunk {chunk['chunk_index']}",
                "",
                f"- Time range: {chunk['start_timecode']} → {chunk['end_timecode']}",
                f"- Duration: {duration_to_label(float(chunk['duration_seconds']))}",
                f"- Segments: {chunk['segment_start_index']}-{chunk['segment_end_index']}",
                f"- Segment count: {chunk['segment_count']}",
                f"- Characters: {chunk['char_count']}",
                "",
                chunk["text"],
            ]
        )

    return "\n".join(lines).rstrip() + "\n"


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Prepare deterministic transcript artifacts for pi.")
    parser.add_argument("transcript_dir", help="directory produced by scripts/transcribe_video.py")
    parser.add_argument(
        "--output-dir",
        default=DEFAULT_OUTPUT_DIR,
        help=f"directory to write prepared analysis outputs (default: {DEFAULT_OUTPUT_DIR})",
    )
    parser.add_argument("--slug", help="override the episode slug used in output filenames")
    parser.add_argument(
        "--plain-output-names",
        action="store_true",
        help="write transcript_chunks.md and transcript_index.json instead of slug-prefixed filenames",
    )
    parser.add_argument(
        "--max-chunk-seconds",
        type=float,
        default=DEFAULT_MAX_CHUNK_SECONDS,
        help=f"maximum duration per chunk in seconds (default: {DEFAULT_MAX_CHUNK_SECONDS})",
    )
    parser.add_argument(
        "--max-chunk-chars",
        type=int,
        default=DEFAULT_MAX_CHUNK_CHARS,
        help=f"maximum characters per chunk (default: {DEFAULT_MAX_CHUNK_CHARS})",
    )
    parser.add_argument(
        "--max-chunk-segments",
        type=int,
        default=DEFAULT_MAX_CHUNK_SEGMENTS,
        help=f"maximum segments per chunk (default: {DEFAULT_MAX_CHUNK_SEGMENTS})",
    )
    return parser.parse_args()


def resolve_output_paths(output_dir: Path, slug: str, plain_output_names: bool) -> tuple[Path, Path]:
    if plain_output_names:
        return output_dir / "transcript_index.json", output_dir / "transcript_chunks.md"
    return output_dir / f"{slug}_transcript_index.json", output_dir / f"{slug}_transcript_chunks.md"


def main() -> None:
    args = parse_args()

    transcript_dir = Path(args.transcript_dir)
    if not transcript_dir.is_dir():
        raise SystemExit(f"transcript directory not found: {transcript_dir}")

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    slug = sanitize_slug(args.slug) if args.slug else derive_slug(transcript_dir)
    index_path, chunks_path = resolve_output_paths(output_dir, slug, args.plain_output_names)
    raw_data = load_segments(transcript_dir)
    segments = normalize_segments(list(raw_data.get("segments", [])))
    chunks = chunk_segments(
        segments,
        max_chunk_seconds=args.max_chunk_seconds,
        max_chunk_chars=args.max_chunk_chars,
        max_chunk_segments=args.max_chunk_segments,
    )

    index = build_index(
        transcript_dir=transcript_dir,
        slug=slug,
        data=raw_data,
        segments=segments,
        chunks=chunks,
        index_path=index_path,
        chunks_path=chunks_path,
        max_chunk_seconds=args.max_chunk_seconds,
        max_chunk_chars=args.max_chunk_chars,
        max_chunk_segments=args.max_chunk_segments,
    )

    index_path.write_text(json.dumps(index, indent=2) + "\n", encoding="utf-8")
    chunks_path.write_text(render_chunks_markdown(index), encoding="utf-8")

    print(f"Wrote {index_path}")
    print(f"Wrote {chunks_path}")


if __name__ == "__main__":
    main()

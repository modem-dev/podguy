#!/usr/bin/env python3
"""
Cut clip candidates from podcast/video media using ffmpeg.

Purpose
- Turn pi-generated clip candidates into actual reviewable media files.
- Keep selection/judgment in pi while this script performs deterministic cutting.
- Support original-aspect cuts and simple social formats for Shorts/TikTok review.

Usage
  uv run python scripts/cut_clips.py <input-media> <clips-file> <output-dir> [options]

Examples
  uv run python scripts/cut_clips.py \
    episode-006-draft.mp4 \
    dist/analysis/ep006/clips.md \
    dist/analysis/ep006/clips/cuts

  uv run python scripts/cut_clips.py episode.mp4 clips.md dist/analysis/ep006/shorts \
    --aspect vertical --pad-start 1 --pad-end 1

Inputs
- Markdown or plain text with time ranges such as `00:01:12 - 00:02:03`.
- JSON containing a list of clips, or an object with a `clips` array.
- CSV with start/end columns and an optional title column.

Outputs
- One media file per clip.
- manifest.json with source ranges, output paths, and ffmpeg commands.
"""

from __future__ import annotations

import argparse
import csv
import json
import re
import shlex
import shutil
import subprocess
import sys
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable, Optional

TIME_PATTERN = r"(?:(?:\d{1,2}:)?\d{1,2}:\d{2})(?:[\.,]\d{1,3})?"
RANGE_RE = re.compile(
    rf"(?P<start>{TIME_PATTERN})\s*(?:-->|->|–|—|-|\bto\b)\s*(?P<end>{TIME_PATTERN})",
    re.IGNORECASE,
)
WORD_RE = re.compile(r"[^a-zA-Z0-9]+")

ASPECT_FILTERS = {
    "source": None,
    "vertical": "scale=1080:1920:force_original_aspect_ratio=increase,crop=1080:1920,setsar=1",
    "square": "scale=1080:1080:force_original_aspect_ratio=increase,crop=1080:1080,setsar=1",
    "horizontal": "scale=1920:1080:force_original_aspect_ratio=increase,crop=1920:1080,setsar=1",
}


@dataclass(frozen=True)
class ClipSpec:
    start: float
    end: float
    title: str
    source: str

    @property
    def duration(self) -> float:
        return max(0.0, self.end - self.start)


def parse_timecode(value: str) -> float:
    normalized = value.strip().replace(",", ".")
    parts = normalized.split(":")
    if len(parts) == 2:
        hours = 0
        minutes = int(parts[0])
        seconds = float(parts[1])
    elif len(parts) == 3:
        hours = int(parts[0])
        minutes = int(parts[1])
        seconds = float(parts[2])
    else:
        raise ValueError(f"invalid timecode: {value}")
    return float(hours * 3600 + minutes * 60 + seconds)


def seconds_to_timecode(seconds: float) -> str:
    total_ms = int(round(seconds * 1000.0))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    m = (total_s // 60) % 60
    h = total_s // 3600
    if ms:
        return f"{h:02d}:{m:02d}:{s:02d}.{ms:03d}"
    return f"{h:02d}:{m:02d}:{s:02d}"


def slugify(value: str, fallback: str) -> str:
    slug = WORD_RE.sub("-", value.strip().lower()).strip("-")
    return slug[:80].strip("-") or fallback


def clean_markdown_title(line: str) -> str:
    line = RANGE_RE.sub("", line)
    line = re.sub(r"^[\s#>*-]+", "", line)
    line = re.sub(r"[`*_\[\]()]+", "", line)
    line = re.sub(r"\b(?:start|end|duration)\s*:\s*", "", line, flags=re.IGNORECASE)
    line = re.sub(r"\s+", " ", line).strip(" :-—–\t")
    return line


def first_present(row: dict[str, Any], *keys: str) -> Any:
    for key in keys:
        if key in row and row[key] is not None and row[key] != "":
            return row[key]
    return None


def normalize_clip(start: Any, end: Any, title: Any, source: str) -> Optional[ClipSpec]:
    if start is None or end is None:
        return None
    try:
        start_seconds = parse_timecode(str(start)) if not isinstance(start, (int, float)) else float(start)
        end_seconds = parse_timecode(str(end)) if not isinstance(end, (int, float)) else float(end)
    except (TypeError, ValueError):
        return None
    if end_seconds <= start_seconds:
        return None
    title_text = str(title or "").strip() or f"Clip {seconds_to_timecode(start_seconds)}"
    return ClipSpec(start=start_seconds, end=end_seconds, title=title_text, source=source)


def parse_json_clips(path: Path) -> list[ClipSpec]:
    data = json.loads(path.read_text(encoding="utf-8"))
    rows = data.get("clips", data.get("items", data)) if isinstance(data, dict) else data
    if not isinstance(rows, list):
        raise SystemExit(f"JSON clip file must be a list or contain a clips array: {path}")

    clips: list[ClipSpec] = []
    for index, row in enumerate(rows, start=1):
        if not isinstance(row, dict):
            continue
        clip = normalize_clip(
            first_present(row, "start", "start_timecode", "in"),
            first_present(row, "end", "end_timecode", "out"),
            first_present(row, "title", "name") or f"Clip {index}",
            f"{path}:{index}",
        )
        if clip:
            clips.append(clip)
    return clips


def parse_csv_clips(path: Path) -> list[ClipSpec]:
    clips: list[ClipSpec] = []
    with path.open("r", encoding="utf-8", newline="") as handle:
        reader = csv.DictReader(handle)
        for index, row in enumerate(reader, start=2):
            lower = {key.lower().strip(): value for key, value in row.items() if key}
            clip = normalize_clip(
                first_present(lower, "start", "start_timecode", "in"),
                first_present(lower, "end", "end_timecode", "out"),
                first_present(lower, "title", "name") or f"Clip {index - 1}",
                f"{path}:{index}",
            )
            if clip:
                clips.append(clip)
    return clips


def nearby_heading(lines: list[str], index: int) -> str:
    for previous in range(index - 1, max(-1, index - 8), -1):
        stripped = lines[previous].strip()
        if stripped.startswith("#"):
            return clean_markdown_title(stripped)
        if stripped.startswith(("- ", "* ")) and RANGE_RE.search(stripped) is None:
            cleaned = clean_markdown_title(stripped)
            if cleaned:
                return cleaned
    return ""


def parse_text_clips(path: Path) -> list[ClipSpec]:
    lines = path.read_text(encoding="utf-8").splitlines()
    clips: list[ClipSpec] = []
    for index, line in enumerate(lines):
        for match in RANGE_RE.finditer(line):
            title = clean_markdown_title(line) or nearby_heading(lines, index) or f"Clip {len(clips) + 1}"
            clip = normalize_clip(match.group("start"), match.group("end"), title, f"{path}:{index + 1}")
            if clip:
                clips.append(clip)
    return clips


def parse_clips(path: Path) -> list[ClipSpec]:
    suffix = path.suffix.lower()
    if suffix == ".json":
        clips = parse_json_clips(path)
    elif suffix == ".csv":
        clips = parse_csv_clips(path)
    else:
        clips = parse_text_clips(path)

    deduped: list[ClipSpec] = []
    seen: set[tuple[int, int]] = set()
    for clip in clips:
        key = (int(round(clip.start * 1000)), int(round(clip.end * 1000)))
        if key in seen:
            continue
        seen.add(key)
        deduped.append(clip)
    return deduped


def build_ffmpeg_command(
    ffmpeg: str,
    input_media: Path,
    output_path: Path,
    start: float,
    duration: float,
    aspect: str,
    copy: bool,
) -> list[str]:
    command = [
        ffmpeg,
        "-hide_banner",
        "-loglevel",
        "error",
        "-y",
        "-ss",
        f"{start:.3f}",
        "-i",
        str(input_media),
        "-t",
        f"{duration:.3f}",
    ]

    video_filter = ASPECT_FILTERS[aspect]
    if copy and video_filter is None:
        command.extend(["-c", "copy", "-avoid_negative_ts", "make_zero"])
    else:
        if video_filter:
            command.extend(["-vf", video_filter])
        command.extend(
            [
                "-c:v",
                "libx264",
                "-preset",
                "veryfast",
                "-crf",
                "20",
                "-c:a",
                "aac",
                "-b:a",
                "160k",
                "-movflags",
                "+faststart",
            ]
        )
    command.append(str(output_path))
    return command


def iter_selected_clips(clips: list[ClipSpec], limit: Optional[int]) -> Iterable[tuple[int, ClipSpec]]:
    selected = clips[:limit] if limit is not None else clips
    for index, clip in enumerate(selected, start=1):
        yield index, clip


def write_manifest(manifest: dict[str, Any], output_dir: Path) -> None:
    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(f"wrote manifest: {manifest_path}", file=sys.stderr)


def main() -> int:
    parser = argparse.ArgumentParser(description="Cut social/highlight clip candidates from media using ffmpeg.")
    parser.add_argument("input_media", type=Path, help="Source audio/video file")
    parser.add_argument("clips_file", type=Path, help="Markdown, text, CSV, or JSON clip candidate file")
    parser.add_argument("output_dir", type=Path, help="Directory for generated clip media and manifest.json")
    parser.add_argument("--aspect", choices=sorted(ASPECT_FILTERS), default="source", help="Output framing preset")
    parser.add_argument("--copy", action="store_true", help="Use stream copy when --aspect source; faster but less frame-accurate")
    parser.add_argument("--pad-start", type=float, default=0.0, help="Seconds to include before each clip start")
    parser.add_argument("--pad-end", type=float, default=0.0, help="Seconds to include after each clip end")
    parser.add_argument("--limit", type=int, default=None, help="Cut only the first N parsed clips")
    parser.add_argument("--prefix", default="clip", help="Output filename prefix")
    parser.add_argument("--extension", default="mp4", help="Output file extension, default mp4")
    parser.add_argument("--dry-run", action="store_true", help="Write manifest and print ffmpeg commands without cutting")
    args = parser.parse_args()

    if not args.input_media.is_file():
        raise SystemExit(f"input media not found: {args.input_media}")
    if not args.clips_file.is_file():
        raise SystemExit(f"clips file not found: {args.clips_file}")
    if args.limit is not None and args.limit < 1:
        raise SystemExit("--limit must be >= 1")
    if args.pad_start < 0 or args.pad_end < 0:
        raise SystemExit("padding values must be >= 0")

    clips = parse_clips(args.clips_file)
    if not clips:
        raise SystemExit(f"no valid clip ranges found in: {args.clips_file}")

    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg and not args.dry_run:
        raise SystemExit("ffmpeg not found on PATH; install ffmpeg or use --dry-run")

    args.output_dir.mkdir(parents=True, exist_ok=True)
    manifest: dict[str, Any] = {
        "schema_version": 1,
        "input_media": str(args.input_media),
        "clips_file": str(args.clips_file),
        "output_dir": str(args.output_dir),
        "aspect": args.aspect,
        "copy": bool(args.copy),
        "dry_run": bool(args.dry_run),
        "clips": [],
    }

    for index, clip in iter_selected_clips(clips, args.limit):
        padded_start = max(0.0, clip.start - args.pad_start)
        padded_end = clip.end + args.pad_end
        duration = max(0.0, padded_end - padded_start)
        if duration <= 0:
            continue

        filename = (
            f"{index:02d}-{slugify(clip.title, f'clip-{index}')}-"
            f"{seconds_to_timecode(padded_start).replace(':', '')}-"
            f"{seconds_to_timecode(padded_end).replace(':', '')}.{args.extension.lstrip('.')}"
        )
        output_path = args.output_dir / filename
        command = build_ffmpeg_command(
            ffmpeg or "ffmpeg",
            args.input_media,
            output_path,
            padded_start,
            duration,
            args.aspect,
            args.copy,
        )

        if args.dry_run:
            print(shlex.join(command))
        else:
            try:
                subprocess.run(command, check=True)
            except subprocess.CalledProcessError as error:
                # Record the clips that already succeeded before bailing out.
                write_manifest(manifest, args.output_dir)
                raise SystemExit(
                    f"error: ffmpeg failed for clip {index} ({clip.title}): "
                    f"exit code {error.returncode}"
                )
            print(output_path)

        manifest["clips"].append(
            {
                "index": index,
                "title": clip.title,
                "source": clip.source,
                "start": round(clip.start, 3),
                "end": round(clip.end, 3),
                "start_timecode": seconds_to_timecode(clip.start),
                "end_timecode": seconds_to_timecode(clip.end),
                "padded_start": round(padded_start, 3),
                "padded_end": round(padded_end, 3),
                "padded_start_timecode": seconds_to_timecode(padded_start),
                "padded_end_timecode": seconds_to_timecode(padded_end),
                "duration_seconds": round(duration, 3),
                "output": str(output_path),
                "command": command,
            }
        )

    write_manifest(manifest, args.output_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

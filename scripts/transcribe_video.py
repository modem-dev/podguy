#!/usr/bin/env python3
"""
Transcript extraction tool for local video/audio files.

Purpose
- Provide a repeatable repo-local command for generating transcripts.
- Prefer local Whisper-compatible backends when available.
- Emit stable outputs that can be reused by downstream editing tools.

Usage
  uv run python scripts/transcribe_video.py <input-media> <output-dir> [options]

Example
  uv run --group transcribe-mlx python scripts/transcribe_video.py "episode-006-draft.mp4" dist/analysis/ep006/transcript

Backends
- auto: prefer mlx-whisper, then faster-whisper, then openai-whisper
- mlx-whisper: best fit for Apple Silicon if installed
- faster-whisper: good cross-platform local backend
- whisper: OpenAI Whisper Python package
- mock: deterministic test backend used by the repo smoke test

Outputs
- summary.txt
- segments.json
- transcript.txt
- transcript.srt
- transcript.vtt
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import shutil
import sys
from pathlib import Path
from typing import Any

BACKEND_ORDER = ["mlx-whisper", "faster-whisper", "whisper"]
DEFAULT_MODELS = {
    "mlx-whisper": "mlx-community/whisper-large-v3-turbo",
    "faster-whisper": "large-v3",
    "whisper": "medium",
    "mock": "mock",
}


def eprint(*args: Any) -> None:
    print(*args, file=sys.stderr)


def seconds_to_timecode(seconds: float, decimal_marker: str = ".") -> str:
    total_ms = int(round(seconds * 1000.0))
    ms = total_ms % 1000
    total_s = total_ms // 1000
    s = total_s % 60
    m = (total_s // 60) % 60
    h = total_s // 3600
    return f"{h:02d}:{m:02d}:{s:02d}{decimal_marker}{ms:03d}"


def normalize_text(text: str) -> str:
    return " ".join(text.strip().split())


def backend_available(name: str) -> bool:
    if name == "mock":
        return True
    module_name = {
        "mlx-whisper": "mlx_whisper",
        "faster-whisper": "faster_whisper",
        "whisper": "whisper",
    }.get(name)
    if not module_name:
        return False
    return importlib.util.find_spec(module_name) is not None


def choose_backend(requested: str) -> str:
    if requested != "auto":
        if not backend_available(requested):
            raise SystemExit(
                f"requested backend '{requested}' is not available. Run --list-backends to inspect local support."
            )
        return requested

    for name in BACKEND_ORDER:
        if backend_available(name):
            return name

    raise SystemExit(
        "no transcription backend found.\n"
        "Install one and re-run with the matching dependency group, e.g.:\n"
        "  uv sync --group transcribe-mlx\n"
        "  uv run --group transcribe-mlx python scripts/transcribe_video.py ...\n"
        "(groups: transcribe-mlx for Apple Silicon, transcribe-faster cross-platform, "
        "transcribe-whisper for OpenAI Whisper)\n"
        "Or run the smoke test with --backend mock."
    )


def resolve_language(value: str) -> str | None:
    return None if value == "auto" else value


def normalize_segments(raw_segments: list[Any]) -> list[dict[str, Any]]:
    segments: list[dict[str, Any]] = []
    for item in raw_segments:
        if isinstance(item, dict):
            start = float(item.get("start", 0.0))
            end = float(item.get("end", start))
            text = normalize_text(str(item.get("text", "")))
        else:
            start = float(getattr(item, "start", 0.0))
            end = float(getattr(item, "end", start))
            text = normalize_text(str(getattr(item, "text", "")))
        if not text:
            continue
        segments.append({"start": start, "end": end, "text": text})
    return segments


def transcribe_with_mlx_whisper(input_path: Path, model_name: str, language: str | None) -> dict[str, Any]:
    import mlx_whisper  # type: ignore

    kwargs: dict[str, Any] = {
        "path_or_hf_repo": model_name,
        "verbose": False,
        "word_timestamps": False,
    }
    if language:
        kwargs["language"] = language

    result = mlx_whisper.transcribe(str(input_path), **kwargs)
    segments = normalize_segments(result.get("segments", []))
    text = normalize_text(result.get("text", "") or " ".join(segment["text"] for segment in segments))
    return {
        "language": result.get("language") or language or "unknown",
        "text": text,
        "segments": segments,
    }


def transcribe_with_faster_whisper(
    input_path: Path,
    model_name: str,
    language: str | None,
    device: str,
    compute_type: str,
) -> dict[str, Any]:
    from faster_whisper import WhisperModel  # type: ignore

    model = WhisperModel(model_name, device=device, compute_type=compute_type)
    kwargs: dict[str, Any] = {"word_timestamps": False}
    if language:
        kwargs["language"] = language

    segments_iter, info = model.transcribe(str(input_path), **kwargs)
    segments = normalize_segments(list(segments_iter))
    text = normalize_text(" ".join(segment["text"] for segment in segments))
    return {
        "language": getattr(info, "language", None) or language or "unknown",
        "text": text,
        "segments": segments,
    }


def transcribe_with_whisper(input_path: Path, model_name: str, language: str | None) -> dict[str, Any]:
    if shutil.which("ffmpeg") is None:
        raise SystemExit("whisper backend requires ffmpeg in PATH")

    import whisper  # type: ignore

    model = whisper.load_model(model_name)
    kwargs: dict[str, Any] = {"verbose": False}
    if language:
        kwargs["language"] = language

    result = model.transcribe(str(input_path), **kwargs)
    segments = normalize_segments(result.get("segments", []))
    text = normalize_text(result.get("text", "") or " ".join(segment["text"] for segment in segments))
    return {
        "language": result.get("language") or language or "unknown",
        "text": text,
        "segments": segments,
    }


def transcribe_with_mock(input_path: Path, model_name: str, language: str | None) -> dict[str, Any]:
    del input_path, model_name
    segments = [
        {"start": 0.0, "end": 4.5, "text": "Mock transcript segment one."},
        {"start": 4.5, "end": 9.2, "text": "Mock transcript segment two."},
        {"start": 9.2, "end": 13.8, "text": "Mock transcript segment three."},
    ]
    text = normalize_text(" ".join(segment["text"] for segment in segments))
    return {
        "language": language or "en",
        "text": text,
        "segments": segments,
    }


def transcribe(
    backend: str,
    input_path: Path,
    model_name: str,
    language: str | None,
    device: str,
    compute_type: str,
) -> dict[str, Any]:
    if backend == "mlx-whisper":
        return transcribe_with_mlx_whisper(input_path, model_name, language)
    if backend == "faster-whisper":
        return transcribe_with_faster_whisper(input_path, model_name, language, device, compute_type)
    if backend == "whisper":
        return transcribe_with_whisper(input_path, model_name, language)
    if backend == "mock":
        return transcribe_with_mock(input_path, model_name, language)
    raise SystemExit(f"unsupported backend: {backend}")


def write_transcript_txt(path: Path, segments: list[dict[str, Any]]) -> None:
    lines = []
    for segment in segments:
        start = seconds_to_timecode(float(segment["start"]))
        end = seconds_to_timecode(float(segment["end"]))
        lines.append(f"[{start} --> {end}] {segment['text']}")
    path.write_text("\n\n".join(lines).strip() + "\n", encoding="utf-8")


def write_srt(path: Path, segments: list[dict[str, Any]]) -> None:
    lines = []
    for idx, segment in enumerate(segments, start=1):
        start = seconds_to_timecode(float(segment["start"]), decimal_marker=",")
        end = seconds_to_timecode(float(segment["end"]), decimal_marker=",")
        lines.extend([str(idx), f"{start} --> {end}", segment["text"], ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_vtt(path: Path, segments: list[dict[str, Any]]) -> None:
    lines = ["WEBVTT", ""]
    for segment in segments:
        start = seconds_to_timecode(float(segment["start"]))
        end = seconds_to_timecode(float(segment["end"]))
        lines.extend([f"{start} --> {end}", segment["text"], ""])
    path.write_text("\n".join(lines).rstrip() + "\n", encoding="utf-8")


def write_outputs(
    output_dir: Path,
    input_path: Path,
    backend: str,
    model_name: str,
    language: str | None,
    result: dict[str, Any],
) -> None:
    output_dir.mkdir(parents=True, exist_ok=True)

    segments = result["segments"]
    text = result["text"]
    detected_language = result.get("language") or language or "unknown"
    duration_seconds = max((float(segment["end"]) for segment in segments), default=0.0)

    segments_json = {
        "input": str(input_path),
        "backend": backend,
        "model": model_name,
        "language": detected_language,
        "text": text,
        "segments": segments,
    }
    (output_dir / "segments.json").write_text(json.dumps(segments_json, indent=2) + "\n", encoding="utf-8")

    write_transcript_txt(output_dir / "transcript.txt", segments)
    write_srt(output_dir / "transcript.srt", segments)
    write_vtt(output_dir / "transcript.vtt", segments)

    summary = "\n".join(
        [
            f"Input: {input_path}",
            f"Backend: {backend}",
            f"Model: {model_name}",
            f"Language: {detected_language}",
            f"Segments: {len(segments)}",
            f"Transcript duration: {seconds_to_timecode(duration_seconds)}",
            "Outputs:",
            f"- {output_dir / 'summary.txt'}",
            f"- {output_dir / 'segments.json'}",
            f"- {output_dir / 'transcript.txt'}",
            f"- {output_dir / 'transcript.srt'}",
            f"- {output_dir / 'transcript.vtt'}",
        ]
    )
    (output_dir / "summary.txt").write_text(summary + "\n", encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Extract transcripts from local video/audio files.")
    parser.add_argument("input_media", nargs="?", help="input video/audio file")
    parser.add_argument("output_dir", nargs="?", help="output directory")
    parser.add_argument(
        "--backend",
        choices=["auto", "mlx-whisper", "faster-whisper", "whisper", "mock"],
        default="auto",
        help="transcription backend to use",
    )
    parser.add_argument("--model", help="backend-specific model name")
    parser.add_argument(
        "--language",
        default="en",
        help="language code, or 'auto' to let the backend detect it (default: en)",
    )
    parser.add_argument("--device", default="auto", help="device for faster-whisper (default: auto)")
    parser.add_argument(
        "--compute-type",
        default="default",
        help="compute type for faster-whisper (default: default)",
    )
    parser.add_argument(
        "--list-backends",
        action="store_true",
        help="print locally available backends and exit",
    )
    return parser.parse_args()


def print_backends() -> None:
    print("available transcription backends:")
    for name in ["mlx-whisper", "faster-whisper", "whisper", "mock"]:
        print(f"- {name}: {'yes' if backend_available(name) else 'no'}")


def main() -> None:
    args = parse_args()

    if args.list_backends:
        print_backends()
        return

    if not args.input_media or not args.output_dir:
        raise SystemExit("usage: scripts/transcribe_video.py <input-media> <output-dir> [options]")

    input_path = Path(args.input_media)
    if not input_path.is_file():
        raise SystemExit(f"input file not found: {input_path}")

    output_dir = Path(args.output_dir)
    backend = choose_backend(args.backend)
    model_name = args.model or DEFAULT_MODELS[backend]
    language = resolve_language(args.language)

    eprint(f"Using backend: {backend}")
    eprint(f"Model: {model_name}")

    result = transcribe(
        backend=backend,
        input_path=input_path,
        model_name=model_name,
        language=language,
        device=args.device,
        compute_type=args.compute_type,
    )
    write_outputs(
        output_dir=output_dir,
        input_path=input_path,
        backend=backend,
        model_name=model_name,
        language=language,
        result=result,
    )
    eprint(f"Wrote transcript outputs to {output_dir}")


if __name__ == "__main__":
    main()

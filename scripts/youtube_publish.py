#!/usr/bin/env python3
"""
Publish podcast episodes to YouTube using the YouTube Data API v3.

Purpose
- Turn pi-prepared episode metadata into actual YouTube uploads.
- Keep editorial judgment (titles, descriptions, chapters) in pi while this
  script performs deterministic API calls.
- Default to private uploads so publishing stays a deliberate, reviewable step.

Usage
  uv run --group youtube python scripts/youtube_publish.py <command> [options]

Commands
  auth            Run the one-time OAuth flow and cache a refresh token.
  upload          Upload a video with metadata (resumable, prints progress).
  set-thumbnail   Set a custom thumbnail on an existing video.
  add-to-playlist Add an existing video to a playlist.
  set-caption     Upload an SRT caption track for an existing video.
  status          Show upload/processing status for a video.
  list-uploads    List recent uploads on the authenticated channel.
  update         Update title/description/tags/privacy on an existing video.

Examples
  uv run --group youtube python scripts/youtube_publish.py auth

  uv run --group youtube python scripts/youtube_publish.py upload \
    dist/exports/ep006-final.mp4 \
    --title "Ep 6: Why this market flipped" \
    --description-file dist/analysis/ep006/youtube-description.md \
    --chapters-file dist/analysis/ep006/chapters.md \
    --privacy private

Setup
- Create a Google Cloud project, enable "YouTube Data API v3", and create an
  OAuth client of type "Desktop app".
- Save the downloaded JSON to ~/.config/podguy/youtube/client_secret.json
  (or pass --client-secrets / set PODGUY_YT_CLIENT_SECRETS).
- Run the `auth` command once; the token is cached at
  ~/.config/podguy/youtube/token.json (or --token / PODGUY_YT_TOKEN).

Notes
- Each upload costs 1600 quota units of the default 10000/day quota.
- `--publish-at` requires `--privacy private`; YouTube flips it public itself.
- Videos uploaded through unverified API projects may be locked private until
  the project passes a YouTube API audit; test before relying on scheduling.
"""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import tomllib
from pathlib import Path
from typing import Any, Optional

DEFAULT_CONFIG_DIR = Path.home() / ".config" / "podguy" / "youtube"
DEFAULT_CLIENT_SECRETS = DEFAULT_CONFIG_DIR / "client_secret.json"
DEFAULT_TOKEN = DEFAULT_CONFIG_DIR / "token.json"
PROFILE_CANDIDATES = ("podguy.toml", "podcast.toml")

SCOPES = [
    "https://www.googleapis.com/auth/youtube.upload",
    "https://www.googleapis.com/auth/youtube.force-ssl",
]

CHUNK_SIZE = 8 * 1024 * 1024

PUBLISH_AT_RE = re.compile(r"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(Z|[+-]\d{2}:\d{2})$")

MISSING_DEPS_HINT = (
    "error: google API client libraries are not installed.\n"
    "Run commands through the youtube dependency group:\n"
    "  uv run --group youtube python scripts/youtube_publish.py ..."
)


def fail(message: str) -> "NoReturn":  # noqa: F821 - py39 compat, comment only
    print(message, file=sys.stderr)
    raise SystemExit(1)


# ---------------------------------------------------------------------------
# podguy.toml profile defaults
# ---------------------------------------------------------------------------


def parse_toml_youtube_section(text: str) -> dict[str, Any]:
    """Read the [youtube] table from podguy.toml."""
    try:
        return dict(tomllib.loads(text).get("youtube", {}))
    except tomllib.TOMLDecodeError as error:
        fail(f"error: could not parse profile TOML: {error}")


def load_profile_defaults(profile_path: Optional[str]) -> dict[str, Any]:
    candidates = [Path(profile_path)] if profile_path else [Path(name) for name in PROFILE_CANDIDATES]
    for candidate in candidates:
        if candidate.is_file():
            return parse_toml_youtube_section(candidate.read_text(encoding="utf-8"))
    if profile_path:
        fail(f"error: profile not found: {profile_path}")
    return {}


# ---------------------------------------------------------------------------
# Auth and service construction
# ---------------------------------------------------------------------------


def resolve_auth_paths(args: argparse.Namespace) -> tuple[Path, Path]:
    client_secrets = Path(
        args.client_secrets
        or os.environ.get("PODGUY_YT_CLIENT_SECRETS")
        or DEFAULT_CLIENT_SECRETS
    )
    token = Path(args.token or os.environ.get("PODGUY_YT_TOKEN") or DEFAULT_TOKEN)
    return client_secrets, token


def run_auth_flow(client_secrets: Path, token: Path) -> None:
    try:
        from google_auth_oauthlib.flow import InstalledAppFlow
    except ImportError:
        fail(MISSING_DEPS_HINT)

    if not client_secrets.is_file():
        fail(
            f"error: OAuth client secrets not found: {client_secrets}\n"
            "Create a Desktop-app OAuth client in Google Cloud Console "
            "(APIs & Services > Credentials) with the YouTube Data API v3 "
            "enabled, download the JSON, and save it to that path."
        )

    flow = InstalledAppFlow.from_client_secrets_file(str(client_secrets), SCOPES)
    creds = flow.run_local_server(port=0, prompt="consent")

    token.parent.mkdir(parents=True, exist_ok=True)
    token.write_text(creds.to_json(), encoding="utf-8")
    token.chmod(0o600)
    print(f"ok: token saved to {token}")


def build_service(args: argparse.Namespace):
    try:
        from google.auth.transport.requests import Request
        from google.oauth2.credentials import Credentials
        from googleapiclient.discovery import build
    except ImportError:
        fail(MISSING_DEPS_HINT)

    client_secrets, token = resolve_auth_paths(args)
    if not token.is_file():
        fail(
            f"error: no cached token at {token}\n"
            "Run the auth command first:\n"
            "  uv run --group youtube python scripts/youtube_publish.py auth"
        )

    creds = Credentials.from_authorized_user_file(str(token), SCOPES)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        token.write_text(creds.to_json(), encoding="utf-8")
        token.chmod(0o600)
    if not creds.valid:
        fail(f"error: cached token at {token} is invalid; re-run the auth command")

    return build("youtube", "v3", credentials=creds, cache_discovery=False)


def api_error_message(error: Exception) -> str:
    text = str(error)
    if "quotaExceeded" in text:
        return (
            "error: YouTube API daily quota exceeded (uploads cost 1600 of "
            "10000 default units). Try again after the quota resets at "
            "midnight Pacific time.\n" + text
        )
    return f"error: YouTube API request failed:\n{text}"


# ---------------------------------------------------------------------------
# Metadata assembly
# ---------------------------------------------------------------------------


def read_text_file(path: str, label: str) -> str:
    file_path = Path(path)
    if not file_path.is_file():
        fail(f"error: {label} not found: {path}")
    return file_path.read_text(encoding="utf-8").strip()


def compose_description(args: argparse.Namespace, profile: dict[str, Any]) -> str:
    parts: list[str] = []
    if args.description:
        parts.append(args.description.strip())
    if args.description_file:
        parts.append(read_text_file(args.description_file, "description file"))
    if args.chapters_file:
        chapters = read_text_file(args.chapters_file, "chapters file")
        if chapters:
            parts.append("Chapters:\n" + chapters)
    footer = profile.get("description_footer", "")
    if isinstance(footer, str) and footer.strip():
        parts.append(footer.strip())
    description = "\n\n".join(part for part in parts if part)
    if len(description) > 5000:
        fail(f"error: composed description is {len(description)} characters; YouTube allows 5000")
    return description


def resolve_tags(args: argparse.Namespace, profile: dict[str, Any]) -> list[str]:
    if args.tags is not None:
        return [tag.strip() for tag in args.tags.split(",") if tag.strip()]
    default_tags = profile.get("default_tags", [])
    if isinstance(default_tags, list):
        return [str(tag) for tag in default_tags]
    return []


def build_upload_body(args: argparse.Namespace, profile: dict[str, Any]) -> dict[str, Any]:
    privacy = args.privacy or profile.get("default_privacy") or "private"
    if privacy not in ("private", "unlisted", "public"):
        fail(f"error: invalid privacy: {privacy}")

    if args.publish_at:
        if not PUBLISH_AT_RE.match(args.publish_at):
            fail(
                "error: --publish-at must be RFC3339, e.g. 2026-06-20T16:00:00Z "
                "or 2026-06-20T09:00:00-07:00"
            )
        if privacy != "private":
            fail("error: --publish-at requires --privacy private (YouTube flips it public)")

    status: dict[str, Any] = {
        "privacyStatus": privacy,
        "selfDeclaredMadeForKids": bool(args.made_for_kids or profile.get("made_for_kids", False)),
    }
    if args.publish_at:
        status["publishAt"] = args.publish_at

    snippet: dict[str, Any] = {
        "title": args.title,
        "description": compose_description(args, profile),
        "categoryId": str(args.category or profile.get("default_category") or "22"),
    }
    tags = resolve_tags(args, profile)
    if tags:
        snippet["tags"] = tags

    return {"snippet": snippet, "status": status}


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------


def cmd_auth(args: argparse.Namespace) -> int:
    client_secrets, token = resolve_auth_paths(args)
    run_auth_flow(client_secrets, token)
    return 0


def cmd_upload(args: argparse.Namespace) -> int:
    media_path = Path(args.media)
    if not media_path.is_file():
        fail(f"error: media file not found: {args.media}")
    if len(args.title) > 100:
        fail(f"error: title is {len(args.title)} characters; YouTube allows 100")

    profile = load_profile_defaults(args.profile)
    body = build_upload_body(args, profile)

    if args.dry_run:
        print(json.dumps({"media": str(media_path), "body": body}, indent=2))
        return 0

    try:
        from googleapiclient.errors import HttpError
        from googleapiclient.http import MediaFileUpload
    except ImportError:
        fail(MISSING_DEPS_HINT)

    service = build_service(args)
    media = MediaFileUpload(str(media_path), chunksize=CHUNK_SIZE, resumable=True)
    request = service.videos().insert(part="snippet,status", body=body, media_body=media)

    print(f"uploading {media_path} ({media_path.stat().st_size / (1024 * 1024):.1f} MiB)...")
    response = None
    try:
        while response is None:
            progress, response = request.next_chunk()
            percent = 100 if response is not None else int(progress.progress() * 100)
            print(f"  {percent}%", flush=True)
    except HttpError as error:
        fail(api_error_message(error))

    video_id = response["id"]
    print(f"ok: uploaded video {video_id}")
    print(f"  https://studio.youtube.com/video/{video_id}/edit")

    playlist_id = str(args.playlist_id or profile.get("playlist_id") or "").strip()
    if playlist_id:
        add_video_to_playlist(service, playlist_id, video_id)
    if args.thumbnail:
        set_video_thumbnail(service, video_id, args.thumbnail)
    if args.caption:
        insert_caption(service, video_id, args.caption, args.caption_language)

    if args.json:
        print(json.dumps({"video_id": video_id, "body": body}, indent=2))
    return 0


def add_video_to_playlist(service, playlist_id: str, video_id: str) -> None:
    from googleapiclient.errors import HttpError

    body = {
        "snippet": {
            "playlistId": playlist_id,
            "resourceId": {"kind": "youtube#video", "videoId": video_id},
        }
    }
    try:
        service.playlistItems().insert(part="snippet", body=body).execute()
        print(f"ok: added {video_id} to playlist {playlist_id}")
    except HttpError as error:
        fail(f"failed to add {video_id} to playlist {playlist_id}:\n{api_error_message(error)}")


def set_video_thumbnail(service, video_id: str, thumbnail: str) -> None:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    thumb_path = Path(thumbnail)
    if not thumb_path.is_file():
        fail(f"error: thumbnail not found: {thumbnail}")
    try:
        service.thumbnails().set(
            videoId=video_id, media_body=MediaFileUpload(str(thumb_path))
        ).execute()
        print(f"ok: thumbnail set on {video_id}")
    except HttpError as error:
        fail(f"failed to set thumbnail on {video_id}:\n{api_error_message(error)}")


def insert_caption(service, video_id: str, caption: str, language: str) -> None:
    from googleapiclient.errors import HttpError
    from googleapiclient.http import MediaFileUpload

    caption_path = Path(caption)
    if not caption_path.is_file():
        fail(f"error: caption file not found: {caption}")
    body = {
        "snippet": {
            "videoId": video_id,
            "language": language,
            "name": "",
        }
    }
    try:
        service.captions().insert(
            part="snippet", body=body, media_body=MediaFileUpload(str(caption_path))
        ).execute()
        print(f"ok: caption track ({language}) uploaded for {video_id}")
    except HttpError as error:
        fail(f"failed to upload caption for {video_id}:\n{api_error_message(error)}")


def cmd_set_thumbnail(args: argparse.Namespace) -> int:
    set_video_thumbnail(build_service(args), args.video_id, args.thumbnail)
    return 0


def cmd_add_to_playlist(args: argparse.Namespace) -> int:
    add_video_to_playlist(build_service(args), args.playlist_id, args.video_id)
    return 0


def cmd_set_caption(args: argparse.Namespace) -> int:
    insert_caption(build_service(args), args.video_id, args.caption, args.caption_language)
    return 0


def cmd_status(args: argparse.Namespace) -> int:
    from googleapiclient.errors import HttpError

    service = build_service(args)
    try:
        response = (
            service.videos()
            .list(part="snippet,status,processingDetails", id=args.video_id)
            .execute()
        )
    except HttpError as error:
        fail(api_error_message(error))

    items = response.get("items", [])
    if not items:
        fail(f"error: video not found: {args.video_id}")
    video = items[0]
    summary = {
        "video_id": video["id"],
        "title": video["snippet"]["title"],
        "privacy": video["status"].get("privacyStatus"),
        "publish_at": video["status"].get("publishAt"),
        "upload_status": video["status"].get("uploadStatus"),
        "processing": video.get("processingDetails", {}).get("processingStatus"),
    }
    print(json.dumps(summary, indent=2))
    return 0


def cmd_list_uploads(args: argparse.Namespace) -> int:
    from googleapiclient.errors import HttpError

    service = build_service(args)
    try:
        channels = service.channels().list(part="contentDetails", mine=True).execute()
        items = channels.get("items", [])
        if not items:
            fail("error: no channel found for the authenticated account")
        uploads_playlist = items[0]["contentDetails"]["relatedPlaylists"]["uploads"]
        playlist_items = (
            service.playlistItems()
            .list(part="snippet,status", playlistId=uploads_playlist, maxResults=args.limit)
            .execute()
        )
    except HttpError as error:
        fail(api_error_message(error))

    rows = [
        {
            "video_id": item["snippet"]["resourceId"]["videoId"],
            "title": item["snippet"]["title"],
            "published_at": item["snippet"].get("publishedAt"),
            "privacy": item.get("status", {}).get("privacyStatus"),
        }
        for item in playlist_items.get("items", [])
    ]
    print(json.dumps(rows, indent=2))
    return 0


def cmd_update(args: argparse.Namespace) -> int:
    from googleapiclient.errors import HttpError

    if not any([args.title, args.description, args.description_file, args.tags, args.privacy]):
        fail("error: nothing to update; pass --title/--description/--description-file/--tags/--privacy")

    service = build_service(args)
    try:
        response = service.videos().list(part="snippet,status", id=args.video_id).execute()
    except HttpError as error:
        fail(api_error_message(error))
    items = response.get("items", [])
    if not items:
        fail(f"error: video not found: {args.video_id}")
    video = items[0]

    snippet = video["snippet"]
    if args.title:
        snippet["title"] = args.title
    if args.description:
        snippet["description"] = args.description
    if args.description_file:
        snippet["description"] = read_text_file(args.description_file, "description file")
    if args.tags is not None:
        snippet["tags"] = [tag.strip() for tag in args.tags.split(",") if tag.strip()]

    description = snippet.get("description", "")
    # Only validate length when this update changes the description; existing
    # Studio-edited descriptions can legitimately exceed the API limit.
    if (args.description or args.description_file) and len(description) > 5000:
        fail(f"error: description is {len(description)} characters; YouTube allows 5000")

    # videos.update clears writable snippet fields that are omitted, so carry
    # everything forward, including defaultLanguage when set.
    update_snippet: dict[str, Any] = {
        "title": snippet["title"],
        "description": description,
        "categoryId": snippet["categoryId"],
        "tags": snippet.get("tags", []),
    }
    if snippet.get("defaultLanguage"):
        update_snippet["defaultLanguage"] = snippet["defaultLanguage"]

    body: dict[str, Any] = {"id": args.video_id, "snippet": update_snippet}
    parts = "snippet"
    if args.privacy:
        if args.privacy not in ("private", "unlisted", "public"):
            fail(f"error: invalid privacy: {args.privacy}")
        body["status"] = {
            "privacyStatus": args.privacy,
            "selfDeclaredMadeForKids": video["status"].get("selfDeclaredMadeForKids", False),
        }
        parts = "snippet,status"

    try:
        service.videos().update(part=parts, body=body).execute()
    except HttpError as error:
        fail(api_error_message(error))
    print(f"ok: updated {args.video_id}")
    return 0


# ---------------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------------


def add_auth_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--client-secrets",
        help=f"OAuth client secrets JSON (default: {DEFAULT_CLIENT_SECRETS})",
    )
    parser.add_argument("--token", help=f"cached OAuth token path (default: {DEFAULT_TOKEN})")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Publish podcast episodes to YouTube via the YouTube Data API v3."
    )
    subparsers = parser.add_subparsers(dest="command", required=True)

    auth = subparsers.add_parser("auth", help="run the one-time OAuth flow")
    add_auth_arguments(auth)
    auth.set_defaults(handler=cmd_auth)

    upload = subparsers.add_parser("upload", help="upload a video with metadata")
    upload.add_argument("media", help="path to the episode video file")
    upload.add_argument("--title", required=True, help="video title (max 100 characters)")
    upload.add_argument("--description", help="inline description text")
    upload.add_argument("--description-file", help="file containing the description body")
    upload.add_argument(
        "--chapters-file",
        help="file with `00:00 Title` chapter lines, appended to the description",
    )
    upload.add_argument("--tags", help="comma-separated tags (overrides profile default_tags)")
    upload.add_argument("--category", help="YouTube category id (default: profile or 22)")
    upload.add_argument(
        "--privacy",
        choices=["private", "unlisted", "public"],
        help="privacy status (default: profile default_privacy or private)",
    )
    upload.add_argument(
        "--publish-at",
        help="RFC3339 scheduled publish time; requires --privacy private",
    )
    upload.add_argument("--playlist-id", help="playlist to add the upload to")
    upload.add_argument("--thumbnail", help="image file to set as the thumbnail")
    upload.add_argument("--caption", help="SRT caption file to upload")
    upload.add_argument("--caption-language", default="en", help="caption language (default: en)")
    upload.add_argument(
        "--made-for-kids", action="store_true", help="declare the video as made for kids"
    )
    upload.add_argument("--profile", help="path to podguy.toml (default: auto-detect)")
    upload.add_argument(
        "--dry-run", action="store_true", help="print the request body without uploading"
    )
    upload.add_argument("--json", action="store_true", help="print the result as JSON")
    add_auth_arguments(upload)
    upload.set_defaults(handler=cmd_upload)

    thumbnail = subparsers.add_parser("set-thumbnail", help="set a thumbnail on a video")
    thumbnail.add_argument("video_id")
    thumbnail.add_argument("thumbnail", help="image file (JPEG/PNG, max 2MB)")
    add_auth_arguments(thumbnail)
    thumbnail.set_defaults(handler=cmd_set_thumbnail)

    playlist = subparsers.add_parser("add-to-playlist", help="add a video to a playlist")
    playlist.add_argument("video_id")
    playlist.add_argument("playlist_id")
    add_auth_arguments(playlist)
    playlist.set_defaults(handler=cmd_add_to_playlist)

    caption = subparsers.add_parser("set-caption", help="upload an SRT caption track")
    caption.add_argument("video_id")
    caption.add_argument("caption", help="SRT caption file")
    caption.add_argument("--caption-language", default="en", help="caption language (default: en)")
    add_auth_arguments(caption)
    caption.set_defaults(handler=cmd_set_caption)

    status = subparsers.add_parser("status", help="show upload/processing status")
    status.add_argument("video_id")
    add_auth_arguments(status)
    status.set_defaults(handler=cmd_status)

    list_uploads = subparsers.add_parser("list-uploads", help="list recent channel uploads")
    list_uploads.add_argument("--limit", type=int, default=10, help="max results (default: 10)")
    add_auth_arguments(list_uploads)
    list_uploads.set_defaults(handler=cmd_list_uploads)

    update = subparsers.add_parser("update", help="update metadata on an existing video")
    update.add_argument("video_id")
    update.add_argument("--title")
    update.add_argument("--description")
    update.add_argument(
        "--description-file",
        help="file with the full description (unlike upload, no chapters/footer composition)",
    )
    update.add_argument("--tags", help="comma-separated tags")
    update.add_argument("--privacy", choices=["private", "unlisted", "public"])
    add_auth_arguments(update)
    update.set_defaults(handler=cmd_update)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    args = build_parser().parse_args(argv)
    return args.handler(args)


if __name__ == "__main__":
    raise SystemExit(main())

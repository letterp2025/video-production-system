"""Shared paths, limits, errors, and atomic JSON helpers for the local workbench."""

from __future__ import annotations

import hashlib
import json
import os
import re
import tempfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import generate_narration as narration


TOOL_DIR = Path(__file__).resolve().parent
REPOSITORY_ROOT = TOOL_DIR.parents[1]
STATIC_DIR = TOOL_DIR / "workbench_static"
AI_GUIDE_PATH = TOOL_DIR / "ai_guide.json"
AI_SCHEMA_PATH = TOOL_DIR / "ai_suggestion.schema.json"
VISUAL_ANIMATIONS_DIR = REPOSITORY_ROOT / "libraries" / "visual_animations_library"
MAX_REQUEST_BYTES = 128_000
MAX_NOTE_CHARS = 6_000
MAX_TEXT_CHARS = 24_000
MAX_TITLE_CHARS = 160
MAX_VISUAL_PLAN_BYTES = 1_000_000
MAX_TTS_VALUES = set(narration.TTS_PARAMETER_DEFAULTS)
MAX_RESPONSE_CHARS = 12_000
MAX_WORK_STATE_BYTES = 5_000_000


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def text_hash(value: str) -> str:
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


class WorkbenchError(Exception):
    def __init__(self, message: str, status: int = 400):
        super().__init__(message)
        self.status = status


def atomic_write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def atomic_create_json(path: Path, value: Any) -> None:
    """Atomically create JSON without replacing a file another writer created."""
    if path.parent.is_symlink() or not path.parent.is_dir():
        raise OSError("The visual plan folder is unavailable or unsafe.")
    temp_path: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", newline="\n", dir=path.parent,
            prefix=f".{path.name}.", suffix=".tmp", delete=False,
        ) as stream:
            temp_path = Path(stream.name)
            json.dump(value, stream, ensure_ascii=False, indent=2)
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.link(temp_path, path)
    finally:
        if temp_path is not None and temp_path.exists():
            temp_path.unlink()


def visual_animation_recipes() -> list[dict[str, str]]:
    """Read recipe IDs and display names from the tracked library catalog."""
    if VISUAL_ANIMATIONS_DIR.is_symlink() or not VISUAL_ANIMATIONS_DIR.is_dir():
        return []
    recipes: list[dict[str, str]] = []
    try:
        entries = sorted(VISUAL_ANIMATIONS_DIR.iterdir(), key=lambda path: path.name.casefold())
    except OSError:
        return []
    for entry in entries:
        if entry.is_symlink() or not entry.is_dir() or not re.fullmatch(r"ANM-[A-Za-z0-9][A-Za-z0-9_-]{0,63}", entry.name):
            continue
        notes = entry / "NOTES.md"
        if notes.is_symlink() or not notes.is_file():
            continue
        try:
            with notes.open("r", encoding="utf-8") as stream:
                heading = stream.readline(4097).strip()
        except (OSError, UnicodeError):
            continue
        match = re.fullmatch(rf"#\s+{re.escape(entry.name)}\s+[—–-]\s+(.+?)\s*", heading)
        title = match.group(1) if match else entry.name.removeprefix("ANM-").replace("-", " ").title()
        if not title.strip() or len(title) > MAX_TITLE_CHARS:
            continue
        recipes.append({"id": entry.name, "title": title})
    return recipes

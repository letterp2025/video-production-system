"""Version-one contracts and path checks for project production-layer JSON."""

from __future__ import annotations

import math
import re
from pathlib import Path, PureWindowsPath
from typing import Any

import generate_narration as narration

from workbench_common import MAX_TEXT_CHARS, MAX_TITLE_CHARS, text_hash


MAX_LAYER_JSON_BYTES = 1_000_000
MAX_LAYER_ENTRIES = 2_000
MAX_CUES = 500
TAKE_ID_PATTERN = re.compile(r"v_layer_[a-z0-9][a-z0-9_-]{0,48}\Z")
REQUEST_ID_PATTERN = re.compile(r"VIS-[0-9]{3,6}\Z")
RENDERERS = {"effectcraft", "manim", "gsap"}
MAPPING_LAYERS = {"music", "sfx"}


def project_relative_path(project_root: Path, value: Any, label: str) -> str:
    """Validate a project-relative path, including existing symlink components."""
    if not isinstance(value, str) or not value.strip() or len(value) > 1_000:
        raise ValueError(f"{label} must be a non-empty project-relative path.")
    normalized = value.replace("\\", "/")
    windows_path = PureWindowsPath(value)
    parts = normalized.split("/")
    if (
        normalized.startswith("/")
        or windows_path.is_absolute()
        or windows_path.drive
        or any(part in {"", ".", ".."} for part in parts)
        or any("\x00" in part or ":" in part for part in parts)
    ):
        raise ValueError(f"{label} must stay inside the video project.")
    root = project_root.resolve(strict=True)
    candidate = root.joinpath(*parts)
    current = root
    for part in parts:
        current = current / part
        if current.is_symlink():
            raise ValueError(f"{label} cannot pass through a symlink.")
    try:
        candidate.resolve(strict=False).relative_to(root)
    except (OSError, ValueError) as exc:
        raise ValueError(f"{label} must stay inside the video project.") from exc
    return "/".join(parts)


def _finite_nonnegative(value: Any, label: str, *, positive: bool = False) -> None:
    if (
        isinstance(value, bool)
        or not isinstance(value, (int, float))
        or not math.isfinite(value)
        or value < 0
        or (positive and value == 0)
    ):
        qualifier = "positive" if positive else "non-negative"
        raise ValueError(f"{label} must be a finite {qualifier} number.")


def validate_visual_take(
    value: Any,
    expected_take_id: str,
    narration_segments: list[dict[str, Any]],
    project_root: Path,
) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "take_id", "title", "creative_direction", "segments",
    }:
        raise ValueError("A visual take must contain schema_version, take_id, title, creative_direction, and segments.")
    if value.get("schema_version") != 1 or isinstance(value.get("schema_version"), bool):
        raise ValueError("The visual take schema version is unsupported.")
    if value.get("take_id") != expected_take_id or not TAKE_ID_PATTERN.fullmatch(expected_take_id):
        raise ValueError("The visual take ID does not match its filename or is invalid.")
    title = value.get("title")
    direction = value.get("creative_direction")
    if not isinstance(title, str) or not title.strip() or len(title) > MAX_TITLE_CHARS:
        raise ValueError("The visual take title is invalid.")
    if not isinstance(direction, str) or not direction.strip() or len(direction) > MAX_TEXT_CHARS:
        raise ValueError("The visual take creative direction is invalid.")
    segments = value.get("segments")
    if not isinstance(segments, dict) or len(segments) > MAX_LAYER_ENTRIES:
        raise ValueError("Visual take segments must be a JSON object with a supported number of entries.")
    known_ids = {segment["id"] for segment in narration_segments}
    for segment_id, entry in segments.items():
        if not isinstance(segment_id, str) or not narration.ID_PATTERN.fullmatch(segment_id):
            raise ValueError("A visual take contains an invalid narration segment ID.")
        if segment_id not in known_ids:
            raise ValueError(f"Visual take references unknown narration segment {segment_id}.")
        if not isinstance(entry, dict) or not {
            "visual_intent", "source_text_sha256", "renderer", "implementation", "library_reference",
        }.issubset(entry) or not set(entry).issubset({
            "visual_intent", "source_text_sha256", "renderer", "implementation", "library_reference",
            "request_ids", "selected_request_id",
        }):
            raise ValueError(f"Visual entry {segment_id} has invalid fields.")
        request_ids = entry.get("request_ids", [])
        selected_request_id = entry.get("selected_request_id")
        if (not isinstance(request_ids, list) or len(request_ids) > 500
            or any(not isinstance(item, str) or not REQUEST_ID_PATTERN.fullmatch(item) for item in request_ids)
            or len(set(request_ids)) != len(request_ids)
            or (selected_request_id is not None and selected_request_id not in request_ids)):
            raise ValueError(f"Visual request selection for {segment_id} is invalid.")
        intent = entry.get("visual_intent")
        if not isinstance(intent, str) or len(intent) > MAX_TEXT_CHARS:
            raise ValueError(f"Visual intent for {segment_id} is invalid.")
        digest = entry.get("source_text_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise ValueError(f"Visual source-text hash for {segment_id} is invalid.")
        renderer = entry.get("renderer")
        if renderer is not None and (not isinstance(renderer, str) or renderer not in RENDERERS):
            raise ValueError(f"Visual renderer for {segment_id} must be effectcraft, manim, gsap, or null.")
        implementation = entry.get("implementation")
        if implementation is not None:
            if not isinstance(implementation, dict) or set(implementation) != {"folder", "entry_file"}:
                raise ValueError(f"Visual implementation for {segment_id} must contain folder and entry_file.")
            folder = project_relative_path(project_root, implementation["folder"], "Visual implementation folder")
            entry_file = project_relative_path(project_root, implementation["entry_file"], "Visual entry file")
            if not entry_file.startswith(folder.rstrip("/") + "/"):
                raise ValueError(f"Visual entry file for {segment_id} must be inside its implementation folder.")
            if renderer is None:
                raise ValueError(f"Choose a renderer for {segment_id} when an implementation is specified.")
        library_reference = entry.get("library_reference")
        if library_reference is not None:
            if not isinstance(library_reference, dict) or set(library_reference) != {"library", "entry_id"}:
                raise ValueError(f"Library reference for {segment_id} is invalid.")
            if not all(
                isinstance(library_reference.get(key), str)
                and library_reference[key].strip()
                and len(library_reference[key]) <= limit
                for key, limit in (("library", 120), ("entry_id", 160))
            ):
                raise ValueError(f"Library reference for {segment_id} is invalid.")
    return value


def visual_segment_status(entry: dict[str, Any] | None, segment: dict[str, Any], project_root: Path) -> str:
    if entry is None:
        return "pending"
    if entry["source_text_sha256"] != text_hash(segment["text"]):
        return "needs_review"
    if entry.get("selected_request_id"):
        return "saved"
    if not entry["visual_intent"].strip():
        return "pending"
    implementation = entry["implementation"]
    if implementation is None:
        return "pending"
    folder = project_root.joinpath(*implementation["folder"].split("/"))
    entry_file = project_root.joinpath(*implementation["entry_file"].split("/"))
    if folder.is_symlink() or entry_file.is_symlink():
        return "invalid"
    if not folder.is_dir() or not entry_file.is_file():
        return "missing"
    return "saved"


def validate_audio_mapping(value: Any, expected_layer: str, expected_segment_id: str, project_root: Path) -> dict[str, Any]:
    if expected_layer not in MAPPING_LAYERS:
        raise ValueError("Unsupported audio mapping layer.")
    if not isinstance(value, dict) or set(value) != {
        "schema_version", "layer", "segment_id", "source_text_sha256", "cues",
    }:
        raise ValueError("An audio mapping must contain schema_version, layer, segment_id, source_text_sha256, and cues.")
    if value.get("schema_version") != 1 or isinstance(value.get("schema_version"), bool):
        raise ValueError("The audio mapping schema version is unsupported.")
    if value.get("layer") != expected_layer or value.get("segment_id") != expected_segment_id:
        raise ValueError("The audio mapping does not match its layer or filename segment ID.")
    digest = value.get("source_text_sha256")
    if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
        raise ValueError("The audio mapping source-text hash is invalid.")
    cues = value.get("cues")
    if not isinstance(cues, list) or len(cues) > MAX_CUES:
        raise ValueError(f"Audio mapping cues must be a list of at most {MAX_CUES} items.")
    for cue in cues:
        if not isinstance(cue, dict) or not {"asset_path", "start_seconds"}.issubset(cue) or not set(cue).issubset({
            "asset_path", "start_seconds", "source_offset_seconds", "duration_seconds", "gain_db",
        }):
            raise ValueError("Each audio cue requires asset_path and start_seconds; other cue fields are optional.")
        project_relative_path(project_root, cue["asset_path"], "Audio cue asset path")
        _finite_nonnegative(cue["start_seconds"], "Audio cue start_seconds")
        if "source_offset_seconds" in cue:
            _finite_nonnegative(cue["source_offset_seconds"], "Audio cue source_offset_seconds")
        if cue.get("duration_seconds") is not None:
            _finite_nonnegative(cue["duration_seconds"], "Audio cue duration_seconds", positive=True)
        if "gain_db" in cue:
            gain = cue["gain_db"]
            if isinstance(gain, bool) or not isinstance(gain, (int, float)) or not math.isfinite(gain) or not -60 <= gain <= 12:
                raise ValueError("Audio cue gain_db must be between -60 and 12 dB.")
    return value

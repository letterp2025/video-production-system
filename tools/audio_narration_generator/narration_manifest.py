"""Manifest schema, names, and speech settings shared by narration commands.

This module has no F5-TTS import, so validation stays lightweight.
"""

from __future__ import annotations

import json
import math
import re
from pathlib import Path
from typing import Any


ID_PATTERN = re.compile(r"^[A-Za-z0-9][A-Za-z0-9_-]{0,31}$")
TAKE_PATTERN = re.compile(r"^(?:[A-Za-z0-9][A-Za-z0-9_-]{0,31}_)?take-(\d{3,})\.wav$")
TAKE_FILE_PATTERN = re.compile(r"^(?:[A-Za-z0-9][A-Za-z0-9_-]{0,31}_)?take-\d{3,}\.(?:wav|json)$")
TAKE_REVIEW_PATTERN = re.compile(r"^take-(\d{3,})$")
INVALID_FILENAME_CHARS = re.compile(r"[^A-Za-z0-9_-]+")
TAKE_REVIEW_RATINGS = {"favorite", "acceptable", "rejected"}
TTS_PARAMETER_DEFAULTS = {
    "speed": 1.0,
    "nfe_step": 32,
    "target_rms": 0.1,
    "cross_fade_duration": 0.15,
    "cfg_strength": 2.0,
    "sway_sampling_coef": -1.0,
    "fix_duration": None,
}


def validate_tts_parameters(values: dict[str, Any], label: str) -> None:
    unknown = set(values) - set(TTS_PARAMETER_DEFAULTS)
    if unknown:
        fail(f"{label} has unsupported F5-TTS parameter(s): " + ", ".join(sorted(unknown)))
    for name, value in values.items():
        if name == "fix_duration" and value is None:
            continue
        if name == "nfe_step":
            if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
                fail(f"{label}.{name} must be a positive integer.")
            continue
        if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value):
            fail(f"{label}.{name} must be a finite number" + (" or null." if name == "fix_duration" else "."))
        if name in {"speed", "fix_duration"} and value <= 0:
            fail(f"{label}.{name} must be greater than zero.")
        if name in {"target_rms", "cross_fade_duration"} and value < 0:
            fail(f"{label}.{name} must be non-negative.")


def fail(message: str) -> None:
    raise ValueError(message)


def load_manifest(path: Path) -> dict[str, Any]:
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        fail(f"Manifest not found: {path}")
    except json.JSONDecodeError as exc:
        fail(f"Invalid JSON in {path}: {exc}")

    if not isinstance(data, dict):
        fail("Manifest root must be a JSON object.")
    project = data.get("project")
    if not isinstance(project, str) or not project.strip() or project in {".", ".."}:
        fail("Manifest must include a simple 'project' name.")
    if not re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9._-]{0,79}", project):
        fail("'project' may contain only letters, numbers, dots, underscores, and hyphens.")

    voice = data.get("voice")
    if not isinstance(voice, dict):
        fail("Manifest must include a 'voice' object.")
    if not isinstance(voice.get("reference_audio"), str) or not voice["reference_audio"].strip():
        fail("voice.reference_audio must be a path to the reference voice audio.")
    if not isinstance(voice.get("reference_text"), str) or not voice["reference_text"].strip():
        fail("voice.reference_text must contain the exact words spoken in the reference audio.")
    voice_styles = data.get("voice_styles", {})
    if not isinstance(voice_styles, dict):
        fail("'voice_styles' must be a JSON object mapping style names to reference recordings.")
    for style_name, style in voice_styles.items():
        if not isinstance(style_name, str) or not ID_PATTERN.fullmatch(style_name):
            fail("Each voice_styles key must be a short stable name using letters, numbers, underscores, or hyphens.")
        if not isinstance(style, dict):
            fail(f"voice_styles.{style_name} must be an object.")
        if not isinstance(style.get("reference_audio"), str) or not style["reference_audio"].strip():
            fail(f"voice_styles.{style_name}.reference_audio must be a path to a style reference recording.")
        if not isinstance(style.get("reference_text"), str) or not style["reference_text"].strip():
            fail(f"voice_styles.{style_name}.reference_text must contain the exact words in that recording.")
        unknown_style_fields = set(style) - {"reference_audio", "reference_text"}
        if unknown_style_fields:
            fail(f"voice_styles.{style_name} has unsupported field(s): " + ", ".join(sorted(unknown_style_fields)))

    segments = data.get("segments")
    if not isinstance(segments, list) or not segments:
        fail("Manifest must contain a non-empty 'segments' list.")
    seen: set[str] = set()
    for index, segment in enumerate(segments, 1):
        if not isinstance(segment, dict):
            fail(f"Segment {index} must be a JSON object.")
        segment_id = segment.get("id")
        if not isinstance(segment_id, str) or not ID_PATTERN.fullmatch(segment_id):
            fail(f"Segment {index} needs a stable descriptive id such as opening-hook.")
        if segment_id in seen:
            fail(f"Duplicate segment id: {segment_id}")
        seen.add(segment_id)
        if "order" in segment:
            fail(f"Segment {segment_id} has an obsolete order field. Move objects in the segments array to change playback order.")
        status = segment.setdefault("status", "active")
        if status == "paused":
            fail(f"Segment {segment_id} uses the retired status 'paused'. Use 'inactive' instead.")
        if status not in {"active", "inactive", "deleted"}:
            fail(f"Segment {segment_id} status must be 'active', 'inactive', or 'deleted'.")
        voice_style = segment.get("voice_style")
        if voice_style is not None and (
            not isinstance(voice_style, str) or voice_style not in voice_styles
        ):
            fail(f"Segment {segment_id} voice_style must name an entry in the top-level voice_styles object.")
        segment_tts = segment.get("tts", {})
        if not isinstance(segment_tts, dict):
            fail(f"Segment {segment_id} tts must be an object of per-segment F5-TTS overrides.")
        validate_tts_parameters(segment_tts, f"segments[{segment_id}].tts")
        if not isinstance(segment.get("text"), str) or not segment["text"].strip():
            fail(f"Segment {segment_id} needs non-empty narration text.")
        take_reviews = segment.get("take_reviews", {})
        if not isinstance(take_reviews, dict):
            fail(f"Segment {segment_id} take_reviews must be an object keyed by take number.")
        for take_key, review in take_reviews.items():
            if not isinstance(take_key, str) or not TAKE_REVIEW_PATTERN.fullmatch(take_key):
                fail(f"Segment {segment_id} take_reviews keys must look like 'take-001'.")
            if not isinstance(review, dict):
                fail(f"Segment {segment_id} take_reviews.{take_key} must be an object.")
            rating = review.get("rating")
            if not isinstance(rating, str) or rating not in TAKE_REVIEW_RATINGS:
                fail(
                    f"Segment {segment_id} take_reviews.{take_key}.rating must be one of: "
                    + ", ".join(sorted(TAKE_REVIEW_RATINGS))
                    + "."
                )
            if set(review) - {"rating", "note"}:
                fail(f"Segment {segment_id} take_reviews.{take_key} supports only 'rating' and optional 'note'.")
            if "note" in review and not isinstance(review["note"], str):
                fail(f"Segment {segment_id} take_reviews.{take_key}.note must be a string.")
        text_hash = segment.get("text_sha256")
        if text_hash is not None and (
            not isinstance(text_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", text_hash)
        ):
            fail(f"Segment {segment_id} text_sha256 must be a lowercase SHA-256 hex digest.")
    settings = data.setdefault("settings", {})
    if not isinstance(settings, dict):
        fail("'settings' must be a JSON object.")
    validate_tts_parameters(
        {key: value for key, value in settings.items() if key in TTS_PARAMETER_DEFAULTS},
        "settings",
    )
    if not isinstance(data.get("selected_takes", {}), dict):
        fail("'selected_takes' must be a JSON object mapping segment ids to take paths.")
    data.setdefault("selected_takes", {})
    if any(not isinstance(value, str) for value in data["selected_takes"].values()):
        fail("Each selected_takes value must be a relative WAV path.")
    segment_ids = {segment["id"] for segment in segments}
    unknown_selected = set(data["selected_takes"]) - segment_ids
    if unknown_selected:
        fail("selected_takes contains unknown segment id(s): " + ", ".join(sorted(unknown_selected)))
    if data.get("project_status", "in_progress") not in {"in_progress", "complete"}:
        fail("project_status must be 'in_progress' or 'complete'.")
    segments_hash = data.get("segments_sha256")
    if segments_hash is not None and (
        not isinstance(segments_hash, str) or not re.fullmatch(r"[0-9a-f]{64}", segments_hash)
    ):
        fail("segments_sha256 must be a lowercase SHA-256 digest or null.")
    if not isinstance(data.get("pruned_takes", []), list):
        fail("pruned_takes must be a JSON array when present.")

    pause_ms = settings.get("pause_ms", 350)
    review_rate = settings.get("review_sample_rate", 48000)
    if not isinstance(pause_ms, int) or pause_ms < 0:
        fail("settings.pause_ms must be a non-negative integer.")
    if not isinstance(review_rate, int) or review_rate < 8000:
        fail("settings.review_sample_rate must be an integer of at least 8000.")
    return data

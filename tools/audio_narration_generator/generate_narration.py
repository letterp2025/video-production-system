"""Generate reviewable F5-TTS narration segments and assemble a master WAV.

Run this with the Python interpreter from the installed F5-TTS environment.
The F5-TTS imports are delayed until generation is requested, so --help,
--dry-run, and --assemble-only do not load the speech model.
"""

from __future__ import annotations

import argparse
import hashlib
import importlib.metadata
import json
import math
import re
import shutil
import subprocess
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Any


TOOL_VERSION = "0.9.0"
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


def safe_slug(value: str, fallback: str) -> str:
    slug = INVALID_FILENAME_CHARS.sub("-", value.strip()).strip("-_")
    return (slug[:48] or fallback).lower()


def segment_text_sha256(segment: dict[str, Any]) -> str:
    """Hash the exact narration string stored in the project manifest."""
    return hashlib.sha256(segment["text"].encode("utf-8")).hexdigest()


def refresh_manifest_text_hashes(data: dict[str, Any]) -> None:
    """Keep the canonical per-segment text hashes in sync with manifest text."""
    for segment in data["segments"]:
        segment["text_sha256"] = segment_text_sha256(segment)


def segments_array_sha256(data: dict[str, Any]) -> str:
    """Hash ordered playback data, excluding tool-owned hashes and take-review notes."""
    normalized = []
    for segment in data["segments"]:
        item = dict(segment)
        item.pop("take_reviews", None)
        item["text_sha256"] = segment_text_sha256(segment)
        normalized.append(item)
    payload = json.dumps(normalized, sort_keys=True, ensure_ascii=False, separators=(",", ":"))
    return hashlib.sha256(payload.encode("utf-8")).hexdigest()


def ordered_segments(data: dict[str, Any]) -> list[dict[str, Any]]:
    """The manifest array position is the narration order."""
    return data["segments"]


def active_segments(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Return only segments included in generation and assembled narration."""
    return [segment for segment in ordered_segments(data) if segment["status"] == "active"]


def retained_takes(data: dict[str, Any]) -> dict[str, str]:
    """Keep selected takes for active and inactive segments during pruning."""
    retained_ids = {segment["id"] for segment in data["segments"] if segment["status"] != "deleted"}
    return {
        segment_id: take
        for segment_id, take in data["selected_takes"].items()
        if segment_id in retained_ids
    }


def segment_folder(audio_root: Path, segment: dict[str, Any]) -> Path:
    title = str(segment.get("title", segment["id"]))
    slug = safe_slug(title, segment["id"].lower())
    return audio_root / "segments" / f"{segment['id']}_{slug}"


def next_take(folder: Path, segment_id: str, data: dict[str, Any]) -> Path:
    numbers = []
    segment_root = folder.parent
    if segment_root.exists():
        for candidate in segment_root.rglob(f"{segment_id}_take-*.wav"):
            if candidate.is_symlink() or not candidate.is_file():
                continue
            match = TAKE_PATTERN.match(candidate.name)
            if match:
                numbers.append(int(match.group(1)))
    segment = next((item for item in data["segments"] if item["id"] == segment_id), None)
    if segment:
        for take_key in segment.get("take_reviews", {}):
            match = TAKE_REVIEW_PATTERN.fullmatch(take_key)
            if match:
                numbers.append(int(match.group(1)))
    for record in data.get("pruned_takes", []):
        if not isinstance(record, dict):
            continue
        if record.get("segment_id") != segment_id:
            continue
        match = TAKE_PATTERN.match(Path(str(record.get("take", ""))).name)
        if match:
            numbers.append(int(match.group(1)))
    return folder / f"{segment_id}_take-{max(numbers, default=0) + 1:03d}.wav"


def relative_audio_path(audio_root: Path, candidate: str) -> Path:
    path = (audio_root / candidate).resolve()
    try:
        path.relative_to(audio_root.resolve())
    except ValueError:
        fail(f"Selected take must stay inside the audio folder: {candidate}")
    return path


def write_json(path: Path, value: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_name(f".{path.name}.tmp")
    temp.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    temp.replace(path)


def resolve_reference_audio(manifest_path: Path, value: str) -> Path:
    path = Path(value)
    if not path.is_absolute():
        path = manifest_path.parent / path
    return path.resolve()


def segment_voice_profile(
    segment: dict[str, Any], data: dict[str, Any],
) -> tuple[str, dict[str, str]]:
    style_name = segment.get("voice_style")
    if style_name is None:
        return "default", data["voice"]
    return style_name, data["voice_styles"][style_name]


def segment_tts_settings(segment: dict[str, Any], data: dict[str, Any]) -> dict[str, Any]:
    overrides = segment.get("tts", {})
    settings = data["settings"]
    return {
        key: overrides.get(key, settings.get(key, default))
        for key, default in TTS_PARAMETER_DEFAULTS.items()
    }


def generation_fingerprint(segment: dict[str, Any], data: dict[str, Any], manifest_path: Path) -> str:
    settings = data["settings"]
    generation_settings = {
        "vocoder_name": settings.get("vocoder_name", "vocos"),
        "checkpoint_file": settings.get("checkpoint_file", "default F5-TTS checkpoint"),
        "model_config": settings.get("model_config", "default F5-TTS config"),
        **segment_tts_settings(segment, data),
    }
    _, voice = segment_voice_profile(segment, data)
    fingerprint_data = {
        "segment_text": segment["text"],
        "reference_audio": str(resolve_reference_audio(manifest_path, voice["reference_audio"])),
        "reference_text": voice["reference_text"],
        "settings": generation_settings,
    }
    encoded = json.dumps(fingerprint_data, sort_keys=True, ensure_ascii=False).encode("utf-8")
    return hashlib.sha256(encoded).hexdigest()


def take_problem(
    segment: dict[str, Any],
    selected: str | None,
    data: dict[str, Any],
    manifest_path: Path,
    audio_root: Path,
) -> str | None:
    if not selected:
        return "no selected take"
    path = relative_audio_path(audio_root, selected)
    if not path.is_file():
        return "selected WAV is missing"
    sidecar = path.with_suffix(".json")
    if not sidecar.is_file():
        return "take receipt is missing"
    try:
        metadata = json.loads(sidecar.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return "take receipt is unreadable"
    if not isinstance(metadata, dict):
        return "take receipt is invalid"
    if metadata.get("segment_id") != segment["id"] or metadata.get("take") != selected:
        return "take receipt identifies another segment or path"
    if metadata.get("text_sha256") != segment_text_sha256(segment):
        return "narration text changed"
    if metadata.get("generation_fingerprint") != generation_fingerprint(segment, data, manifest_path):
        return "voice or speech settings changed"
    return None


def verify_existing_takes(
    data: dict[str, Any],
    manifest_path: Path,
    audio_root: Path,
) -> None:
    for segment in active_segments(data):
        problem = take_problem(segment, data["selected_takes"].get(segment["id"]), data, manifest_path, audio_root)
        if problem:
            fail(f"Selected take for {segment['id']} is not usable ({problem}). Run normally to regenerate it.")


def selected_segments(
    data: dict[str, Any], requested_ids: list[str] | None, manifest_path: Path, audio_root: Path,
) -> tuple[list[dict[str, Any]], dict[str, str]]:
    segments = active_segments(data)
    by_id = {segment["id"]: segment for segment in segments}
    if requested_ids:
        all_segments = {segment["id"]: segment for segment in ordered_segments(data)}
        unknown = sorted(set(requested_ids) - set(all_segments))
        if unknown:
            fail("Unknown segment id(s): " + ", ".join(unknown))
        blocked = sorted(
            segment_id for segment_id in set(requested_ids)
            if all_segments[segment_id]["status"] != "active"
        )
        if blocked:
            details = ", ".join(f"{sid} ({all_segments[sid]['status']})" for sid in blocked)
            fail(f"Cannot audition non-active segment(s): {details}. Set status to 'active' first.")
        chosen = [by_id[segment_id] for segment_id in dict.fromkeys(requested_ids)]
        return chosen, {segment["id"]: "explicit audition" for segment in chosen}

    selected = data["selected_takes"]
    reasons = {
        segment["id"]: problem
        for segment in segments
        if (problem := take_problem(segment, selected.get(segment["id"]), data, manifest_path, audio_root))
    }
    return [segment for segment in segments if segment["id"] in reasons], reasons


def unused_take_files(
    audio_root: Path,
    selected_takes: dict[str, str],
    preserve_segment_ids: set[str] | None = None,
    favorite_takes: set[Path] | None = None,
) -> list[Path]:
    root = audio_root / "segments"
    if not root.is_dir():
        return []
    protected = set()
    for selected in selected_takes.values():
        path = relative_audio_path(audio_root, selected)
        protected.update((path, path.with_suffix(".json")))
    for favorite in favorite_takes or set():
        protected.update((favorite.resolve(), favorite.with_suffix(".json").resolve()))
    unused = []
    for folder in root.iterdir():
        if not folder.is_dir() or folder.is_symlink():
            continue
        if preserve_segment_ids and any(folder.name.startswith(f"{segment_id}_") for segment_id in preserve_segment_ids):
            continue
        for path in folder.iterdir():
            if path.is_file() and not path.is_symlink() and TAKE_FILE_PATTERN.fullmatch(path.name):
                if path.resolve() not in protected:
                    unused.append(path)
    return sorted(unused)


def favorite_take_paths(audio_root: Path, data: dict[str, Any]) -> set[Path]:
    """Return rated favorite WAVs for segments that have not been deleted."""
    root = audio_root / "segments"
    if not root.is_dir():
        return set()
    favorites: set[Path] = set()
    for segment in data["segments"]:
        if segment["status"] == "deleted":
            continue
        reviewed = segment.get("take_reviews", {})
        favorite_keys = {
            key for key, review in reviewed.items()
            if isinstance(review, dict) and review.get("rating") == "favorite"
        }
        if not favorite_keys:
            continue
        for folder in root.iterdir():
            if not folder.is_dir() or folder.is_symlink():
                continue
            for path in folder.iterdir():
                if not path.is_file() or path.is_symlink() or path.suffix.lower() != ".wav":
                    continue
                match = TAKE_PATTERN.match(path.name)
                if not match or f"take-{int(match.group(1)):03d}" not in favorite_keys:
                    continue
                take_key = f"take-{int(match.group(1)):03d}"
                if path.name == f"{segment['id']}_{take_key}.wav":
                    favorites.add(path.resolve())
                    continue
                # Legacy take-NNN filenames have no segment ID; use the sidecar receipt.
                if path.name == f"take-{int(match.group(1)):03d}.wav":
                    sidecar = path.with_suffix(".json")
                    try:
                        receipt = json.loads(sidecar.read_text(encoding="utf-8"))
                    except (json.JSONDecodeError, OSError):
                        receipt = None
                    if isinstance(receipt, dict) and receipt.get("segment_id") == segment["id"]:
                        favorites.add(path.resolve())
    return favorites


def pruned_take_records(
    audio_root: Path, paths: list[Path], run_id: str, data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Capture the take receipt and removed-file details before unlinking files."""
    records: dict[str, dict[str, Any]] = {}
    pruned_at = datetime.now().astimezone().isoformat(timespec="seconds")
    for path in paths:
        take = path.with_suffix(".wav").relative_to(audio_root).as_posix()
        record = records.setdefault(take, {
            "take": take,
            "segment_id": None,
            "pruned_at": pruned_at,
            "run_id": run_id,
            "files": [],
            "receipt": None,
        })
        record["files"].append({
            "path": path.relative_to(audio_root).as_posix(),
            "size_bytes": path.stat().st_size,
        })
        if path.suffix == ".json":
            try:
                receipt = json.loads(path.read_text(encoding="utf-8"))
            except (json.JSONDecodeError, OSError):
                receipt = None
            if isinstance(receipt, dict):
                record["receipt"] = receipt
                record["segment_id"] = receipt.get("segment_id")
    segments_by_id = {segment["id"]: segment for segment in data["segments"]}
    for record in records.values():
        segment = segments_by_id.get(record["segment_id"])
        match = TAKE_PATTERN.match(Path(record["take"]).name)
        if segment and match:
            take_key = f"take-{int(match.group(1)):03d}"
            review = segment.get("take_reviews", {}).get(take_key)
            if review:
                record["take_review"] = dict(review)
    return list(records.values())


def load_f5_engine(settings: dict[str, Any]) -> tuple[Any, Any, Any, str, str]:
    try:
        from cached_path import cached_path
        from importlib.resources import files
        from omegaconf import OmegaConf
        from f5_tts.infer import utils_infer
        from f5_tts.model import DiT
    except ImportError as exc:
        fail(
            "F5-TTS dependencies are missing. Run this script with the Python "
            "interpreter from your installed F5-TTS environment. "
            f"Details: {exc}"
        )

    vocoder_name = settings.get("vocoder_name", "vocos")
    if vocoder_name not in {"vocos", "bigvgan"}:
        fail("settings.vocoder_name must be 'vocos' or 'bigvgan'.")
    if vocoder_name != "vocos":
        fail("This first tool version supports the tested Vocos setup only.")

    config_path = settings.get("model_config")
    if config_path:
        model_config_path = Path(config_path).resolve()
    else:
        model_config_path = Path(str(files("f5_tts").joinpath("configs/F5TTS_Base_train.yaml")))
    model_config = OmegaConf.load(str(model_config_path)).model.arch

    checkpoint = settings.get("checkpoint_file")
    if checkpoint:
        checkpoint_path = Path(checkpoint).resolve()
        if not checkpoint_path.is_file():
            fail(f"F5-TTS checkpoint not found: {checkpoint_path}")
    else:
        checkpoint_path = Path(
            cached_path("hf://SWivid/F5-TTS/F5TTS_Base/model_1200000.safetensors")
        )

    vocoder = utils_infer.load_vocoder(vocoder_name=vocoder_name, is_local=False)
    model = utils_infer.load_model(
        DiT,
        model_config,
        str(checkpoint_path),
        mel_spec_type=vocoder_name,
        vocab_file="",
    )
    try:
        f5_version = importlib.metadata.version("f5-tts")
    except importlib.metadata.PackageNotFoundError:
        f5_version = "unknown"
    return utils_infer, model, vocoder, f5_version, str(checkpoint_path)


def assemble_audio(
    audio_root: Path,
    project: str,
    segments: list[dict[str, Any]],
    selected_takes: dict[str, str],
    pause_ms: int,
    review_sample_rate: int,
    run_id: str,
    ffmpeg_setting: str | None,
) -> tuple[Path, Path | None, int, float]:
    try:
        import numpy as np
        import soundfile as sf
    except ImportError as exc:
        fail(f"Audio assembly requires numpy and soundfile: {exc}")

    waves = []
    sample_rate = None
    selected_details = []
    for segment in segments:
        segment_id = segment["id"]
        selected = selected_takes.get(segment_id)
        if not selected:
            fail(f"No selected take for {segment_id}; generate it first.")
        path = relative_audio_path(audio_root, selected)
        if not path.is_file():
            fail(f"Selected take for {segment_id} is missing: {path}")
        audio, current_rate = sf.read(path, dtype="float32", always_2d=False)
        if getattr(audio, "ndim", 1) != 1:
            fail(f"Expected mono segment audio for {segment_id}: {path}")
        if sample_rate is None:
            sample_rate = int(current_rate)
        elif int(current_rate) != sample_rate:
            fail(f"Sample rate mismatch in {path}: expected {sample_rate}, got {current_rate}")
        waves.append(audio)
        selected_details.append({
            "id": segment_id,
            "take": selected,
            "duration_seconds": round(len(audio) / current_rate, 3),
        })

    if sample_rate is None:
        fail("There are no selected takes to assemble.")
    silence = np.zeros(round(sample_rate * pause_ms / 1000), dtype=np.float32)
    pieces = []
    for index, audio in enumerate(waves):
        pieces.append(audio)
        if index < len(waves) - 1 and len(silence):
            pieces.append(silence)
    combined = np.concatenate(pieces)

    assembled_dir = audio_root / "assembled"
    assembled_dir.mkdir(parents=True, exist_ok=True)
    master = assembled_dir / f"{project}_narration_{run_id}_{sample_rate}hz_mono.wav"
    sf.write(master, combined, sample_rate, subtype="PCM_16")

    ffmpeg = ffmpeg_setting or shutil.which("ffmpeg")
    review = None
    if ffmpeg:
        review = assembled_dir / f"{project}_narration_{run_id}_{review_sample_rate}hz_stereo-review.wav"
        command = [
            ffmpeg, "-hide_banner", "-loglevel", "error", "-y", "-i", str(master),
            "-ar", str(review_sample_rate), "-ac", "2", "-c:a", "pcm_s16le", str(review),
        ]
        subprocess.run(command, check=True, capture_output=True, text=True)
    else:
        print("FFmpeg not found; created the mono master only.", file=sys.stderr)
    return master, review, sample_rate, len(combined) / sample_rate


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Generate separately reviewable F5-TTS narration takes and assemble a full review WAV."
    )
    parser.add_argument("--manifest", required=True, type=Path, help="Project narration JSON manifest.")
    parser.add_argument(
        "--segment", action="append", dest="segments", metavar="ID",
        help="Force a new audition for this segment. Repeat for multiple IDs. Without this flag, stale or missing takes are regenerated.",
    )
    parser.add_argument("--assemble-only", action="store_true", help="Assemble the takes selected in the manifest without generating audio.")
    parser.add_argument("--generate-only", action="store_true", help="Generate the requested takes without assembling the full narration.")
    parser.add_argument("--prune-unused", action="store_true", help="For a completed project, delete unselected segment takes and receipts. Use --dry-run to preview.")
    parser.add_argument("--dry-run", action="store_true", help="Validate and show planned paths without loading F5-TTS.")
    return parser


def main() -> int:
    args = build_parser().parse_args()
    manifest_path = args.manifest.resolve()
    data = load_manifest(manifest_path)
    audio_root = manifest_path.parent.resolve()
    project = data["project"]
    settings = data["settings"]
    run_id = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    if args.assemble_only and args.segments:
        fail("Use either --assemble-only or --segment, not both.")
    if args.assemble_only and args.generate_only:
        fail("Use either --assemble-only or --generate-only, not both.")
    if args.prune_unused and (args.assemble_only or args.generate_only or args.segments):
        fail("Use --prune-unused separately from generation and assembly options.")

    if args.prune_unused:
        if data.get("project_status") != "complete":
            fail("Set project_status to 'complete' in the manifest before pruning unused takes.")
        verify_existing_takes(data, manifest_path, audio_root)
        inactive_ids = {segment["id"] for segment in data["segments"] if segment["status"] == "inactive"}
        favorites = favorite_take_paths(audio_root, data)
        unused = unused_take_files(
            audio_root,
            retained_takes(data),
            preserve_segment_ids=inactive_ids,
            favorite_takes=favorites,
        )
        size = sum(path.stat().st_size for path in unused)
        print(f"Unused take files: {len(unused)} ({size:,} bytes)")
        for path in unused:
            print(f"  {path.relative_to(audio_root)}")
        if args.dry_run:
            print("Dry run only; no files were deleted.")
            return 0
        pruned_records = pruned_take_records(audio_root, unused, run_id, data)
        # Only numbered take WAVs and their receipts under audio/segments are eligible.
        for path in unused:
            path.unlink()
        deleted_ids = {segment["id"] for segment in data["segments"] if segment["status"] == "deleted"}
        for segment_id in deleted_ids:
            data["selected_takes"].pop(segment_id, None)
        if pruned_records:
            data.setdefault("pruned_takes", []).extend(pruned_records)
        if deleted_ids or pruned_records:
            write_json(manifest_path, data)
        for folder in (audio_root / "segments").iterdir():
            if folder.is_dir() and not folder.is_symlink() and not any(folder.iterdir()):
                folder.rmdir()
        run_path = audio_root / "performance" / f"run_{run_id}.json"
        write_json(run_path, {
            "status": "complete", "tool": "audio_narration_generator", "tool_version": TOOL_VERSION,
            "operation": "prune_unused", "project": project,
            "finished_local": datetime.now().astimezone().isoformat(timespec="seconds"),
            "deleted_files": [path.relative_to(audio_root).as_posix() for path in unused],
            "pruned_takes": [record["take"] for record in pruned_records],
            "reclaimed_bytes": size,
        })
        print(f"Prune record: {run_path}")
        return 0

    to_generate, reasons = ([], {}) if args.assemble_only else selected_segments(data, args.segments, manifest_path, audio_root)
    active = active_segments(data)
    inactive = [segment for segment in ordered_segments(data) if segment["status"] == "inactive"]
    deleted = [segment for segment in ordered_segments(data) if segment["status"] == "deleted"]
    current_segments_hash = segments_array_sha256(data)
    segments_changed_since_assembly = data.get("segments_sha256") != current_segments_hash
    if not args.generate_only and not active:
        fail("There are no active segments to assemble. Set at least one segment status to 'active'.")
    print(f"Project: {project}")
    print(f"Audio root: {audio_root}")
    print(f"Segments to generate: {', '.join(item['id'] for item in to_generate) or '(none)'}")
    print(f"Inactive segments: {', '.join(item['id'] for item in inactive) or '(none)'}")
    print(f"Deleted segments: {', '.join(item['id'] for item in deleted) or '(none)'}")
    print(
        "Segment array hash: "
        + ("changed since last assembly" if segments_changed_since_assembly else "matches last assembly")
    )
    for segment in to_generate:
        folder = segment_folder(audio_root, segment)
        output = next_take(folder, segment["id"], data)
        print(f"  {segment['id']} ({reasons[segment['id']]}) -> {output.relative_to(audio_root)}")
    if not args.segments and not args.assemble_only:
        print(f"Unchanged segments: {', '.join(s['id'] for s in active if s['id'] not in reasons) or '(none)'}")
    if args.dry_run:
        if args.assemble_only:
            verify_existing_takes(data, manifest_path, audio_root)
        print("Dry run only; no audio or model files were created.")
        return 0

    # The narration manifest is canonical. Refresh each segment's exact-text
    # hash before validating selected takes against their saved receipts.
    refresh_manifest_text_hashes(data)
    write_json(manifest_path, data)
    if args.assemble_only:
        verify_existing_takes(data, manifest_path, audio_root)

    performance_dir = audio_root / "performance"
    run_path = performance_dir / f"run_{run_id}.json"
    run_record: dict[str, Any] = {
        "status": "running",
        "tool": "audio_narration_generator",
        "tool_version": TOOL_VERSION,
        "project": project,
        "started_local": datetime.now().astimezone().isoformat(timespec="seconds"),
        "f5_tts_version": None,
        "checkpoint": None,
        "reference_audio_name": Path(data["voice"]["reference_audio"]).name,
        "settings": {
            "speed": settings.get("speed", 1.0),
            "pause_ms": settings.get("pause_ms", 350),
            "review_sample_rate": settings.get("review_sample_rate", 48000),
            "vocoder_name": settings.get("vocoder_name", "vocos"),
            "nfe_step": settings.get("nfe_step", 32),
            "target_rms": settings.get("target_rms", 0.1),
            "cross_fade_duration": settings.get("cross_fade_duration", 0.15),
            "cfg_strength": settings.get("cfg_strength", 2.0),
            "sway_sampling_coef": settings.get("sway_sampling_coef", -1.0),
            "fix_duration": settings.get("fix_duration"),
        },
        "generated_segments": [],
        "generation_reasons": reasons,
        "segments_sha256": current_segments_hash,
        "segments_changed_since_last_assembly": segments_changed_since_assembly,
        "skipped_segments": [s["id"] for s in active if s["id"] not in reasons],
        "inactive_segments": [s["id"] for s in inactive],
        "deleted_segments": [s["id"] for s in deleted],
        "assembly": None,
    }
    write_json(run_path, run_record)
    started = time.perf_counter()
    try:
        if to_generate:
            reference_profiles: dict[str, tuple[str, dict[str, str], Path]] = {}
            for segment in to_generate:
                voice_style, voice_profile = segment_voice_profile(segment, data)
                reference_audio = resolve_reference_audio(manifest_path, voice_profile["reference_audio"])
                if not reference_audio.is_file():
                    fail(f"Reference voice audio for {segment['id']} not found: {reference_audio}")
                reference_profiles[segment["id"]] = (voice_style, voice_profile, reference_audio)

            utils_infer, model, vocoder, f5_version, checkpoint_path = load_f5_engine(settings)
            run_record["f5_tts_version"] = f5_version
            run_record["checkpoint"] = checkpoint_path
            write_json(run_path, run_record)
            processed_references: dict[tuple[str, str], tuple[Any, str]] = {}

            for segment in to_generate:
                segment_started = time.perf_counter()
                voice_style, voice_profile, reference_audio = reference_profiles[segment["id"]]
                reference_key = (str(reference_audio), voice_profile["reference_text"])
                if reference_key not in processed_references:
                    processed_references[reference_key] = utils_infer.preprocess_ref_audio_text(
                        str(reference_audio), voice_profile["reference_text"]
                    )
                processed_ref, processed_text = processed_references[reference_key]
                generation_settings = segment_tts_settings(segment, data)
                folder = segment_folder(audio_root, segment)
                folder.mkdir(parents=True, exist_ok=True)
                output_path = next_take(folder, segment["id"], data)
                temp_path = output_path.with_name(f".{output_path.stem}.{run_id}.tmp.wav")
                waveform, sample_rate, _ = utils_infer.infer_process(
                    processed_ref,
                    processed_text,
                    segment["text"].strip(),
                    model,
                    vocoder,
                    mel_spec_type=settings.get("vocoder_name", "vocos"),
                    target_rms=float(generation_settings["target_rms"]),
                    cross_fade_duration=float(generation_settings["cross_fade_duration"]),
                    nfe_step=int(generation_settings["nfe_step"]),
                    cfg_strength=float(generation_settings["cfg_strength"]),
                    sway_sampling_coef=float(generation_settings["sway_sampling_coef"]),
                    speed=float(generation_settings["speed"]),
                    fix_duration=generation_settings["fix_duration"],
                )
                import soundfile as sf

                sf.write(temp_path, waveform, int(sample_rate), subtype="PCM_16")
                temp_path.replace(output_path)
                relative = output_path.relative_to(audio_root).as_posix()
                write_json(output_path.with_suffix(".json"), {
                    "segment_id": segment["id"],
                    "take": relative,
                    "text_sha256": segment_text_sha256(segment),
                    "generation_fingerprint": generation_fingerprint(segment, data, manifest_path),
                    "voice_style": voice_style,
                    "reference_audio_name": reference_audio.name,
                    "generation_settings": generation_settings,
                    "f5_tts_version": f5_version,
                    "checkpoint": checkpoint_path,
                    "sample_rate": int(sample_rate),
                    "duration_seconds": round(len(waveform) / int(sample_rate), 3),
                    "size_bytes": output_path.stat().st_size,
                })
                data["selected_takes"][segment["id"]] = relative
                write_json(manifest_path, data)
                run_record["generated_segments"].append({
                    "id": segment["id"],
                    "take": relative,
                    "voice_style": voice_style,
                    "reference_audio_name": reference_audio.name,
                    "generation_settings": generation_settings,
                    "text_sha256": segment_text_sha256(segment),
                    "duration_seconds": round(len(waveform) / int(sample_rate), 3),
                    "sample_rate": int(sample_rate),
                    "size_bytes": output_path.stat().st_size,
                    "generation_seconds": round(time.perf_counter() - segment_started, 2),
                })
                write_json(run_path, run_record)
                print(f"Saved {relative}")

        if not args.generate_only:
            verify_existing_takes(data, manifest_path, audio_root)
            master, review, sample_rate, duration = assemble_audio(
                audio_root,
                project,
                active,
                data["selected_takes"],
                int(settings.get("pause_ms", 350)),
                int(settings.get("review_sample_rate", 48000)),
                run_id,
                settings.get("ffmpeg_path"),
            )
            run_record["assembly"] = {
                "master_mono": master.relative_to(audio_root).as_posix(),
                "review_stereo": review.relative_to(audio_root).as_posix() if review else None,
                "sample_rate": sample_rate,
                "duration_seconds": round(duration, 3),
                "master_size_bytes": master.stat().st_size,
                "review_size_bytes": review.stat().st_size if review else None,
                "selected_takes": data["selected_takes"].copy(),
            }
            data["segments_sha256"] = segments_array_sha256(data)
            write_json(manifest_path, data)
        run_record["status"] = "complete"
        run_record["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        run_record["finished_local"] = datetime.now().astimezone().isoformat(timespec="seconds")
        write_json(run_path, run_record)
        print(f"Run record: {run_path}")
        return 0
    except Exception as exc:
        run_record["status"] = "failed"
        run_record["elapsed_seconds"] = round(time.perf_counter() - started, 2)
        run_record["error"] = f"{type(exc).__name__}: {exc}"
        run_record["finished_local"] = datetime.now().astimezone().isoformat(timespec="seconds")
        write_json(run_path, run_record)
        print(f"Narration run failed: {type(exc).__name__}: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    try:
        raise SystemExit(main())
    except ValueError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        raise SystemExit(2)

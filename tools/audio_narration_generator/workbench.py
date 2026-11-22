#!/usr/bin/env python3
"""Loopback-only script and narration workbench for one selected project."""

from __future__ import annotations

import argparse
import hashlib
import ipaddress
import json
import mimetypes
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import threading
import uuid
import wave
import unicodedata
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import generate_narration as narration


TOOL_DIR = Path(__file__).resolve().parent
STATIC_DIR = TOOL_DIR / "workbench_static"
AI_GUIDE_PATH = TOOL_DIR / "ai_guide.json"
AI_SCHEMA_PATH = TOOL_DIR / "ai_suggestion.schema.json"
MAX_REQUEST_BYTES = 128_000
MAX_NOTE_CHARS = 6_000
MAX_TEXT_CHARS = 24_000
MAX_TITLE_CHARS = 160
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


class Project:
    """Manifest and its private, project-local work queue."""

    def __init__(self, manifest_path: Path):
        try:
            resolved = manifest_path.expanduser().resolve(strict=True)
        except OSError as exc:
            raise WorkbenchError(f"Cannot open the selected manifest: {exc}") from exc
        if not resolved.is_file() or resolved.name.lower() != "narration_manifest.json":
            raise WorkbenchError("Select the project's narration_manifest.json file.")
        self.manifest_path = resolved
        self.audio_root = resolved.parent
        self.work_dir = self.audio_root / ".workbench"
        self.work_path = self.work_dir / "workbench_state.json"
        self.lock = threading.RLock()
        self.manifest_operation_lock = threading.Lock()
        self._ensure_work_dir()

    def _ensure_work_dir(self) -> None:
        if self.work_dir.exists() and self.work_dir.is_symlink():
            raise WorkbenchError("The audio/.workbench folder cannot be a symlink.")
        try:
            self.work_dir.mkdir(parents=True, exist_ok=True)
            resolved = self.work_dir.resolve(strict=True)
            resolved.relative_to(self.audio_root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise WorkbenchError("The temporary work area must remain inside the selected audio folder.") from exc

    def _read_manifest_bytes(self) -> bytes:
        try:
            return self.manifest_path.read_bytes()
        except OSError as exc:
            raise WorkbenchError(f"Could not read narration_manifest.json: {exc}", 500) from exc

    def read_manifest(self) -> tuple[dict[str, Any], str]:
        raw = self._read_manifest_bytes()
        digest = sha256_bytes(raw)
        try:
            data = narration.load_manifest(self.manifest_path)
        except (ValueError, OSError) as exc:
            raise WorkbenchError(f"Manifest validation failed: {exc}") from exc
        return data, digest

    def read_state(self) -> dict[str, Any]:
        if not self.work_path.exists():
            return {"schema_version": 1, "updated_at": now_iso(), "segments": {}}
        try:
            resolved = self.work_path.resolve(strict=True)
            resolved.relative_to(self.audio_root.resolve(strict=True))
            if resolved.stat().st_size > MAX_WORK_STATE_BYTES:
                raise WorkbenchError("Temporary work state is larger than 5 MB. Move it aside to recover the queue.", 500)
            state = json.loads(resolved.read_text(encoding="utf-8"))
        except (OSError, ValueError, json.JSONDecodeError) as exc:
            raise WorkbenchError(f"Temporary work state is unreadable: {exc}", 500) from exc
        if not isinstance(state, dict) or state.get("schema_version") != 1 or not isinstance(state.get("segments"), dict):
            raise WorkbenchError("Temporary work state has an unsupported format. Move it aside to start a fresh queue.", 500)
        for segment_id, work in state["segments"].items():
            if not isinstance(segment_id, str) or not isinstance(work, dict):
                raise WorkbenchError("Temporary work state contains an invalid segment entry.", 500)
            if not isinstance(work.get("note", ""), str) or not isinstance(work.get("suggestions", []), list):
                raise WorkbenchError(f"Temporary work state for {segment_id} has invalid fields.", 500)
            for suggestion in work.get("suggestions", []):
                suggestion_status = suggestion.get("status") if isinstance(suggestion, dict) else None
                if not isinstance(suggestion, dict) or not isinstance(suggestion_status, str) or suggestion_status not in {"pending", "accepted", "dismissed", "stale"}:
                    raise WorkbenchError(f"Temporary work state for {segment_id} contains an invalid suggestion.", 500)
                if not all(isinstance(suggestion.get(key), str) for key in ("id", "base_text_sha256", "original_text", "proposed_text", "rationale")):
                    raise WorkbenchError(f"Temporary work state for {segment_id} contains an incomplete suggestion.", 500)
        return state

    def write_state(self, state: dict[str, Any]) -> None:
        self._ensure_work_dir()
        state["updated_at"] = now_iso()
        self._check_state_size(state)
        try:
            atomic_write_json(self.work_path, state)
        except OSError as exc:
            raise WorkbenchError(f"Could not save temporary work state: {exc}", 500) from exc

    @staticmethod
    def _check_state_size(state: dict[str, Any]) -> None:
        serialized_size = len((json.dumps(state, ensure_ascii=False, indent=2) + "\n").encode("utf-8"))
        if serialized_size > MAX_WORK_STATE_BYTES:
            raise WorkbenchError("Temporary work queue is full. Clear resolved suggestions before adding more.", 413)

    @staticmethod
    def find_segment(data: dict[str, Any], segment_id: str) -> tuple[int, dict[str, Any]]:
        matches = [(i, item) for i, item in enumerate(data["segments"]) if item.get("id") == segment_id]
        if len(matches) != 1:
            raise WorkbenchError("Segment not found or the manifest contains a duplicate ID.", 404)
        return matches[0]

    def _sync_stale(self, data: dict[str, Any], state: dict[str, Any]) -> bool:
        changed = False
        by_id = {segment["id"]: segment for segment in data["segments"]}
        for segment_id, work in state["segments"].items():
            if not isinstance(work, dict) or not isinstance(work.get("suggestions", []), list):
                continue
            current = by_id.get(segment_id)
            if not current:
                continue
            digest = text_hash(current["text"])
            for suggestion in work.get("suggestions", []):
                if (
                    isinstance(suggestion, dict)
                    and suggestion.get("status") == "pending"
                    and suggestion.get("base_text_sha256") != digest
                ):
                    suggestion["status"] = "stale"
                    suggestion["resolved_at"] = now_iso()
                    changed = True
        return changed

    def state_payload(self) -> dict[str, Any]:
        with self.lock:
            data, manifest_digest = self.read_manifest()
            state = self.read_state()
            if self._sync_stale(data, state):
                self.write_state(state)
            segments = []
            for index, segment in enumerate(data["segments"]):
                segment_id = segment["id"]
                selected = data["selected_takes"].get(segment_id)
                status = segment.get("status", "active")
                issue = None
                duration_seconds = None
                if status != "active":
                    generation_state = "not-included" if status == "inactive" else "retired"
                elif not selected:
                    generation_state = "take-needed"
                else:
                    try:
                        issue = narration.take_problem(segment, selected, data, self.manifest_path, self.audio_root)
                    except ValueError:
                        issue = "selected take path is outside the project audio folder"
                    generation_state = "ready" if issue is None else "take-needed"
                    if generation_state == "ready":
                        try:
                            with wave.open(str(self._safe_audio_path(selected)), "rb") as audio:
                                sample_rate = audio.getframerate()
                                if sample_rate > 0:
                                    duration_seconds = audio.getnframes() / sample_rate
                        except (EOFError, OSError, wave.Error, WorkbenchError):
                            duration_seconds = None
                work = state["segments"].get(segment_id, {})
                segments.append({
                    "position": index + 1,
                    "id": segment_id,
                    "title": segment.get("title", segment_id),
                    "text": segment["text"],
                    "status": status,
                    "voice_style": segment.get("voice_style"),
                    "tts": segment.get("tts", {}),
                    "generation_state": generation_state,
                    "generation_detail": issue if status == "active" and selected and issue else None,
                    "duration_seconds": duration_seconds,
                    "has_selected_take": bool(selected),
                    "audio_url": f"/api/audio/segment/{segment_id}" if selected else None,
                    "takes": self._segment_takes(data, segment),
                    "work": self._work_summary(work, segment["text"]),
                })
            assembled = self._latest_assembly()
            assembly_current = (
                assembled is not None
                and data.get("segments_sha256") == narration.segments_array_sha256(data)
                and self._assembly_matches_manifest(data, assembled)
            )
            return {
                "project": data["project"],
                "project_status": data.get("project_status", "in_progress"),
                "manifest_hash": manifest_digest,
                "voice_style_names": list(data.get("voice_styles", {}).keys()),
                "tts_defaults": {key: value for key, value in data["settings"].items() if key in MAX_TTS_VALUES},
                "pause_ms": data["settings"].get("pause_ms", 350),
                "segments": segments,
                "assembled_audio_url": "/api/audio/assembly" if assembled else None,
                "assembled_audio_name": assembled.name if assembled else None,
                "assembly_current": assembly_current,
            }

    def reorder_segment(self, segment_id: str, target_id: str, placement: str, expected_hash: str) -> dict[str, Any]:
        if placement not in {"before", "after"} or segment_id == target_id:
            raise WorkbenchError("Choose another beat and a valid move direction.")
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
        try:
            with self.lock:
                data, current_hash = self.read_manifest()
                self._check_manifest_hash(expected_hash, current_hash)
                index, segment = self.find_segment(data, segment_id)
                self.find_segment(data, target_id)
                data["segments"].pop(index)
                target_index, _ = self.find_segment(data, target_id)
                data["segments"].insert(target_index + (placement == "after"), segment)
                self._validate_candidate(data)
                self._write_manifest(data, current_hash)
                return self.state_payload()
        finally:
            self.manifest_operation_lock.release()

    def insert_segment(self, after_id: str, title: str, text: str, status: str, expected_hash: str) -> dict[str, Any]:
        if not isinstance(title, str) or not title.strip() or len(title) > MAX_TITLE_CHARS:
            raise WorkbenchError(f"Title must be 1 to {MAX_TITLE_CHARS} characters.")
        if not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS:
            raise WorkbenchError(f"Spoken text must be 1 to {MAX_TEXT_CHARS} characters.")
        if status not in {"active", "inactive"}:
            raise WorkbenchError("New beat status must be active or inactive.")
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
        try:
            with self.lock:
                data, current_hash = self.read_manifest()
                self._check_manifest_hash(expected_hash, current_hash)
                index, _ = self.find_segment(data, after_id)
                normalized = unicodedata.normalize("NFKD", title.strip()).encode("ascii", "ignore").decode("ascii").lower()
                base = re.sub(r"[^a-z0-9]+", "-", normalized).strip("-")[:32].rstrip("-") or "new-beat"
                existing = {segment["id"] for segment in data["segments"]}
                segment_id = base
                number = 2
                while segment_id in existing:
                    suffix = f"-{number}"
                    segment_id = f"{base[:32 - len(suffix)].rstrip('-')}{suffix}"
                    number += 1
                spoken = text.strip()
                data["segments"].insert(index + 1, {
                    "id": segment_id, "status": status, "title": title.strip(),
                    "text": spoken, "text_sha256": text_hash(spoken),
                })
                self._validate_candidate(data)
                self._write_manifest(data, current_hash)
                return {"segment_id": segment_id, "state": self.state_payload()}
        finally:
            self.manifest_operation_lock.release()


    @staticmethod
    def _work_summary(work: Any, current_text: str) -> dict[str, Any]:
        if not isinstance(work, dict):
            return {"note": "", "suggestions": []}
        current_hash = text_hash(current_text)
        suggestions = []
        for item in work.get("suggestions", []):
            if not isinstance(item, dict):
                continue
            copy = dict(item)
            if copy.get("status") == "pending" and copy.get("base_text_sha256") != current_hash:
                copy["status"] = "stale"
            suggestions.append(copy)
        return {"note": work.get("note", ""), "suggestions": suggestions}

    def save_segment(self, segment_id: str, updates: dict[str, Any], expected_hash: str) -> dict[str, Any]:
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
        try:
            return self._save_segment_locked(segment_id, updates, expected_hash)
        finally:
            self.manifest_operation_lock.release()

    def _save_segment_locked(self, segment_id: str, updates: dict[str, Any], expected_hash: str) -> dict[str, Any]:
        allowed = {"title", "text", "status", "voice_style", "tts"}
        if set(updates) - allowed:
            raise WorkbenchError("This edit contains an unsupported field.")
        with self.lock:
            data, current_hash = self.read_manifest()
            self._check_manifest_hash(expected_hash, current_hash)
            _, segment = self.find_segment(data, segment_id)
            if "title" in updates:
                value = updates["title"]
                if not isinstance(value, str) or not value.strip() or len(value) > MAX_TITLE_CHARS:
                    raise WorkbenchError(f"Title must be 1 to {MAX_TITLE_CHARS} characters.")
                value = value.strip()
                if segment.get("title", segment_id) != value:
                    segment["title"] = value
            if "text" in updates:
                value = updates["text"]
                if not isinstance(value, str) or not value.strip() or len(value) > MAX_TEXT_CHARS:
                    raise WorkbenchError(f"Spoken text must be 1 to {MAX_TEXT_CHARS} characters.")
                segment["text"] = value
            if "status" in updates:
                if updates["status"] not in {"active", "inactive", "deleted"}:
                    raise WorkbenchError("Status must be active, inactive, or deleted.")
                if segment.get("status", "active") != updates["status"]:
                    segment["status"] = updates["status"]
            if "voice_style" in updates:
                voice_style = updates["voice_style"]
                if voice_style is not None and voice_style not in data.get("voice_styles", {}):
                    raise WorkbenchError("Choose a voice style from this project's manifest.")
                if segment.get("voice_style") != voice_style:
                    segment["voice_style"] = voice_style
            if "tts" in updates:
                overrides = updates["tts"]
                if not isinstance(overrides, dict) or set(overrides) - MAX_TTS_VALUES:
                    raise WorkbenchError("TTS overrides contain an unsupported setting.")
                try:
                    narration.validate_tts_parameters(overrides, f"segments[{segment_id}].tts")
                except ValueError as exc:
                    raise WorkbenchError(str(exc)) from exc
                if segment.get("tts", {}) != overrides:
                    segment["tts"] = overrides
            state = self.read_state()
            self._sync_stale(data, state)
            self._check_state_size(state)
            self._validate_candidate(data)
            new_hash = self._write_manifest(data, current_hash)
            self.write_state(state)
            return {"manifest_hash": new_hash, "state": self.state_payload()}

    def _validate_candidate(self, data: dict[str, Any]) -> None:
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="w", encoding="utf-8", dir=self.work_dir, prefix=".manifest-check-",
                suffix=".json", delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                json.dump(data, stream, ensure_ascii=False)
            narration.load_manifest(temp_path)
        except (ValueError, OSError) as exc:
            raise WorkbenchError(f"Manifest validation failed: {exc}") from exc
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()

    @staticmethod
    def _check_manifest_hash(expected_hash: str, actual_hash: str) -> None:
        if not isinstance(expected_hash, str) or expected_hash != actual_hash:
            raise WorkbenchError("The manifest changed in another editor. Reload it before saving.", 409)

    def _write_manifest(self, data: dict[str, Any], expected_hash: str) -> str:
        current = sha256_bytes(self._read_manifest_bytes())
        self._check_manifest_hash(expected_hash, current)
        raw = (json.dumps(data, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
        temp_path: Path | None = None
        try:
            with tempfile.NamedTemporaryFile(
                mode="wb", dir=self.audio_root, prefix=".narration_manifest.", suffix=".tmp", delete=False,
            ) as stream:
                temp_path = Path(stream.name)
                stream.write(raw)
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temp_path, self.manifest_path)
        except OSError as exc:
            raise WorkbenchError(f"Could not save narration manifest: {exc}", 500) from exc
        finally:
            if temp_path is not None and temp_path.exists():
                temp_path.unlink()
        return sha256_bytes(raw)

    def save_note(self, segment_id: str, note: str) -> None:
        if not isinstance(note, str) or len(note) > MAX_NOTE_CHARS:
            raise WorkbenchError(f"Note must be at most {MAX_NOTE_CHARS} characters.")
        with self.lock:
            data, _ = self.read_manifest()
            self.find_segment(data, segment_id)
            state = self.read_state()
            work = state["segments"].setdefault(segment_id, {"note": "", "suggestions": []})
            work["note"] = note
            work["note_updated_at"] = now_iso()
            work.setdefault("suggestions", [])
            self.write_state(state)

    def codex_context(self, segment_id: str, note: str) -> tuple[dict[str, Any], str]:
        data, _ = self.read_manifest()
        index, segment = self.find_segment(data, segment_id)
        context = {
            "segment_id": segment_id,
            "title": segment.get("title", segment_id),
            "text": segment["text"],
            "note": note,
            "previous_text": self._neighbor_text(data, index - 1),
            "next_text": self._neighbor_text(data, index + 1),
        }
        try:
            guide = json.loads(AI_GUIDE_PATH.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError(f"The tracked AI guide could not be read: {exc}", 500) from exc
        return context, json.dumps(guide, ensure_ascii=False, indent=2)

    @staticmethod
    def _neighbor_text(data: dict[str, Any], index: int) -> str | None:
        if index < 0 or index >= len(data["segments"]):
            return None
        candidate = data["segments"][index]
        return candidate.get("text") if candidate.get("status", "active") != "deleted" else None

    def store_suggestion(
        self, segment_id: str, note: str, result: dict[str, Any], base_text: str,
    ) -> dict[str, Any]:
        with self.lock:
            data, _ = self.read_manifest()
            _, segment = self.find_segment(data, segment_id)
            state = self.read_state()
            work = state["segments"].setdefault(segment_id, {"note": note, "suggestions": []})
            work.setdefault("note", note)
            base_hash = text_hash(base_text)
            suggestion = {
                "id": uuid.uuid4().hex,
                "status": "pending" if text_hash(segment["text"]) == base_hash else "stale",
                "created_at": now_iso(),
                "base_text_sha256": base_hash,
                "original_text": base_text,
                "proposed_text": result["proposed_text"],
                "rationale": result["rationale"],
                "note": note,
            }
            if suggestion["status"] == "stale":
                suggestion["resolved_at"] = now_iso()
            work.setdefault("suggestions", []).append(suggestion)
            self.write_state(state)
            return suggestion

    def accept_suggestion(self, segment_id: str, suggestion_id: str, expected_hash: str) -> dict[str, Any]:
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
        try:
            return self._accept_suggestion_locked(segment_id, suggestion_id, expected_hash)
        finally:
            self.manifest_operation_lock.release()

    def _accept_suggestion_locked(self, segment_id: str, suggestion_id: str, expected_hash: str) -> dict[str, Any]:
        with self.lock:
            data, current_hash = self.read_manifest()
            self._check_manifest_hash(expected_hash, current_hash)
            _, segment = self.find_segment(data, segment_id)
            state = self.read_state()
            work = state["segments"].get(segment_id, {})
            suggestion = self._find_suggestion(work, suggestion_id)
            if suggestion.get("status") != "pending":
                raise WorkbenchError("This suggestion is no longer pending. Review the latest manifest state.", 409)
            current_text_hash = text_hash(segment["text"])
            if suggestion.get("base_text_sha256") != current_text_hash:
                suggestion["status"] = "stale"
                suggestion["resolved_at"] = now_iso()
                self.write_state(state)
                raise WorkbenchError("The segment changed after this suggestion was made. It is now marked stale.", 409)
            segment["text"] = suggestion["proposed_text"]
            suggestion["status"] = "accepted"
            suggestion["resolved_at"] = now_iso()
            suggestion["accepted_text_sha256"] = text_hash(segment["text"])
            self._sync_stale(data, state)
            self._check_state_size(state)
            self._validate_candidate(data)
            self._write_manifest(data, current_hash)
            self.write_state(state)
            return self.state_payload()

    def dismiss_suggestion(self, segment_id: str, suggestion_id: str) -> None:
        with self.lock:
            data, _ = self.read_manifest()
            self.find_segment(data, segment_id)
            state = self.read_state()
            suggestion = self._find_suggestion(state["segments"].get(segment_id, {}), suggestion_id)
            if suggestion.get("status") != "pending":
                raise WorkbenchError("This suggestion has already been resolved.", 409)
            suggestion["status"] = "dismissed"
            suggestion["resolved_at"] = now_iso()
            self.write_state(state)

    @staticmethod
    def _find_suggestion(work: dict[str, Any], suggestion_id: str) -> dict[str, Any]:
        for item in work.get("suggestions", []):
            if isinstance(item, dict) and item.get("id") == suggestion_id:
                return item
        raise WorkbenchError("Suggestion not found.", 404)

    def clear_resolved(self) -> int:
        with self.lock:
            state = self.read_state()
            removed = 0
            for work in state["segments"].values():
                if not isinstance(work, dict):
                    continue
                before = work.get("suggestions", [])
                after = [item for item in before if isinstance(item, dict) and item.get("status") == "pending"]
                removed += len(before) - len(after)
                work["suggestions"] = after
            self.write_state(state)
            return removed

    def _selected_audio(self, segment_id: str) -> Path:
        data, _ = self.read_manifest()
        _, segment = self.find_segment(data, segment_id)
        relative = data["selected_takes"].get(segment_id)
        if not relative:
            raise WorkbenchError("This segment has no selected narration take.", 404)
        return self._safe_audio_path(relative)

    def _segment_takes(self, data: dict[str, Any], segment: dict[str, Any]) -> list[dict[str, Any]]:
        """Join on-disk takes, manifest reviews, selected take, and prune records."""
        segment_id = segment["id"]
        selected = data["selected_takes"].get(segment_id)
        paths: dict[str, str] = {}
        root = self.audio_root / "segments"
        if root.is_dir() and not root.is_symlink():
            for folder in root.iterdir():
                if not folder.is_dir() or folder.is_symlink():
                    continue
                for path in folder.iterdir():
                    if not path.is_file() or path.is_symlink() or path.suffix.lower() != ".wav":
                        continue
                    match = narration.TAKE_PATTERN.fullmatch(path.name)
                    if not match:
                        continue
                    if path.name.startswith(f"{segment_id}_take-"):
                        pass
                    elif path.name == f"take-{match.group(1)}.wav":
                        try:
                            receipt = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            continue
                        if not isinstance(receipt, dict) or receipt.get("segment_id") != segment_id:
                            continue
                    else:
                        continue
                    key = f"take-{int(match.group(1)):03d}"
                    paths[key] = path.relative_to(self.audio_root).as_posix()
        selected_key = None
        if selected:
            match = narration.TAKE_PATTERN.fullmatch(Path(selected).name)
            if match:
                selected_key = f"take-{int(match.group(1)):03d}"
                try:
                    self._safe_audio_path(selected)
                except WorkbenchError:
                    pass
                else:
                    paths[selected_key] = selected
        pruned: dict[str, dict[str, Any]] = {}
        for record in data.get("pruned_takes", []):
            if not isinstance(record, dict) or record.get("segment_id") != segment_id:
                continue
            match = narration.TAKE_PATTERN.fullmatch(Path(str(record.get("take", ""))).name)
            if match:
                pruned[f"take-{int(match.group(1)):03d}"] = record
        keys = set(paths) | set(segment.get("take_reviews", {})) | set(pruned)
        if selected_key:
            keys.add(selected_key)
        return [
            {
                "key": key,
                "rating": (segment.get("take_reviews", {}).get(key) or pruned.get(key, {}).get("take_review") or {}).get("rating"),
                "note": (segment.get("take_reviews", {}).get(key) or pruned.get(key, {}).get("take_review") or {}).get("note", ""),
                "selected": key == selected_key,
                "available": key in paths,
                "pruned": key in pruned and key not in paths,
                "audio_url": f"/api/audio/take/{segment_id}/{key}" if key in paths else None,
            }
            for key in sorted(keys, key=lambda value: int(value.removeprefix("take-")))
        ]

    def take_audio_path(self, segment_id: str, take_key: str) -> Path:
        if not narration.TAKE_REVIEW_PATTERN.fullmatch(take_key):
            raise WorkbenchError("Invalid take number.", 404)
        data, _ = self.read_manifest()
        _, segment = self.find_segment(data, segment_id)
        take = next((item for item in self._segment_takes(data, segment) if item["key"] == take_key), None)
        if not take or not take["audio_url"]:
            raise WorkbenchError("This take's audio is unavailable.", 404)
        # Resolve the confined path again; never accept a filesystem path from the browser.
        selected = data["selected_takes"].get(segment_id)
        if take["selected"] and selected:
            try:
                return self._safe_audio_path(selected)
            except WorkbenchError:
                pass
        root = self.audio_root / "segments"
        for folder in root.iterdir():
            if not folder.is_dir() or folder.is_symlink():
                continue
            for name in (f"{segment_id}_{take_key}.wav", f"{take_key}.wav"):
                path = folder / name
                if path.is_file() and not path.is_symlink():
                    if name == f"{take_key}.wav":
                        try:
                            receipt = json.loads(path.with_suffix(".json").read_text(encoding="utf-8"))
                        except (OSError, json.JSONDecodeError):
                            continue
                        if not isinstance(receipt, dict) or receipt.get("segment_id") != segment_id:
                            continue
                    return self._safe_audio_path(path.relative_to(self.audio_root).as_posix())
        raise WorkbenchError("This take's audio is unavailable.", 404)

    def _safe_audio_path(self, relative: str) -> Path:
        try:
            path = narration.relative_audio_path(self.audio_root, relative)
        except ValueError as exc:
            raise WorkbenchError(str(exc), 404) from exc
        if path.suffix.lower() != ".wav" or not path.is_file() or path.is_symlink():
            raise WorkbenchError("Selected narration audio is missing or unavailable.", 404)
        return path

    def _latest_assembly(self) -> Path | None:
        folder = self.audio_root / "assembled"
        if not folder.is_dir() or folder.is_symlink():
            return None
        files = [path for path in folder.glob("*.wav") if path.is_file() and not path.is_symlink()]
        return max(
            files,
            key=lambda path: (path.stat().st_mtime_ns, path.name.endswith("stereo-review.wav")),
        ) if files else None

    def _assembly_matches_manifest(self, data: dict[str, Any], audio_path: Path) -> bool:
        performance_dir = self.audio_root / "performance"
        if not performance_dir.is_dir() or performance_dir.is_symlink():
            return False
        for record_path in sorted(performance_dir.glob("run_*.json"), key=lambda path: path.name, reverse=True):
            if not record_path.is_file() or record_path.is_symlink():
                continue
            try:
                record = json.loads(record_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                continue
            if not isinstance(record, dict) or record.get("status") != "complete":
                continue
            assembly = record.get("assembly")
            if not isinstance(assembly, dict):
                continue
            recorded_paths = [assembly.get("master_mono"), assembly.get("review_stereo")]
            recorded_paths = [path for path in recorded_paths if isinstance(path, str)]
            if not recorded_paths or assembly.get("selected_takes") != data.get("selected_takes", {}):
                return False
            for recorded_path in recorded_paths:
                try:
                    recorded_audio = self._safe_audio_path(recorded_path)
                except WorkbenchError:
                    continue
                if recorded_audio.resolve() == audio_path.resolve():
                    return True
            return False
        return False

    def assembly_audio_path(self) -> Path:
        path = self._latest_assembly()
        if path is None:
            raise WorkbenchError("No assembled narration WAV is available yet.", 404)
        return path


def build_codex_prompt(guide_json: str, context: dict[str, Any]) -> str:
    return (
        "Revise one narration segment using the guide and context below. The creator explicitly requested "
        "a suggestion. Return a complete replacement for the selected segment only. Keep facts and meaning "
        "grounded in the supplied words. Do not make changes to files or use tools.\n\n"
        "AI GUIDE (tracked public tool file):\n"
        f"{guide_json}\n\n"
        "REQUEST CONTEXT (only this segment, its note, and immediate neighbors):\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n"
    )


def run_codex_suggestion(codex_path: str, project: Project, segment_id: str, note: str) -> dict[str, str]:
    if not note.strip():
        raise WorkbenchError("Add a wording note before asking Codex.")
    context, guide = project.codex_context(segment_id, note)
    prompt = build_codex_prompt(guide, context)
    with tempfile.TemporaryDirectory(prefix="narration-workbench-codex-") as temp_dir:
        response_path = Path(temp_dir) / "suggestion.json"
        command = [
            codex_path, "exec", "--ephemeral", "--sandbox", "read-only",
            "--ignore-user-config", "--skip-git-repo-check", "--output-schema", str(AI_SCHEMA_PATH),
            "--output-last-message", str(response_path), "--color", "never", "-",
        ]
        try:
            completed = subprocess.run(
                command, input=prompt, text=True, encoding="utf-8", errors="replace",
                capture_output=True, cwd=temp_dir, timeout=240, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WorkbenchError("Codex took more than four minutes. The note is still saved for another try.", 504) from exc
        except OSError as exc:
            raise WorkbenchError(f"Could not start Codex: {exc}. The note is still saved.", 503) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-1600:]
            raise WorkbenchError(f"Codex could not return a suggestion. {detail or 'Check Codex sign-in and CLI setup.'}", 502)
        try:
            result = json.loads(response_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError("Codex returned a response that could not be read as structured JSON.", 502) from exc
    if not isinstance(result, dict) or set(result) != {"segment_id", "proposed_text", "rationale"}:
        raise WorkbenchError("Codex response did not match the suggestion format.", 502)
    if result["segment_id"] != segment_id:
        raise WorkbenchError("Codex response targeted a different segment. No suggestion was saved.", 502)
    if not isinstance(result["proposed_text"], str) or not result["proposed_text"].strip() or len(result["proposed_text"]) > MAX_TEXT_CHARS:
        raise WorkbenchError("Codex returned empty or oversized narration text.", 502)
    if not isinstance(result["rationale"], str):
        raise WorkbenchError("Codex returned an invalid explanation.", 502)
    return result


def resolve_codex(requested: str | None) -> str | None:
    if requested:
        candidate = Path(requested).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        return shutil.which(requested)
    return shutil.which("codex")


def run_tool(command: list[str], timeout: int, input_text: str | None = None) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command, input=input_text, text=True, encoding="utf-8", errors="replace",
            capture_output=True, cwd=TOOL_DIR, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise WorkbenchError(f"The command exceeded its {timeout}-second limit.", 504) from exc
    except OSError as exc:
        raise WorkbenchError(f"Could not start the narration tool: {exc}", 503) from exc
    output = (result.stdout or "").strip()
    errors = (result.stderr or "").strip()
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "output": output[-MAX_RESPONSE_CHARS:],
        "error": errors[-MAX_RESPONSE_CHARS:],
    }


def create_handler(project: Project, codex_path: str | None, python_path: str) -> type[BaseHTTPRequestHandler]:
    sequence_run_lock = threading.Lock()
    sequence_state_lock = threading.Lock()
    sequence_process: subprocess.Popen[str] | None = None
    sapi_render_lock = threading.Lock()
    sapi_temp: tempfile.TemporaryDirectory[str] | None = None
    sapi_cache: dict[str, Any] = {}

    class Handler(BaseHTTPRequestHandler):
        server_version = "NarrationWorkbench/1.0"
        sys_version = ""

        def log_message(self, fmt: str, *args: Any) -> None:
            # Avoid putting script text or user notes in the terminal log.
            print(f"{self.address_string()} - {fmt % args}")

        def _local_request(self) -> bool:
            try:
                if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                    return False
            except ValueError:
                return False
            host_header = urlparse("//" + self.headers.get("Host", "")).hostname
            try:
                host_port = urlparse("//" + self.headers.get("Host", "")).port
            except ValueError:
                return False
            if (host_header or "").lower() not in {"127.0.0.1", "localhost"} or host_port != self.server.server_port:
                return False
            origin = self.headers.get("Origin")
            if origin:
                parsed = urlparse(origin)
                try:
                    origin_port = parsed.port
                except ValueError:
                    return False
                if (parsed.scheme not in {"http", "https"}
                    or (parsed.hostname or "").lower() not in {"127.0.0.1", "localhost"}
                    or origin_port != self.server.server_port):
                    return False
            return True

        def _headers(self, content_type: str) -> None:
            self.send_header("Content-Type", content_type)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; media-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")

        def _json(self, status: int, value: dict[str, Any]) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._headers("application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _read_json(self) -> dict[str, Any]:
            if self.headers.get_content_type() != "application/json":
                raise WorkbenchError("Send this request as application/json.", 415)
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise WorkbenchError("Invalid request size.") from exc
            if length < 2 or length > MAX_REQUEST_BYTES:
                raise WorkbenchError(f"Request must be between 2 and {MAX_REQUEST_BYTES} bytes.", 413)
            try:
                value = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise WorkbenchError("Request body is not valid UTF-8 JSON.") from exc
            if not isinstance(value, dict):
                raise WorkbenchError("Request body must be a JSON object.")
            return value

        def do_GET(self) -> None:  # noqa: N802
            if not self._local_request():
                self._json(403, {"error": "This workbench accepts requests only from its local browser."})
                return
            try:
                if self.path in {"/", "/index.html", "/app.js", "/styles.css"}:
                    filename = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/styles.css": "styles.css"}[self.path]
                    path = STATIC_DIR / filename
                    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                    if filename.endswith(".js"):
                        content_type += "; charset=utf-8"
                    elif filename.endswith(".html") or filename.endswith(".css"):
                        content_type += "; charset=utf-8"
                    self._send_file(path, content_type)
                elif self.path == "/api/state":
                    self._json(200, project.state_payload())
                elif self.path == "/api/provider":
                    provider = {"name": "Codex", "available": bool(codex_path), "executable": bool(codex_path)}
                    if codex_path:
                        result = run_tool([codex_path, "--version"], 10)
                        provider["available"] = result["ok"]
                        provider["version"] = result["output"] if result["ok"] else "Version check failed"
                    self._json(200, {
                        "codex": provider,
                        "preview": {"available": platform.system() == "Windows", "backend": "Windows SAPI" if platform.system() == "Windows" else "unsupported on this system"},
                    })
                elif self.path.startswith("/api/audio/segment/"):
                    segment_id = self.path.removeprefix("/api/audio/segment/")
                    self._send_file(project._selected_audio(segment_id), "audio/wav", allow_range=True)
                elif self.path.startswith("/api/audio/take/"):
                    parts = self.path.removeprefix("/api/audio/take/").split("/")
                    if len(parts) != 2:
                        raise WorkbenchError("Invalid take audio request.", 404)
                    self._send_file(project.take_audio_path(parts[0], parts[1]), "audio/wav", allow_range=True)
                elif self.path == "/api/audio/assembly":
                    self._send_file(project.assembly_audio_path(), "audio/wav", allow_range=True)
                elif self.path.split("?", 1)[0] == "/api/audio/sapi-preview":
                    if not sapi_cache.get("path"):
                        raise WorkbenchError("Build the SAPI preview first.", 404)
                    self._send_file(sapi_cache["path"], "audio/wav", allow_range=True)
                else:
                    self._json(404, {"error": "Not found."})
            except WorkbenchError as exc:
                self._json(exc.status, {"error": str(exc)})

        def _send_file(self, path: Path, content_type: str, allow_range: bool = False) -> None:
            if not path.is_file() or path.is_symlink():
                raise WorkbenchError("Requested file is unavailable.", 404)
            size = path.stat().st_size
            start, end, status = 0, size - 1, 200
            range_header = self.headers.get("Range") if allow_range else None
            if range_header:
                try:
                    unit, spec = range_header.split("=", 1)
                    if unit != "bytes" or "," in spec:
                        raise ValueError
                    left, right = spec.split("-", 1)
                    if left:
                        start = int(left)
                        end = int(right) if right else size - 1
                    else:
                        length = int(right)
                        start = max(0, size - length)
                        end = size - 1
                    if start < 0 or end < start or start >= size:
                        raise ValueError
                    end = min(end, size - 1)
                    status = 206
                except (ValueError, IndexError):
                    self.send_response(416)
                    self._headers("text/plain; charset=utf-8")
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
            length = max(0, end - start + 1)
            self.send_response(status)
            self._headers(content_type)
            self.send_header("Accept-Ranges", "bytes" if allow_range else "none")
            self.send_header("Content-Length", str(length))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with path.open("rb") as stream:
                stream.seek(start)
                remaining = length
                while remaining:
                    chunk = stream.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def do_POST(self) -> None:  # noqa: N802
            if not self._local_request():
                self._json(403, {"error": "This workbench accepts requests only from its local browser."})
                return
            try:
                body = self._read_json()
                if self.path == "/api/segment/save":
                    result = project.save_segment(
                        self._required_string(body, "segment_id"), self._object(body, "updates"),
                        self._required_string(body, "manifest_hash"),
                    )
                    self._json(200, result)
                elif self.path == "/api/segments/reorder":
                    self._json(200, {"state": project.reorder_segment(
                        self._required_string(body, "segment_id"), self._required_string(body, "target_id"),
                        self._required_string(body, "placement"), self._required_string(body, "manifest_hash"),
                    )})
                elif self.path == "/api/segments/insert":
                    self._json(200, project.insert_segment(
                        self._required_string(body, "after_id"), self._required_string(body, "title"),
                        self._required_string(body, "text"), self._required_string(body, "status"),
                        self._required_string(body, "manifest_hash"),
                    ))
                elif self.path == "/api/note":
                    segment_id = self._required_string(body, "segment_id")
                    project.save_note(segment_id, self._string(body, "note"))
                    self._json(200, {"ok": True, "state": project.state_payload()})
                elif self.path == "/api/codex/suggest":
                    segment_id = self._required_string(body, "segment_id")
                    note = self._string(body, "note")
                    project.save_note(segment_id, note)
                    if not codex_path:
                        raise WorkbenchError("Codex CLI was not found. Install or sign in to Codex, then restart this workbench. Your note is saved.", 503)
                    context, _ = project.codex_context(segment_id, note)
                    result = run_codex_suggestion(codex_path, project, segment_id, note)
                    suggestion = project.store_suggestion(segment_id, note, result, context["text"])
                    self._json(200, {"suggestion": suggestion, "state": project.state_payload()})
                elif self.path == "/api/suggestion/accept":
                    state = project.accept_suggestion(
                        self._required_string(body, "segment_id"),
                        self._required_string(body, "suggestion_id"),
                        self._required_string(body, "manifest_hash"),
                    )
                    self._json(200, {"state": state})
                elif self.path == "/api/suggestion/dismiss":
                    project.dismiss_suggestion(
                        self._required_string(body, "segment_id"),
                        self._required_string(body, "suggestion_id"),
                    )
                    self._json(200, {"ok": True, "state": project.state_payload()})
                elif self.path == "/api/work/clear":
                    self._json(200, {"removed_suggestions": project.clear_resolved(), "state": project.state_payload()})
                elif self.path == "/api/preview":
                    self._json(200, self._preview(self._string(body, "text")))
                elif self.path == "/api/preview/sequence":
                    self._preview_sequence(body.get("texts"))
                elif self.path == "/api/preview/stop":
                    with sequence_state_lock:
                        process = sequence_process
                        if process is not None and process.poll() is None:
                            process.terminate()
                    self._json(200, {"ok": True})
                elif self.path == "/api/preview/render":
                    self._json(200, self._render_sapi_preview())
                elif self.path == "/api/generate":
                    self._json(200, self._run_generation(assemble=False))
                elif self.path == "/api/assemble":
                    self._json(200, self._run_generation(assemble=True))
                else:
                    self._json(404, {"error": "Not found."})
            except WorkbenchError as exc:
                self._json(exc.status, {"error": str(exc)})
            except (KeyError, TypeError) as exc:
                self._json(400, {"error": f"Invalid request: {exc}"})

        @staticmethod
        def _required_string(body: dict[str, Any], key: str) -> str:
            value = body.get(key)
            if not isinstance(value, str) or not value.strip():
                raise WorkbenchError(f"{key} is required.")
            return value

        @staticmethod
        def _string(body: dict[str, Any], key: str) -> str:
            value = body.get(key)
            if not isinstance(value, str):
                raise WorkbenchError(f"{key} must be text.")
            return value

        @staticmethod
        def _object(body: dict[str, Any], key: str) -> dict[str, Any]:
            value = body.get(key)
            if not isinstance(value, dict):
                raise WorkbenchError(f"{key} must be an object.")
            return value

        def _preview(self, text: str) -> dict[str, Any]:
            if not text.strip() or len(text) > MAX_TEXT_CHARS:
                raise WorkbenchError("Preview text must not be empty or exceed the narration text limit.")
            script = TOOL_DIR / "preview_narration.py"
            result = run_tool([python_path, str(script), "--text", "-"], timeout=180, input_text=text)
            if not result["ok"]:
                message = result["error"] or result["output"] or "Transient preview failed."
                return {"ok": False, "error": message, "unsupported": "unavailable" in message.lower() or platform.system() != "Windows"}
            return {"ok": True, "message": result["output"] or "Preview finished."}

        def _render_sapi_preview(self) -> dict[str, Any]:
            nonlocal sapi_temp
            if platform.system() != "Windows":
                raise WorkbenchError("SAPI preview is available only on Windows.", 503)
            executable = shutil.which("powershell.exe") or shutil.which("powershell")
            if not executable:
                raise WorkbenchError("Windows PowerShell was not found.", 503)
            if not sapi_render_lock.acquire(blocking=False):
                raise WorkbenchError("A SAPI preview is already being rendered.", 409)
            try:
                data, _ = project.read_manifest()
                active = narration.active_segments(data)
                if not active or len(active) > 500:
                    raise WorkbenchError("SAPI preview needs 1 to 500 active beats.")
                texts = [segment["text"] for segment in active]
                if sum(len(text) for text in texts) > 250_000:
                    raise WorkbenchError("The active narration is too long for a quick SAPI preview.")
                pause_ms = int(data["settings"].get("pause_ms", 350))
                digest = text_hash(json.dumps([[(segment["id"], segment["text"]) for segment in active], pause_ms], ensure_ascii=False))
                if sapi_cache.get("digest") == digest and sapi_cache["path"].is_file():
                    return {"ok": True, "url": f"/api/audio/sapi-preview?v={digest}", "beats": sapi_cache["beats"], "cached": True}

                if sapi_temp is None:
                    sapi_temp = tempfile.TemporaryDirectory(prefix="vps-sapi-preview-")
                with tempfile.TemporaryDirectory(dir=sapi_temp.name, prefix="beats-") as beat_dir:
                    try:
                        result = subprocess.run(
                            [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                             "-File", str(TOOL_DIR / "preview_narration.ps1"), "-RenderSequence",
                             "-OutputDirectory", beat_dir],
                            input=json.dumps(texts, ensure_ascii=False), capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=300,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        raise WorkbenchError(f"Could not render SAPI preview: {exc}", 503) from exc
                    if result.returncode:
                        raise WorkbenchError(result.stderr.strip() or "SAPI preview rendering failed.", 503)

                    timeline: list[dict[str, Any]] = []
                    cursor = 0
                    frames = bytearray()
                    format_key: tuple[Any, ...] | None = None
                    sample_rate = 0
                    for index, segment in enumerate(active):
                        beat_path = Path(beat_dir) / f"beat-{index:04d}.wav"
                        try:
                            with wave.open(str(beat_path), "rb") as beat_audio:
                                current_format = (beat_audio.getnchannels(), beat_audio.getsampwidth(),
                                                  beat_audio.getframerate(), beat_audio.getcomptype())
                                if format_key is None:
                                    format_key = current_format
                                    sample_rate = beat_audio.getframerate()
                                elif current_format != format_key:
                                    raise WorkbenchError("SAPI returned inconsistent audio formats between beats.", 503)
                                frame_count = beat_audio.getnframes()
                                frames.extend(beat_audio.readframes(frame_count))
                        except (OSError, EOFError, wave.Error) as exc:
                            raise WorkbenchError(f"Could not read SAPI beat {index + 1}: {exc}", 503) from exc
                        timeline.append({"id": segment["id"], "start": cursor / sample_rate,
                                         "end": (cursor + frame_count) / sample_rate})
                        cursor += frame_count
                        if index < len(active) - 1:
                            silent_frames = round(sample_rate * pause_ms / 1000)
                            frames.extend(b"\0" * silent_frames * format_key[0] * format_key[1])
                            cursor += silent_frames

                    output_path = Path(sapi_temp.name) / f"{digest}.wav"
                    with wave.open(str(output_path), "wb") as output:
                        output.setnchannels(format_key[0])
                        output.setsampwidth(format_key[1])
                        output.setframerate(sample_rate)
                        output.writeframes(frames)
                sapi_cache.update(digest=digest, path=output_path, beats=timeline)
                return {"ok": True, "url": f"/api/audio/sapi-preview?v={digest}", "beats": timeline, "cached": False}
            finally:
                sapi_render_lock.release()

        def _preview_sequence(self, texts: Any) -> None:
            nonlocal sequence_process
            if platform.system() != "Windows":
                raise WorkbenchError("SAPI sequence preview is available only on Windows.", 503)
            if (not isinstance(texts, list) or not texts or len(texts) > 500
                or any(not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS for text in texts)):
                raise WorkbenchError("Preview sequence needs 1 to 500 nonempty narration beats.")
            executable = shutil.which("powershell.exe") or shutil.which("powershell")
            if not executable:
                raise WorkbenchError("Windows PowerShell was not found.", 503)
            if not sequence_run_lock.acquire(blocking=False):
                raise WorkbenchError("A SAPI sequence preview is already running.", 409)
            process: subprocess.Popen[str] | None = None
            try:
                process = subprocess.Popen(
                    [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-File", str(TOOL_DIR / "preview_narration.ps1"), "-Sequence"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace", cwd=TOOL_DIR,
                )
                with sequence_state_lock:
                    sequence_process = process
                assert process.stdin is not None
                process.stdin.write(json.dumps(texts, ensure_ascii=False))
                process.stdin.close()
                self.send_response(200)
                self._headers("application/x-ndjson; charset=utf-8")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True

                def emit(event: str, **details: Any) -> None:
                    payload = json.dumps({"event": event, **details}, ensure_ascii=False).encode("utf-8") + b"\n"
                    self.wfile.write(payload)
                    self.wfile.flush()

                assert process.stdout is not None
                for line in process.stdout:
                    kind, _, number = line.strip().partition(" ")
                    if kind in {"START", "DONE"} and number.isdecimal() and int(number) < len(texts):
                        emit(kind.lower(), index=int(number))
                returncode = process.wait()
                if returncode:
                    assert process.stderr is not None
                    emit("error", message=process.stderr.read().strip() or "SAPI preview stopped unexpectedly.")
                else:
                    emit("complete")
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                with sequence_state_lock:
                    if sequence_process is process:
                        sequence_process = None
                sequence_run_lock.release()

        def _run_generation(self, assemble: bool) -> dict[str, Any]:
            if not project.manifest_operation_lock.acquire(blocking=False):
                raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
            try:
                project.read_manifest()
                if assemble:
                    command = [python_path, str(TOOL_DIR / "generate_narration.py"), "--manifest", str(project.manifest_path), "--assemble-only"]
                else:
                    command = [python_path, str(TOOL_DIR / "generate_narration.py"), "--manifest", str(project.manifest_path), "--generate-only"]
                result = run_tool(command, timeout=3600)
                result["state"] = project.state_payload()
                return result
            finally:
                project.manifest_operation_lock.release()

    return Handler


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open a local script and narration workbench for one project.")
    parser.add_argument("--manifest", required=True, type=Path, help="The selected project's narration_manifest.json file.")
    parser.add_argument("--port", type=int, default=8766, help="Local browser port (default: 8766).")
    parser.add_argument("--codex", help="Optional path or command name for the Codex CLI.")
    parser.add_argument("--python", default=sys.executable, help="Python executable used by the existing narration scripts.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not 1024 <= args.port <= 65535:
        print("Port must be between 1024 and 65535.", file=sys.stderr)
        return 2
    try:
        project = Project(args.manifest)
        project.read_manifest()
    except WorkbenchError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    codex_path = resolve_codex(args.codex)
    server_type = type("WorkbenchHTTPServer", (ThreadingHTTPServer,), {"daemon_threads": True})
    try:
        server = server_type(("127.0.0.1", args.port), create_handler(project, codex_path, args.python))
    except OSError as exc:
        print(f"Could not start local server on 127.0.0.1:{args.port}: {exc}", file=sys.stderr)
        return 2
    print(f"Narration workbench for {project.manifest_path.parent.parent.name}")
    print(f"Open http://127.0.0.1:{args.port} in your browser. Press Ctrl+C to stop.")
    print(f"Codex CLI: {'available' if codex_path else 'not found'}; Windows SAPI preview: {'available' if platform.system() == 'Windows' else 'unavailable on this system'}")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopping the narration workbench.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

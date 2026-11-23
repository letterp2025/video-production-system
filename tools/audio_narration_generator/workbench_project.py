"""Manifest-backed project state, editing, notes, audio, and visual plans."""

from __future__ import annotations

import json
import os
import re
import tempfile
import threading
import unicodedata
import uuid
import wave
from pathlib import Path
from typing import Any

import generate_narration as narration
from workbench_audio import AudioReadMixin
from workbench_layer_mappings import AudioLayerMappingMixin
from workbench_common import (
    AI_GUIDE_PATH, MAX_NOTE_CHARS, MAX_TEXT_CHARS, MAX_TITLE_CHARS,
    MAX_TTS_VALUES, MAX_WORK_STATE_BYTES,
    WorkbenchError, atomic_write_json, now_iso,
    sha256_bytes, text_hash, visual_animation_recipes,
)
from workbench_visuals import VisualPlanMixin


class Project(VisualPlanMixin, AudioLayerMappingMixin, AudioReadMixin):
    """Manifest and private work queue, with focused audio and layer helpers."""

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

    @staticmethod
    def _recipe_catalog() -> list[dict[str, str]]:
        return visual_animation_recipes()


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
            visual_recipes = self._recipe_catalog()
            recipes_by_id = {item["id"]: item["title"] for item in visual_recipes}
            visual_layer = self.visual_layer_payload(data)
            visual_take_document = None
            selected_visual_take = visual_layer.get("selected_take") or {}
            if selected_visual_take.get("take_id") and selected_visual_take.get("status") != "invalid":
                try:
                    visual_take_document = self._visual_take_document(selected_visual_take["take_id"], data)
                except WorkbenchError:
                    pass
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
                    "visual_plan": self._visual_plan_summary(segment, recipes_by_id),
                    "visual_take_segment": self.visual_take_segment_payload(segment, visual_layer, visual_take_document),
                    "music_mapping": self._audio_mapping_summary("music", segment),
                    "sfx_mapping": self._audio_mapping_summary("sfx", segment),
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
                "visual_recipes": visual_recipes,
                "visual_layer": visual_layer,
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

    def rate_take(self, segment_id: str, take_key: str, rating: str, expected_hash: str) -> dict[str, Any]:
        if not narration.TAKE_REVIEW_PATTERN.fullmatch(take_key):
            raise WorkbenchError("Choose a valid take number.")
        if rating not in narration.TAKE_REVIEW_RATINGS:
            raise WorkbenchError("Choose Favorite, Acceptable, or Rejected.")
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
        try:
            with self.lock:
                data, current_hash = self.read_manifest()
                self._check_manifest_hash(expected_hash, current_hash)
                _, segment = self.find_segment(data, segment_id)
                take = next((item for item in self._segment_takes(data, segment) if item["key"] == take_key), None)
                if take is None:
                    raise WorkbenchError("Take not found in this project.", 404)

                if take["pruned"] and not take["available"]:
                    record = next((
                        item for item in data.get("pruned_takes", [])
                        if isinstance(item, dict)
                        and item.get("segment_id") == segment_id
                        and (match := narration.TAKE_PATTERN.fullmatch(Path(str(item.get("take", ""))).name))
                        and f"take-{int(match.group(1)):03d}" == take_key
                    ), None)
                    if record is None:
                        raise WorkbenchError("Take review record could not be found.", 404)
                    reviews = segment.setdefault("take_reviews", {})
                    archived_review = record.get("take_review")
                    current_review = reviews.get(take_key)
                    review = dict(archived_review) if isinstance(archived_review, dict) else {}
                    if isinstance(current_review, dict):
                        review.update(current_review)
                    review["rating"] = rating
                    reviews[take_key] = review
                    record["take_review"] = dict(review)
                else:
                    reviews = segment.setdefault("take_reviews", {})
                    review = reviews.get(take_key)
                    if not isinstance(review, dict):
                        review = {}
                        for record in data.get("pruned_takes", []):
                            if not isinstance(record, dict) or record.get("segment_id") != segment_id:
                                continue
                            match = narration.TAKE_PATTERN.fullmatch(Path(str(record.get("take", ""))).name)
                            if match and f"take-{int(match.group(1)):03d}" == take_key:
                                archived_review = record.get("take_review")
                                if isinstance(archived_review, dict):
                                    review = dict(archived_review)
                                break
                    review["rating"] = rating
                    reviews[take_key] = review

                self._validate_candidate(data)
                new_hash = self._write_manifest(data, current_hash)
                return {"manifest_hash": new_hash, "state": self.state_payload()}
        finally:
            self.manifest_operation_lock.release()

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

"""Optional per-segment Music and SFX cue mapping JSON files."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import generate_narration as narration

from workbench_common import WorkbenchError, atomic_create_json, text_hash
from workbench_layer_contracts import MAX_LAYER_JSON_BYTES, validate_audio_mapping
from workbench_visual_takes import VisualTakeMixin


class AudioLayerMappingMixin(VisualTakeMixin):
    def _audio_mapping_dir(self, layer: str, *, create: bool = False) -> Path:
        if layer not in {"music", "sfx"}:
            raise WorkbenchError("Choose the Music or Sound Effects layer.")
        folder = self.audio_root / layer
        if folder.is_symlink():
            raise WorkbenchError(f"The audio/{layer} folder cannot be a symlink.")
        if create:
            try:
                folder.mkdir(exist_ok=True)
            except OSError as exc:
                raise WorkbenchError(f"Could not create audio/{layer}: {exc}", 500) from exc
        if folder.exists() and not folder.is_dir():
            raise WorkbenchError(f"The audio/{layer} path is not a folder.")
        try:
            folder.resolve(strict=folder.exists()).relative_to(self.audio_root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise WorkbenchError(f"The audio/{layer} folder must stay inside the selected project.") from exc
        return folder

    def _audio_mapping_path(self, layer: str, segment_id: str, *, create: bool = False) -> Path:
        if not isinstance(segment_id, str) or not narration.ID_PATTERN.fullmatch(segment_id):
            raise WorkbenchError("Invalid segment ID.")
        path = self._audio_mapping_dir(layer, create=create) / f"{segment_id}.json"
        if path.is_symlink():
            raise WorkbenchError("An audio mapping file cannot be a symlink.")
        try:
            path.resolve(strict=False).relative_to(self.audio_root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise WorkbenchError("The audio mapping file must stay inside the project audio folder.") from exc
        return path

    def _audio_mapping_summary(self, layer: str, segment: dict[str, Any]) -> dict[str, Any]:
        segment_id = segment["id"]
        relative_path = f"{layer}/{segment_id}.json"
        try:
            path = self._audio_mapping_path(layer, segment_id)
        except WorkbenchError:
            return {"status": "invalid", "exists": False, "can_open": False, "relative_path": relative_path, "cue_count": 0}
        if not path.exists():
            return {"status": "none", "exists": False, "can_open": False, "relative_path": relative_path, "cue_count": 0}
        if path.is_symlink() or not path.is_file():
            return {"status": "invalid", "exists": True, "can_open": False, "relative_path": relative_path, "cue_count": 0}
        try:
            if path.stat().st_size > MAX_LAYER_JSON_BYTES:
                return {"status": "invalid", "exists": True, "can_open": False, "relative_path": relative_path, "cue_count": 0}
            value = self._read_layer_json(path)
            mapping = validate_audio_mapping(value, layer, segment_id, self._project_root())
        except (WorkbenchError, ValueError, OSError):
            return {"status": "invalid", "exists": True, "can_open": True, "relative_path": relative_path, "cue_count": 0}
        status = "needs_review" if mapping["source_text_sha256"] != text_hash(segment["text"]) else "saved"
        return {
            "status": status,
            "exists": True,
            "can_open": True,
            "relative_path": relative_path,
            "cue_count": len(mapping["cues"]),
        }

    def create_audio_mapping(self, layer: str, segment_id: str, expected_hash: str) -> dict[str, Any]:
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
        try:
            return self._create_audio_mapping(layer, segment_id, expected_hash)
        finally:
            self.manifest_operation_lock.release()

    def _create_audio_mapping(self, layer: str, segment_id: str, expected_hash: str) -> dict[str, Any]:
        with self.lock:
            narration_data, current_hash = self.read_manifest()
            self._check_manifest_hash(expected_hash, current_hash)
            _, segment = self.find_segment(narration_data, segment_id)
            path = self._audio_mapping_path(layer, segment_id, create=True)
            if path.exists() or path.is_symlink():
                raise WorkbenchError("A mapping already exists for this beat. Open it to review; it was not overwritten.", 409)
            value = {
                "schema_version": 1,
                "layer": layer,
                "segment_id": segment_id,
                "source_text_sha256": text_hash(segment["text"]),
                "cues": [],
            }
            try:
                atomic_create_json(path, value)
            except FileExistsError as exc:
                raise WorkbenchError("A mapping already exists for this beat. Open it to review; it was not overwritten.", 409) from exc
            except OSError as exc:
                raise WorkbenchError(f"Could not create the {layer} mapping: {exc}", 500) from exc
            return {"relative_path": f"{layer}/{segment_id}.json", "state": self.state_payload()}

    def open_audio_mapping(self, layer: str, segment_id: str) -> None:
        with self.lock:
            narration_data, _ = self.read_manifest()
            self.find_segment(narration_data, segment_id)
            path = self._audio_mapping_path(layer, segment_id)
            if not path.is_file() or path.is_symlink():
                raise WorkbenchError("No safe mapping file is available for this beat.", 404)
            if path.stat().st_size > MAX_LAYER_JSON_BYTES:
                raise WorkbenchError("Layer JSON is larger than the 1 MB workbench limit.", 413)
            self._open_layer_file(path, f"{layer} mapping")

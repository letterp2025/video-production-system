"""Whole-spine visual take manifests for a selected video project."""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path
from typing import Any

from workbench_common import WorkbenchError, atomic_create_json, atomic_write_json, text_hash
from workbench_layer_contracts import (
    MAX_LAYER_JSON_BYTES,
    TAKE_ID_PATTERN,
    validate_visual_take,
    visual_segment_status,
)


class VisualTakeMixin:
    def _project_root(self) -> Path:
        return self.audio_root.parent.resolve(strict=True)

    def _visual_layer_dir(self, *, create: bool = False) -> Path:
        root = self._project_root() / "visual_layer"
        if root.is_symlink():
            raise WorkbenchError("The project visual_layer folder cannot be a symlink.")
        if create:
            try:
                root.mkdir(exist_ok=True)
            except OSError as exc:
                raise WorkbenchError(f"Could not create project visual_layer folder: {exc}", 500) from exc
        if root.exists() and not root.is_dir():
            raise WorkbenchError("The project visual_layer path is not a folder.")
        try:
            root.resolve(strict=root.exists()).relative_to(self._project_root())
        except (OSError, ValueError) as exc:
            raise WorkbenchError("The project visual_layer folder must stay inside the video project.") from exc
        return root

    def _visual_take_path(self, take_id: str, *, create: bool = False) -> Path:
        if not isinstance(take_id, str) or not TAKE_ID_PATTERN.fullmatch(take_id):
            raise WorkbenchError("Take ID must start with v_layer_ and contain only lowercase letters, numbers, underscores, or hyphens.")
        root = self._visual_layer_dir(create=create)
        path = root / f"{take_id}.json"
        if path.is_symlink():
            raise WorkbenchError("A visual take manifest cannot be a symlink.")
        try:
            path.resolve(strict=False).relative_to(self._project_root())
        except (OSError, ValueError) as exc:
            raise WorkbenchError("The visual take manifest must stay inside the video project.") from exc
        return path

    def _selected_visual_take_path(self, *, create: bool = False) -> Path:
        path = self._visual_layer_dir(create=create) / "selected_take.json"
        if path.is_symlink():
            raise WorkbenchError("The selected visual take pointer cannot be a symlink.")
        return path

    @staticmethod
    def _read_layer_json(path: Path) -> Any:
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_LAYER_JSON_BYTES + 1)
        except OSError as exc:
            raise WorkbenchError("The layer JSON could not be read.", 500) from exc
        if len(raw) > MAX_LAYER_JSON_BYTES:
            raise WorkbenchError("Layer JSON is larger than the 1 MB workbench limit.", 413)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError, RecursionError) as exc:
            raise WorkbenchError("Layer file is not valid UTF-8 JSON.") from exc

    def _visual_take_document(self, take_id: str, narration_data: dict[str, Any]) -> dict[str, Any]:
        path = self._visual_take_path(take_id)
        if not path.is_file() or path.is_symlink():
            raise WorkbenchError("The visual take manifest is unavailable.", 404)
        value = self._read_layer_json(path)
        try:
            return validate_visual_take(value, take_id, narration_data["segments"], self._project_root())
        except ValueError as exc:
            raise WorkbenchError(str(exc)) from exc

    def _visual_take_summary(
        self,
        take_id: str,
        narration_data: dict[str, Any],
        selected_take_id: str | None,
    ) -> dict[str, Any]:
        try:
            path = self._visual_take_path(take_id)
        except WorkbenchError as exc:
            return {
                "take_id": take_id,
                "filename": f"{take_id}.json",
                "selected": take_id == selected_take_id,
                "title": take_id,
                "creative_direction": "",
                "can_open": False,
                "status": "invalid",
                "error": str(exc),
            }
        base = {
            "take_id": take_id,
            "filename": path.name,
            "selected": take_id == selected_take_id,
            "can_open": False,
        }
        try:
            base["can_open"] = path.is_file() and not path.is_symlink() and path.stat().st_size <= MAX_LAYER_JSON_BYTES
        except OSError:
            pass
        try:
            document = self._visual_take_document(take_id, narration_data)
        except (WorkbenchError, OSError) as exc:
            return {**base, "title": take_id, "creative_direction": "", "status": "invalid", "error": str(exc)}

        by_id = {segment["id"]: segment for segment in narration_data["segments"]}
        entry_statuses = {
            segment_id: visual_segment_status(document["segments"].get(segment_id), segment, self._project_root())
            for segment_id, segment in by_id.items()
        }
        active_ids = {segment["id"] for segment in narration_data["segments"] if segment.get("status", "active") == "active"}
        missing_ids = sorted(active_ids - set(document["segments"]))
        active_statuses = [entry_statuses[segment_id] for segment_id in active_ids]
        if any(status == "invalid" for status in active_statuses):
            status = "invalid"
        elif any(item == "needs_review" for item in active_statuses):
            status = "needs_review"
        elif missing_ids or any(item in {"pending", "missing"} for item in active_statuses):
            status = "in_progress"
        else:
            status = "complete"
        return {
            **base,
            "title": document["title"],
            "creative_direction": document["creative_direction"],
            "status": status,
            "segment_statuses": entry_statuses,
            "missing_active_segment_ids": missing_ids,
            "active_segment_count": len(active_ids),
            "complete_active_segment_count": sum(entry_statuses[item] == "saved" for item in active_ids),
        }

    def visual_layer_payload(self, narration_data: dict[str, Any]) -> dict[str, Any]:
        selected_take_id: str | None = None
        selection_status = "none"
        try:
            pointer_path = self._selected_visual_take_path()
            if pointer_path.exists():
                if not pointer_path.is_file() or pointer_path.is_symlink():
                    raise WorkbenchError("Selected visual take pointer is not a regular file.")
                pointer = self._read_layer_json(pointer_path)
                if (
                    not isinstance(pointer, dict)
                    or set(pointer) != {"schema_version", "selected_take"}
                    or pointer.get("schema_version") != 1
                    or isinstance(pointer.get("schema_version"), bool)
                    or not isinstance(pointer.get("selected_take"), str)
                    or not pointer["selected_take"].endswith(".json")
                ):
                    raise WorkbenchError("Selected visual take pointer has an unsupported format.")
                selected_take_id = pointer["selected_take"][:-5]
                if not TAKE_ID_PATTERN.fullmatch(selected_take_id):
                    raise WorkbenchError("Selected visual take pointer contains an invalid take ID.")
                selection_status = "saved"
        except WorkbenchError:
            selection_status = "invalid"

        take_ids: list[str] = []
        try:
            folder = self._visual_layer_dir()
            if folder.is_dir():
                take_ids = sorted(
                    path.stem for path in folder.iterdir()
                    if path.suffix.lower() == ".json"
                    and path.name != "selected_take.json"
                    and TAKE_ID_PATTERN.fullmatch(path.stem)
                )
        except WorkbenchError:
            selection_status = "invalid"

        takes = [self._visual_take_summary(take_id, narration_data, selected_take_id) for take_id in take_ids]
        selected = next((item for item in takes if item["take_id"] == selected_take_id), None)
        if selected_take_id and selected is None:
            selected = {
                "take_id": selected_take_id,
                "filename": f"{selected_take_id}.json",
                "title": selected_take_id,
                "creative_direction": "",
                "selected": True,
                "can_open": False,
                "status": "missing",
            }
        if selection_status == "invalid":
            selected = {"take_id": None, "title": "Selection unavailable", "creative_direction": "", "status": "invalid", "selected": False, "can_open": False}
        return {
            "selected_take_id": selected_take_id,
            "selection_status": selection_status,
            "takes": takes,
            "selected_take": selected,
        }

    def visual_take_segment_payload(
        self,
        segment: dict[str, Any],
        layer: dict[str, Any],
        document: dict[str, Any] | None,
    ) -> dict[str, Any]:
        selected = layer.get("selected_take")
        if not selected or not selected.get("take_id"):
            return {"status": "none", "visual_intent": "", "renderer": None, "implementation": None}
        if document is None:
            return {"status": "invalid", "visual_intent": "", "renderer": None, "implementation": None}
        entry = document["segments"].get(segment["id"])
        status = visual_segment_status(entry, segment, self._project_root())
        if entry is None:
            status = "pending"
        return {
            "status": status,
            "visual_intent": entry["visual_intent"] if entry else "",
            "renderer": entry["renderer"] if entry else None,
            "implementation": entry["implementation"] if entry else None,
        }

    def create_visual_take(self, take_id: str, title: str, creative_direction: str, expected_hash: str) -> dict[str, Any]:
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
        try:
            return self._create_visual_take(take_id, title, creative_direction, expected_hash)
        finally:
            self.manifest_operation_lock.release()

    def _create_visual_take(self, take_id: str, title: str, creative_direction: str, expected_hash: str) -> dict[str, Any]:
        if not isinstance(title, str) or not title.strip() or len(title) > 160:
            raise WorkbenchError("Take title must be 1 to 160 characters.")
        if not isinstance(creative_direction, str) or not creative_direction.strip() or len(creative_direction) > 24_000:
            raise WorkbenchError("Creative direction must be 1 to 24,000 characters.")
        with self.lock:
            narration_data, current_hash = self.read_manifest()
            self._check_manifest_hash(expected_hash, current_hash)
            path = self._visual_take_path(take_id, create=True)
            if path.exists() or path.is_symlink():
                raise WorkbenchError("A visual take with this ID already exists. It was not overwritten.", 409)
            document = {
                "schema_version": 1,
                "take_id": take_id,
                "title": title.strip(),
                "creative_direction": creative_direction.strip(),
                "segments": {
                    segment["id"]: {
                        "visual_intent": "",
                        "source_text_sha256": text_hash(segment["text"]),
                        "renderer": None,
                        "implementation": None,
                        "library_reference": None,
                    }
                    for segment in narration_data["segments"]
                },
            }
            try:
                atomic_create_json(path, document)
                pointer_path = self._selected_visual_take_path(create=True)
                atomic_write_json(pointer_path, {"schema_version": 1, "selected_take": path.name})
            except FileExistsError as exc:
                raise WorkbenchError("A visual take with this ID already exists. It was not overwritten.", 409) from exc
            except OSError as exc:
                raise WorkbenchError(f"Could not create the visual take: {exc}", 500) from exc
            return {"relative_path": f"visual_layer/{path.name}", "state": self.state_payload()}

    def select_visual_take(self, take_id: str) -> dict[str, Any]:
        with self.lock:
            narration_data, _ = self.read_manifest()
            self._visual_take_document(take_id, narration_data)
            pointer_path = self._selected_visual_take_path(create=True)
            try:
                atomic_write_json(pointer_path, {"schema_version": 1, "selected_take": f"{take_id}.json"})
            except OSError as exc:
                raise WorkbenchError(f"Could not save selected visual take: {exc}", 500) from exc
            return self.state_payload()

    def open_visual_take(self, take_id: str) -> None:
        with self.lock:
            path = self._visual_take_path(take_id)
            if not path.is_file() or path.is_symlink():
                raise WorkbenchError("The visual take manifest is unavailable.", 404)
            if path.stat().st_size > MAX_LAYER_JSON_BYTES:
                raise WorkbenchError("Layer JSON is larger than the 1 MB workbench limit.", 413)
            self._open_layer_file(path, "visual take")

    @staticmethod
    def _open_layer_file(path: Path, label: str) -> None:
        try:
            if os.name == "nt":
                os.startfile(str(path))  # type: ignore[attr-defined]
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            else:
                subprocess.Popen(["xdg-open", str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
        except (OSError, AttributeError) as exc:
            raise WorkbenchError(f"Could not open the {label} in the default app: {exc}", 500) from exc

"""Repeatable, project-owned visual requests inside a whole-spine take."""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from workbench_common import WorkbenchError, atomic_create_json, atomic_write_json, text_hash
from workbench_layer_contracts import REQUEST_ID_PATTERN, RENDERERS, project_relative_path
from workbench_visual_takes import VisualTakeMixin


class VisualRequestsMixin(VisualTakeMixin):
    def _request_folder(self, take_id: str, segment_id: str, request_id: str, *, create: bool = False) -> Path:
        if not isinstance(request_id, str) or not REQUEST_ID_PATTERN.fullmatch(request_id):
            raise WorkbenchError("Invalid visual request ID.")
        root = self._project_root()
        relative = f"visual_layer/{take_id}/segments/{segment_id}/requests/{request_id}"
        try:
            project_relative_path(root, relative, "Visual request folder")
        except ValueError as exc:
            raise WorkbenchError(str(exc)) from exc
        folder = root / relative
        if create:
            try:
                folder.mkdir(parents=True, exist_ok=True)
            except OSError as exc:
                raise WorkbenchError(f"Could not create visual request folder: {exc}", 500) from exc
        return folder

    def _selected_request_context(self, segment_id: str) -> tuple[dict[str, Any], dict[str, Any], str]:
        data, _ = self.read_manifest()
        self.find_segment(data, segment_id)
        layer = self.visual_layer_payload(data)
        take_id = layer.get("selected_take_id")
        if not take_id or layer.get("selection_status") != "saved":
            raise WorkbenchError("Select a valid whole-video visual take first.")
        document = self._visual_take_document(take_id, data)
        return data, document, take_id

    def visual_requests_payload(self, take_id: str, segment_id: str, entry: dict[str, Any]) -> dict[str, Any]:
        items = []
        for request_id in entry.get("request_ids", []):
            try:
                folder = self._request_folder(take_id, segment_id, request_id)
                request_path, result_path = folder / "request.json", folder / "result.json"
                if request_path.is_symlink() or result_path.is_symlink():
                    raise ValueError("Request files cannot be symlinks.")
                brief = self._read_layer_json(request_path)
                result = self._read_layer_json(result_path)
                if not isinstance(brief, dict) or brief.get("request_id") != request_id or brief.get("take_id") != take_id or brief.get("segment_id") != segment_id:
                    raise ValueError("Request identity does not match its folder.")
                if not isinstance(brief.get("source_text_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", brief["source_text_sha256"]):
                    raise ValueError("Request narration hash is invalid.")
                if not isinstance(result, dict) or result.get("request_id") != request_id or result.get("status") not in {"requested", "in_progress", "completed", "failed"}:
                    raise ValueError("Result identity or status is invalid.")
                for key in ("implementation_path", "preview_path", "export_path"):
                    if result.get(key) is not None:
                        value = project_relative_path(self._project_root(), result[key], key)
                        if not value.startswith(folder.relative_to(self._project_root()).as_posix() + "/"):
                            raise ValueError(f"{key} must be inside this request folder.")
                if result["status"] == "completed" and not result.get("export_path"):
                    raise ValueError("Completed result needs a segment export path.")
                items.append({"request_id": request_id, "brief": brief.get("brief", ""), "renderer": brief.get("renderer"),
                              "source_text_sha256": brief["source_text_sha256"],
                              "references": brief.get("references", []), "result": result,
                              "sfx_path": f"{folder.relative_to(self._project_root()).as_posix()}/sfx.json" if (folder / "sfx.json").is_file() and not (folder / "sfx.json").is_symlink() else None})
            except (WorkbenchError, ValueError, OSError) as exc:
                items.append({"request_id": request_id, "error": str(exc), "result": {"status": "invalid"}})
        return {"requests": items, "selected_request_id": entry.get("selected_request_id")}

    def create_visual_request(self, segment_id: str, brief: str, renderer: str | None, references: list[Any], expected_hash: str) -> dict[str, Any]:
        if not isinstance(brief, str) or not brief.strip() or len(brief) > 24_000:
            raise WorkbenchError("Enter a visual brief of at most 24,000 characters.")
        if renderer is not None and (not isinstance(renderer, str) or renderer not in RENDERERS):
            raise WorkbenchError("Choose EffectCraft, Manim, GSAP, or no renderer preference.")
        if not isinstance(references, list) or len(references) > 20:
            raise WorkbenchError("Attach at most 20 library entries.")
        catalog = getattr(self, "catalog", None)
        clean_references = []
        for reference in references:
            if not isinstance(reference, dict) or set(reference) != {"visibility", "library", "entry_id", "note"}:
                raise WorkbenchError("Library reference fields are invalid.")
            visibility, library, entry_id, note = (reference[key] for key in ("visibility", "library", "entry_id", "note"))
            if (not all(isinstance(item, str) for item in (visibility, library, entry_id, note))
                or visibility not in {"public", "private"}
                or library not in {"visual_reference_library", "visual_elements_library", "visual_animations_library"}
                or not re.fullmatch(r"(?:REF|ELM|ANM)-[a-z0-9]+(?:-[a-z0-9]+)*", entry_id)
                or len(note) > 4000):
                raise WorkbenchError("Library reference or note is invalid.")
            if catalog is None or catalog.entry(visibility, library, entry_id) is None:
                raise WorkbenchError(f"Library entry {entry_id} is unavailable. Refresh the browser.")
            clean_references.append(reference)
        if len({(item["visibility"], item["library"], item["entry_id"]) for item in clean_references}) != len(clean_references):
            raise WorkbenchError("Attach each library entry only once per request.")
        with self.lock:
            data, digest = self.read_manifest()
            self._check_manifest_hash(expected_hash, digest)
            _, document, take_id = self._selected_request_context(segment_id)
            entry = document["segments"].get(segment_id)
            if entry is None:
                raise WorkbenchError("This narration segment is not in the take. Add its stable ID to the take JSON first.")
            ids = entry.get("request_ids", [])
            if len(ids) >= 500:
                raise WorkbenchError("This segment has reached the 500-request limit.", 413)
            number = max((int(item[4:]) for item in ids), default=0) + 1
            request_id = f"VIS-{number:03d}"
            folder = self._request_folder(take_id, segment_id, request_id, create=True)
            request_path = folder / "request.json"
            request_doc = {"schema_version": 1, "take_id": take_id, "segment_id": segment_id,
                           "request_id": request_id, "source_text_sha256": text_hash(self.find_segment(data, segment_id)[1]["text"]),
                           "brief": brief.strip(), "renderer": renderer, "references": clean_references}
            try:
                atomic_create_json(request_path, request_doc)
                atomic_create_json(folder / "result.json", {"schema_version": 1, "request_id": request_id, "status": "requested",
                                                               "implementation_path": None, "preview_path": None, "export_path": None})
            except FileExistsError as exc:
                raise WorkbenchError("Request ID already exists; nothing was overwritten.", 409) from exc
            except OSError as exc:
                raise WorkbenchError(f"Could not create visual request files: {exc}", 500) from exc
            entry["request_ids"] = [*ids, request_id]
            entry.setdefault("selected_request_id", None)
            try:
                atomic_write_json(self._visual_take_path(take_id), document)
            except OSError as exc:
                raise WorkbenchError(f"Request files were created but take index could not be updated: {exc}", 500) from exc
            return {"request_id": request_id, "state": self.state_payload()}

    def select_visual_request(self, segment_id: str, request_id: str) -> dict[str, Any]:
        with self.lock:
            _, document, take_id = self._selected_request_context(segment_id)
            entry = document["segments"].get(segment_id)
            if not entry or request_id not in entry.get("request_ids", []):
                raise WorkbenchError("Request is not part of this take and segment.", 404)
            item = next(item for item in self.visual_requests_payload(take_id, segment_id, entry)["requests"] if item["request_id"] == request_id)
            if item["result"]["status"] != "completed":
                raise WorkbenchError("Only a completed visual candidate can be selected.")
            if item["source_text_sha256"] != text_hash(self.find_segment(self.read_manifest()[0], segment_id)[1]["text"]):
                raise WorkbenchError("This candidate was planned against older narration. Create a new request or review the text first.")
            entry["selected_request_id"] = request_id
            entry["source_text_sha256"] = item["source_text_sha256"]
            try:
                atomic_write_json(self._visual_take_path(take_id), document)
            except OSError as exc:
                raise WorkbenchError(f"Could not select visual candidate: {exc}", 500) from exc
            return self.state_payload()

    def create_visual_sfx(self, segment_id: str, request_id: str) -> dict[str, Any]:
        with self.lock:
            _, document, take_id = self._selected_request_context(segment_id)
            if request_id not in document["segments"].get(segment_id, {}).get("request_ids", []):
                raise WorkbenchError("Request is not part of this take and segment.", 404)
            path = self._request_folder(take_id, segment_id, request_id) / "sfx.json"
            try:
                atomic_create_json(path, {"schema_version": 1, "take_id": take_id, "segment_id": segment_id,
                                          "request_id": request_id, "notes": "", "cues": []})
            except FileExistsError as exc:
                raise WorkbenchError("SFX plan already exists; it was not overwritten.", 409) from exc
            except OSError as exc:
                raise WorkbenchError(f"Could not create SFX plan: {exc}", 500) from exc
            return {"relative_path": path.relative_to(self._project_root()).as_posix(), "state": self.state_payload()}

    def open_visual_request_file(self, segment_id: str, request_id: str, filename: str) -> None:
        if filename not in {"request.json", "result.json", "sfx.json"}:
            raise WorkbenchError("Unsupported request file.")
        with self.lock:
            _, document, take_id = self._selected_request_context(segment_id)
            if request_id not in document["segments"].get(segment_id, {}).get("request_ids", []):
                raise WorkbenchError("Request is not part of this take and segment.", 404)
            path = self._request_folder(take_id, segment_id, request_id) / filename
            if not path.is_file() or path.is_symlink():
                raise WorkbenchError("Request file is unavailable.", 404)
            self._open_layer_file(path, "visual request file")

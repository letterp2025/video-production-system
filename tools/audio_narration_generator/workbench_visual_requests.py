"""Repeatable, project-owned visual requests inside a whole-spine take."""

from __future__ import annotations

import re
from datetime import datetime
from pathlib import Path
from typing import Any

from workbench_common import WorkbenchError, atomic_create_json, atomic_write_json, now_iso, text_hash
from workbench_layer_contracts import REQUEST_ID_PATTERN, RENDERERS, project_relative_path, visual_source_hash, visual_source_field
from workbench_visual_takes import VisualTakeMixin


class VisualRequestsMixin(VisualTakeMixin):
    _LEGACY_RESULT_FIELDS = {
        "schema_version", "request_id", "status", "implementation_path", "preview_path", "export_path",
    }
    _RESULT_FIELDS = {
        "schema_version", "take_id", "segment_id", "request_id", "source_text_sha256", "status",
        "implementation_path", "preview_path", "export_path", "provider", "updated_at", "completed_at", "error",
    }
    _VISUAL_RESULT_FIELDS = (_RESULT_FIELDS - {"source_text_sha256"}) | {"source_unit_sha256"}

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
        if segment_id not in {unit["id"] for unit in self._visual_units(data)}:
            raise WorkbenchError("Sequence unit not found.", 404)
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
                raw_result = self._read_layer_json(result_path)
                visual_only = brief.get("schema_version") == 2 if isinstance(brief, dict) else False
                source_field = "source_unit_sha256" if visual_only else "source_text_sha256"
                if (not isinstance(brief, dict) or brief.get("schema_version") not in {1, 2}
                    or brief.get("request_id") != request_id or brief.get("take_id") != take_id
                    or brief.get("segment_id") != segment_id):
                    raise ValueError("Request identity does not match its folder.")
                if not isinstance(brief.get(source_field), str) or not re.fullmatch(r"[0-9a-f]{64}", brief[source_field]):
                    raise ValueError("Request source hash is invalid.")
                result, legacy_result = self._validate_visual_result(raw_result, brief, folder)
                items.append({"request_id": request_id, "brief": brief.get("brief", ""), "renderer": brief.get("renderer"),
                              source_field: brief[source_field],
                              "references": brief.get("references", []), "result": result, "legacy_result": legacy_result,
                              "sfx_path": f"{folder.relative_to(self._project_root()).as_posix()}/sfx.json" if (folder / "sfx.json").is_file() and not (folder / "sfx.json").is_symlink() else None})
            except (WorkbenchError, ValueError, OSError) as exc:
                items.append({"request_id": request_id, "error": str(exc), "result": {"status": "invalid"}})
        return {"requests": items, "selected_request_id": entry.get("selected_request_id")}

    @staticmethod
    def _valid_timestamp(value: Any) -> bool:
        if not isinstance(value, str) or not value.strip() or len(value) > 80:
            return False
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00")).tzinfo is not None
        except ValueError:
            return False

    def _validate_visual_result(
        self, result: Any, request: dict[str, Any], folder: Path,
    ) -> tuple[dict[str, Any], bool]:
        if not isinstance(result, dict):
            raise ValueError("Result must be a JSON object.")
        status = result.get("status")
        if not isinstance(status, str) or status not in {"requested", "in_progress", "completed", "failed"}:
            raise ValueError("Result status is unsupported.")

        legacy = type(result.get("schema_version")) is int and result["schema_version"] == 1 and set(result) == self._LEGACY_RESULT_FIELDS
        if legacy:
            if result.get("request_id") != request["request_id"]:
                raise ValueError("Legacy result request ID does not match its request.")
        else:
            visual_only = request["schema_version"] == 2
            source_field = "source_unit_sha256" if visual_only else "source_text_sha256"
            if set(result) != (self._VISUAL_RESULT_FIELDS if visual_only else self._RESULT_FIELDS):
                raise ValueError("Result fields do not match the Visual Layer result contract.")
            if (type(result.get("schema_version")) is not int or result["schema_version"] != (3 if visual_only else 2)
                or result.get("take_id") != request["take_id"]
                or result.get("segment_id") != request["segment_id"]
                or result.get("request_id") != request["request_id"]
                or result.get(source_field) != request[source_field]):
                raise ValueError("Result identity or source-text hash does not match its request." if not visual_only else "Result identity or source-unit hash does not match its request.")
            if not self._valid_timestamp(result.get("updated_at")):
                raise ValueError("Result updated_at must be an ISO 8601 timestamp with a timezone.")
            provider = result.get("provider")
            if provider is not None and (not isinstance(provider, str) or not provider.strip() or len(provider) > 200):
                raise ValueError("Result provider must be null or a non-empty string of at most 200 characters.")
            error = result.get("error")
            if error is not None and (not isinstance(error, str) or len(error) > 4_000):
                raise ValueError("Result error must be null or text of at most 4000 characters.")
            completed_at = result.get("completed_at")
            if completed_at is not None and not self._valid_timestamp(completed_at):
                raise ValueError("Result completed_at must be null or an ISO 8601 timestamp with a timezone.")
            if status == "completed" and (completed_at is None or error is not None):
                raise ValueError("A completed result needs completed_at and must not contain an error.")
            if status == "failed" and (completed_at is not None or not isinstance(error, str) or not error.strip()):
                raise ValueError("A failed result needs an error and must not contain completed_at.")
            if status in {"requested", "in_progress"} and (completed_at is not None or error is not None):
                raise ValueError("An unfinished result must not contain completed_at or error.")

        root = self._project_root()
        request_prefix = folder.relative_to(root).as_posix() + "/"
        for key in ("implementation_path", "preview_path", "export_path"):
            value = result.get(key)
            if value is None:
                continue
            relative = project_relative_path(root, value, key)
            if not relative.startswith(request_prefix):
                raise ValueError(f"{key} must be inside this request folder.")
            candidate = root.joinpath(*relative.split("/"))
            try:
                candidate.resolve(strict=True).relative_to(root)
            except (OSError, ValueError) as exc:
                raise ValueError(f"{key} must point to an existing project file or folder.") from exc
            if key == "implementation_path":
                if not candidate.is_file() and not candidate.is_dir():
                    raise ValueError("implementation_path must point to a file or folder.")
            elif not candidate.is_file():
                raise ValueError(f"{key} must point to an existing file.")

        if status == "completed" and not result.get("export_path"):
            raise ValueError("A completed result needs an existing segment export file.")
        return result, legacy

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
            unit = next(unit for unit in self._visual_units(data) if unit["id"] == segment_id)
            entry = document["segments"].get(segment_id)
            if entry is None:
                entry = {"visual_intent": "", visual_source_field(unit): visual_source_hash(unit),
                         "renderer": None, "implementation": None, "library_reference": None}
                document["segments"][segment_id] = entry
            ids = entry.get("request_ids", [])
            if len(ids) >= 500:
                raise WorkbenchError("This segment has reached the 500-request limit.", 413)
            number = max((int(item[4:]) for item in ids), default=0) + 1
            request_id = f"VIS-{number:03d}"
            folder = self._request_folder(take_id, segment_id, request_id, create=True)
            request_path = folder / "request.json"
            source_field = visual_source_field(unit)
            request_doc = {"schema_version": 2 if unit["kind"] == "visual_only" else 1, "take_id": take_id, "segment_id": segment_id,
                           "request_id": request_id, source_field: visual_source_hash(unit),
                           "brief": brief.strip(), "renderer": renderer, "references": clean_references,
                           "task": (
                               "Create this segment's visual asset using the brief and optional references. Keep all outputs "
                               "inside this request folder. Do not edit request.json or narration_manifest.json. Update the paired "
                               f"result.json, preserving its take_id, segment_id, request_id, and {source_field}. Set status to "
                               "in_progress while working and update updated_at. On success, set status to completed, set completed_at, "
                               "and point export_path to an existing rendered segment file. On failure, set status to failed and explain "
                               "the issue in error. Use only project-relative paths for outputs."
                           )}
            try:
                atomic_create_json(request_path, request_doc)
                source_hash = request_doc[source_field]
                atomic_create_json(folder / "result.json", {
                    "schema_version": 3 if unit["kind"] == "visual_only" else 2,
                    "take_id": take_id,
                    "segment_id": segment_id,
                    "request_id": request_id,
                    source_field: source_hash,
                    "status": "requested",
                    "implementation_path": None,
                    "preview_path": None,
                    "export_path": None,
                    "provider": None,
                    "updated_at": now_iso(),
                    "completed_at": None,
                    "error": None,
                })
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
            unit = next(unit for unit in self._visual_units(self.read_manifest()[0]) if unit["id"] == segment_id)
            source_field = visual_source_field(unit)
            if item[source_field] != visual_source_hash(unit):
                raise WorkbenchError("This candidate was planned against an older source. Create a new request or review the unit first.")
            entry["selected_request_id"] = request_id
            entry[source_field] = item[source_field]
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

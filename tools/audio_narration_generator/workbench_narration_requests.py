"""Portable file handoff for narration-editing requests from any AI assistant."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import generate_narration as narration

from workbench_common import (
    AI_GUIDE_PATH,
    MAX_TEXT_CHARS,
    WorkbenchError,
    atomic_create_json,
    atomic_write_json,
    now_iso,
    text_hash,
)
from workbench_layer_contracts import project_relative_path


NARRATION_REQUEST_ID = re.compile(r"SCR-[0-9]{3,6}\Z")
MAX_NARRATION_REQUEST_BYTES = 1_000_000


class NarrationRequestsMixin:
    def _narration_request_folder(
        self, segment_id: str, request_id: str, *, create: bool = False,
    ) -> Path:
        if not narration.ID_PATTERN.fullmatch(segment_id):
            raise WorkbenchError("Invalid stable narration segment ID.")
        if not isinstance(request_id, str) or not NARRATION_REQUEST_ID.fullmatch(request_id):
            raise WorkbenchError("Invalid narration request ID.")
        relative = f"audio/narration_requests/{segment_id}/requests/{request_id}"
        try:
            project_relative_path(self._project_root(), relative, "Narration request folder")
        except ValueError as exc:
            raise WorkbenchError(str(exc)) from exc
        folder = self._project_root() / relative
        if create:
            try:
                folder.mkdir(parents=True, exist_ok=True)
                project_relative_path(self._project_root(), relative, "Narration request folder")
            except (OSError, ValueError) as exc:
                raise WorkbenchError(f"Could not safely create narration request folder: {exc}", 500) from exc
        return folder

    def _read_narration_json(self, path: Path, label: str) -> dict[str, Any]:
        if path.is_symlink() or not path.is_file():
            raise WorkbenchError(f"{label} is unavailable.", 404)
        try:
            if path.stat().st_size > MAX_NARRATION_REQUEST_BYTES:
                raise WorkbenchError(f"{label} is larger than the 1 MB workbench limit.", 413)
            value = json.loads(path.read_text(encoding="utf-8"))
        except WorkbenchError:
            raise
        except (OSError, UnicodeError, json.JSONDecodeError) as exc:
            raise WorkbenchError(f"{label} is not readable JSON: {exc}", 422) from exc
        if not isinstance(value, dict):
            raise WorkbenchError(f"{label} must contain a JSON object.", 422)
        return value

    def _narration_request_document(self, segment_id: str, request_id: str) -> dict[str, Any]:
        folder = self._narration_request_folder(segment_id, request_id)
        request = self._read_narration_json(folder / "request.json", "Narration request")
        if (type(request.get("schema_version")) is not int or request.get("schema_version") != 1
            or request.get("request_id") != request_id
            or request.get("segment_id") != segment_id):
            raise WorkbenchError("Narration request identity does not match its folder.", 422)
        digest = request.get("source_text_sha256")
        if not isinstance(digest, str) or not re.fullmatch(r"[0-9a-f]{64}", digest):
            raise WorkbenchError("Narration request source-text hash is invalid.", 422)
        context = request.get("context")
        if (not isinstance(context, dict) or context.get("segment_id") != segment_id
            or not isinstance(context.get("title"), str) or not isinstance(context.get("text"), str)
            or text_hash(context["text"]) != digest or not isinstance(context.get("note"), str)
            or any(context.get(key) is not None and not isinstance(context.get(key), str)
                   for key in ("previous_text", "next_text"))
            or not isinstance(request.get("task"), str)
            or not isinstance(request.get("project_context"), dict)
            or not isinstance(request.get("ai_guide"), dict)):
            raise WorkbenchError("Narration request context does not match its source-text hash.", 422)
        return request

    def _narration_result(self, segment_id: str, request_id: str) -> dict[str, Any]:
        folder = self._narration_request_folder(segment_id, request_id)
        result = self._read_narration_json(folder / "result.json", "Narration result")
        request = self._narration_request_document(segment_id, request_id)
        required = {
            "schema_version", "request_id", "segment_id", "source_text_sha256", "status",
            "proposed_text", "rationale", "provider", "completed_at", "error",
        }
        if set(result) != required:
            raise WorkbenchError("Narration result fields do not match the result JSON contract.", 422)
        if (type(result.get("schema_version")) is not int or result.get("schema_version") != 1
            or result.get("request_id") != request_id
            or result.get("segment_id") != segment_id
            or result.get("source_text_sha256") != request.get("source_text_sha256")):
            raise WorkbenchError("Narration result identity or source-text hash does not match its request.", 422)
        if not isinstance(result.get("status"), str) or result["status"] not in {"requested", "in_progress", "completed", "failed"}:
            raise WorkbenchError("Narration result has an unsupported status.", 422)
        if (not isinstance(result.get("proposed_text"), str) or len(result["proposed_text"]) > MAX_TEXT_CHARS
            or not isinstance(result.get("rationale"), str) or len(result["rationale"]) > 6_000
            or (result.get("provider") is not None and not isinstance(result.get("provider"), str))
            or (result.get("completed_at") is not None and not isinstance(result.get("completed_at"), str))
            or (result.get("error") is not None and not isinstance(result.get("error"), str))):
            raise WorkbenchError("Narration result contains invalid field values.", 422)
        if result["status"] == "completed":
            proposed = result.get("proposed_text")
            rationale = result.get("rationale")
            if not isinstance(proposed, str) or not proposed.strip() or len(proposed) > MAX_TEXT_CHARS:
                raise WorkbenchError("A completed narration result needs valid proposed_text.", 422)
            if not isinstance(rationale, str) or len(rationale) > 6_000:
                raise WorkbenchError("A completed narration result needs a valid rationale.", 422)
        return result

    def create_narration_request(
        self, segment_id: str, note: str, expected_hash: str,
    ) -> dict[str, Any]:
        if not isinstance(note, str) or not note.strip() or len(note) > 6_000:
            raise WorkbenchError("Add a wording note of at most 6,000 characters first.")
        with self.lock:
            self.ensure_project_manifest()
            data, digest = self.read_manifest()
            self._check_manifest_hash(expected_hash, digest)
            index, segment = self.find_segment(data, segment_id)
            project_manifest = self.project_manifest_payload()["manifest"]
            context = {
                "segment_id": segment_id,
                "title": segment.get("title", segment_id),
                "text": segment["text"],
                "note": note.strip(),
                "previous_text": self._neighbor_text(data, index - 1),
                "next_text": self._neighbor_text(data, index + 1),
            }
            try:
                guide = json.loads(AI_GUIDE_PATH.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError) as exc:
                raise WorkbenchError(f"The tracked AI guide could not be read: {exc}", 500) from exc

            parent = self._narration_request_folder(segment_id, "SCR-001").parent
            if parent.is_symlink():
                raise WorkbenchError("Narration request folders cannot be symlinks.", 403)
            try:
                existing = [
                    int(path.name[4:]) for path in parent.iterdir()
                    if path.is_dir() and not path.is_symlink()
                    and NARRATION_REQUEST_ID.fullmatch(path.name)
                ] if parent.exists() else []
            except OSError as exc:
                raise WorkbenchError(f"Could not inspect narration request history: {exc}", 500) from exc
            next_number = max(existing, default=0) + 1
            if next_number > 999_999:
                raise WorkbenchError("This segment has reached the narration request limit.", 413)
            request_id = f"SCR-{next_number:03d}"
            request = {
                "schema_version": 1,
                "request_id": request_id,
                "segment_id": segment_id,
                "created_at": now_iso(),
                "source_text_sha256": text_hash(segment["text"]),
                "task": (
                    "Suggest a complete replacement for this narration segment using the creator's note and "
                    "the supplied immediate context. Preserve the intended facts and meaning, keep the wording "
                    "natural to speak aloud, and do not edit narration_manifest.json or any other project file. "
                    "Use the supplied project context as creative direction. Write your response only to the paired "
                    "result.json, preserving its identity and source hash. "
                    "Set status to completed and fill proposed_text and rationale."
                ),
                "project_context": project_manifest,
                "context": context,
                "ai_guide": guide,
            }
            result = {
                "schema_version": 1,
                "request_id": request_id,
                "segment_id": segment_id,
                "source_text_sha256": request["source_text_sha256"],
                "status": "requested",
                "proposed_text": "",
                "rationale": "",
                "provider": None,
                "completed_at": None,
                "error": None,
            }
            if len(json.dumps(request, ensure_ascii=False).encode("utf-8")) > MAX_NARRATION_REQUEST_BYTES:
                raise WorkbenchError("The project context makes this narration request larger than 1 MB.", 413)
            folder = self._narration_request_folder(segment_id, request_id, create=True)
            try:
                atomic_create_json(folder / "request.json", request)
                atomic_create_json(folder / "result.json", result)
            except FileExistsError as exc:
                raise WorkbenchError("Narration request ID already exists; nothing was overwritten.", 409) from exc
            except OSError as exc:
                raise WorkbenchError(f"Could not create narration request files: {exc}", 500) from exc
            self.save_note(segment_id, note.strip())
            relative = (folder / "request.json").relative_to(self._project_root()).as_posix()
            return {"request_id": request_id, "relative_path": relative, "state": self.state_payload()}

    def narration_requests_payload(
        self, segment_id: str, work: dict[str, Any],
    ) -> list[dict[str, Any]]:
        if not narration.ID_PATTERN.fullmatch(segment_id):
            return []
        relative = f"audio/narration_requests/{segment_id}/requests"
        try:
            project_relative_path(self._project_root(), relative, "Narration requests")
            parent = self._project_root() / relative
            if not parent.exists():
                return []
            if parent.is_symlink() or not parent.is_dir():
                raise ValueError("Narration request history is not a safe folder.")
            suggestions = work.get("suggestions", [])
            imported = {
                item["request_id"]: item for item in suggestions
                if isinstance(item, dict) and isinstance(item.get("request_id"), str)
                and NARRATION_REQUEST_ID.fullmatch(item["request_id"])
            }
            imported_ids = set(work.get("imported_request_ids", []))
            items = []
            for folder in sorted(parent.iterdir(), key=lambda path: path.name):
                if not NARRATION_REQUEST_ID.fullmatch(folder.name):
                    continue
                request_id = folder.name
                try:
                    if folder.is_symlink() or not folder.is_dir():
                        raise ValueError("Request folder cannot be a symlink or non-folder.")
                    request = self._narration_request_document(segment_id, request_id)
                    result = self._narration_result(segment_id, request_id)
                    suggestion = imported.get(request_id)
                    items.append({
                        "request_id": request_id,
                        "relative_path": f"{relative}/{request_id}/request.json",
                        "created_at": request.get("created_at"),
                        "status": suggestion.get("status") if suggestion else "imported" if request_id in imported_ids else result["status"],
                        "result_status": result["status"],
                        "provider": result.get("provider"),
                        "suggestion_id": suggestion.get("id") if suggestion else None,
                        "error": result.get("error"),
                    })
                except (WorkbenchError, ValueError, OSError) as exc:
                    items.append({"request_id": request_id, "status": "invalid", "error": str(exc)})
            return items
        except (WorkbenchError, ValueError, OSError) as exc:
            return [{"request_id": "", "status": "invalid", "error": str(exc)}]

    def open_narration_request_file(self, segment_id: str, request_id: str, filename: str) -> None:
        if filename not in {"request.json", "result.json"}:
            raise WorkbenchError("Unsupported narration request file.")
        with self.lock:
            folder = self._narration_request_folder(segment_id, request_id)
            path = folder / filename
            if path.is_symlink() or not path.is_file():
                raise WorkbenchError("Narration request file is unavailable.", 404)
            self._open_layer_file(path, "narration request file")

    def narration_request_documents(
        self, segment_id: str, request_id: str,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        with self.lock:
            request = self._narration_request_document(segment_id, request_id)
            result = self._narration_result(segment_id, request_id)
            return request, result

    def save_narration_result(
        self, segment_id: str, request_id: str, result: dict[str, Any],
    ) -> None:
        with self.lock:
            folder = self._narration_request_folder(segment_id, request_id)
            request = self._narration_request_document(segment_id, request_id)
            output = {
                "schema_version": 1,
                "request_id": request_id,
                "segment_id": segment_id,
                "source_text_sha256": request["source_text_sha256"],
                "status": "completed",
                "proposed_text": result["proposed_text"],
                "rationale": result["rationale"],
                "provider": "Codex CLI",
                "completed_at": now_iso(),
                "error": None,
            }
            try:
                atomic_write_json(folder / "result.json", output)
            except OSError as exc:
                raise WorkbenchError(f"Could not save the Codex result JSON: {exc}", 500) from exc

    def set_narration_request_status(
        self, segment_id: str, request_id: str, status: str, error: str | None = None,
    ) -> None:
        with self.lock:
            folder = self._narration_request_folder(segment_id, request_id)
            request = self._narration_request_document(segment_id, request_id)
            output = {
                "schema_version": 1,
                "request_id": request_id,
                "segment_id": segment_id,
                "source_text_sha256": request["source_text_sha256"],
                "status": status,
                "proposed_text": "",
                "rationale": "",
                "provider": "Codex CLI",
                "completed_at": None,
                "error": error,
            }
            try:
                atomic_write_json(folder / "result.json", output)
            except OSError as exc:
                raise WorkbenchError(f"Could not update narration request status: {exc}", 500) from exc

    def refresh_narration_requests(self, segment_id: str) -> dict[str, Any]:
        with self.lock:
            data, _ = self.read_manifest()
            self.find_segment(data, segment_id)
            state = self.read_state()
            work = state["segments"].get(segment_id, {})
            known = {
                item["request_id"] for item in work.get("suggestions", [])
                if isinstance(item, dict) and isinstance(item.get("request_id"), str)
            }
            known.update(work.get("imported_request_ids", []))
            relative = f"audio/narration_requests/{segment_id}/requests"
            try:
                project_relative_path(self._project_root(), relative, "Narration requests")
                parent = self._project_root() / relative
                folders = list(parent.iterdir()) if parent.exists() else []
            except (WorkbenchError, ValueError, OSError) as exc:
                raise WorkbenchError(f"Could not read narration requests safely: {exc}", 422) from exc
            imported = 0
            for folder in folders:
                if not NARRATION_REQUEST_ID.fullmatch(folder.name) or folder.is_symlink() or not folder.is_dir():
                    continue
                request_id = folder.name
                if request_id in known:
                    continue
                try:
                    request = self._narration_request_document(segment_id, request_id)
                    result = self._narration_result(segment_id, request_id)
                except WorkbenchError:
                    continue
                if result["status"] != "completed":
                    continue
                context = request.get("context")
                if not isinstance(context, dict) or not isinstance(context.get("text"), str):
                    continue
                note = context.get("note", "")
                if not isinstance(note, str):
                    continue
                self.store_suggestion(
                    segment_id,
                    note,
                    {"segment_id": segment_id, "proposed_text": result["proposed_text"],
                     "rationale": result["rationale"], "provider": result.get("provider")},
                    context["text"],
                    request_id=request_id,
                )
                state = self.read_state()
                work = state["segments"].setdefault(segment_id, {"note": note, "suggestions": []})
                imported_ids = work.setdefault("imported_request_ids", [])
                if request_id not in imported_ids:
                    imported_ids.append(request_id)
                    self.write_state(state)
                known.add(request_id)
                imported += 1
            return {"imported": imported, "state": self.state_payload()}

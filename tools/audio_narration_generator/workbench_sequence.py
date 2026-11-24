"""Canonical project story order, separate from spoken narration."""

from __future__ import annotations

import json
import math
from pathlib import Path
from typing import Any

import generate_narration as narration
from workbench_common import WorkbenchError, atomic_create_json, atomic_write_json, sha256_bytes
from workbench_layer_contracts import MAX_LAYER_JSON_BYTES


def validate_sequence(value: Any, narration_data: dict[str, Any]) -> dict[str, Any]:
    if not isinstance(value, dict) or set(value) != {"schema_version", "units"} or type(value.get("schema_version")) is not int or value["schema_version"] != 1:
        raise ValueError("Sequence must contain schema_version 1 and units.")
    units = value["units"]
    if not isinstance(units, list) or len(units) > 2_000:
        raise ValueError("Sequence units must be a list of at most 2000 items.")
    narration_ids = {item["id"] for item in narration_data["segments"]}
    seen: set[str] = set()
    linked: set[str] = set()
    for unit in units:
        if not isinstance(unit, dict) or unit.get("kind") not in {"narration", "visual_only"}:
            raise ValueError("Each sequence unit needs a valid kind.")
        kind = unit["kind"]
        allowed = {"id", "kind", "duration_seconds", "narration_segment_id"} if kind == "narration" else {"id", "kind", "title", "duration_seconds", "note"}
        required = allowed - ({"note"} if kind == "visual_only" else set())
        if not required.issubset(unit) or not set(unit).issubset(allowed):
            raise ValueError("Sequence unit fields do not match its kind.")
        unit_id = unit["id"]
        if not isinstance(unit_id, str) or not narration.ID_PATTERN.fullmatch(unit_id) or unit_id in seen:
            raise ValueError("Sequence unit IDs must be valid and unique.")
        seen.add(unit_id)
        duration = unit["duration_seconds"]
        if isinstance(duration, bool) or not isinstance(duration, (int, float)) or not math.isfinite(duration) or not 0 < duration <= 86_400:
            raise ValueError(f"Sequence duration for {unit_id} must be a finite positive number up to 86400 seconds.")
        if kind == "narration":
            link = unit["narration_segment_id"]
            if link != unit_id or link not in narration_ids or link in linked:
                raise ValueError(f"Narration unit {unit_id} must link exactly once to an existing same-ID narration segment.")
            linked.add(link)
        else:
            if unit_id in narration_ids:
                raise ValueError(f"Visual-only unit {unit_id} collides with a narration ID.")
            if not isinstance(unit["title"], str) or not unit["title"].strip() or len(unit["title"]) > 160:
                raise ValueError(f"Visual-only unit {unit_id} needs a title of at most 160 characters.")
            if not isinstance(unit.get("note", ""), str) or len(unit.get("note", "")) > 6_000:
                raise ValueError(f"Visual-only unit {unit_id} has an invalid note.")
    return value


class SequenceMixin:
    def _sequence_path(self) -> Path:
        path = self.audio_root.parent.resolve(strict=True) / "sequence_manifest.json"
        if path.is_symlink():
            raise WorkbenchError("The sequence manifest cannot be a symlink.", 403)
        if path.exists() and not path.is_file():
            raise WorkbenchError("The sequence manifest path is not a file.", 409)
        return path

    def _initial_sequence(self, data: dict[str, Any]) -> dict[str, Any]:
        units = []
        for segment in data["segments"]:
            duration = None
            selected = data.get("selected_takes", {}).get(segment["id"])
            if selected:
                try:
                    import wave
                    with wave.open(str(self._safe_audio_path(selected)), "rb") as audio:
                        if audio.getframerate() > 0:
                            duration = audio.getnframes() / audio.getframerate()
                except (OSError, EOFError, wave.Error, WorkbenchError):
                    pass
            units.append({"id": segment["id"], "kind": "narration", "narration_segment_id": segment["id"],
                          "duration_seconds": round(duration or max(1.0, len(segment["text"].split()) / 2.5), 3)})
        return {"schema_version": 1, "units": units}

    def read_sequence(self, data: dict[str, Any]) -> tuple[dict[str, Any], str]:
        path = self._sequence_path()
        if not path.exists():
            self.ensure_sequence_manifest()
        try:
            raw = path.read_bytes()
            if len(raw) > MAX_LAYER_JSON_BYTES:
                raise ValueError("Sequence manifest exceeds the 1 MB limit.")
            value = validate_sequence(json.loads(raw.decode("utf-8")), data)
        except (OSError, UnicodeDecodeError, json.JSONDecodeError, ValueError) as exc:
            raise WorkbenchError(f"Sequence manifest needs review; it was not replaced: {exc}", 422) from exc
        return value, sha256_bytes(raw)

    def ensure_sequence_manifest(self) -> bool:
        with self.lock:
            data, _ = self.read_manifest()
            path = self._sequence_path()
            if path.exists():
                self.read_sequence(data)
                return False
            document = self._initial_sequence(data)
            validate_sequence(document, data)
            try:
                atomic_create_json(path, document)
                return True
            except FileExistsError:
                self.read_sequence(data)
                return False
            except OSError as exc:
                raise WorkbenchError(f"Could not initialize sequence manifest: {exc}", 500) from exc

    def sequence_units(self, data: dict[str, Any]) -> tuple[list[dict[str, Any]], str, list[str]]:
        document, digest = self.read_sequence(data)
        by_id = {item["id"]: item for item in data["segments"]}
        units = []
        linked = set()
        for position, unit in enumerate(document["units"], 1):
            copy = dict(unit)
            copy["position"] = position
            if unit["kind"] == "narration":
                segment = by_id[unit["id"]]
                copy["title"] = segment.get("title", segment["id"])
                copy["status"] = segment.get("status", "active")
                linked.add(unit["id"])
            else:
                copy["status"] = "active"
            units.append(copy)
        unlinked = [item["id"] for item in data["segments"] if item["id"] not in linked]
        return units, digest, unlinked

    def edit_sequence(self, action: str, body: dict[str, Any]) -> dict[str, Any]:
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit or narration operation is already running.", 409)
        try:
            with self.lock:
                data, manifest_digest = self.read_manifest()
                document, digest = self.read_sequence(data)
                if body.get("sequence_hash") != digest:
                    raise WorkbenchError("Sequence changed elsewhere. Reload before editing.", 409)
                units = document["units"]
                unit_id = body.get("unit_id")
                index = next((i for i, item in enumerate(units) if item["id"] == unit_id), None)
                if action == "add":
                    title = body.get("title")
                    if not isinstance(unit_id, str) or not isinstance(title, str):
                        raise WorkbenchError("Provide a visual unit ID and title.")
                    after_id = body.get("after_id")
                    after_index = next((i for i, item in enumerate(units) if item["id"] == after_id), None)
                    if after_id is not None and after_index is None:
                        raise WorkbenchError("The insertion point is no longer in the sequence.", 409)
                    units.insert(0 if after_id is None else after_index + 1, {"id": unit_id, "kind": "visual_only",
                        "title": title.strip(), "duration_seconds": body.get("duration_seconds"), "note": body.get("note", "")})
                elif action == "update":
                    if index is None:
                        raise WorkbenchError("Sequence unit not found.", 404)
                    updates = body.get("updates")
                    if not isinstance(updates, dict) or not set(updates).issubset({"title", "note", "duration_seconds"}):
                        raise WorkbenchError("Unsupported sequence edit.")
                    if units[index]["kind"] == "narration" and set(updates) - {"duration_seconds"}:
                        raise WorkbenchError("Edit narration titles in the narration layer.")
                    units[index].update(updates)
                elif action == "move":
                    target_id, placement = body.get("target_id"), body.get("placement")
                    target_index = next((i for i, item in enumerate(units) if item["id"] == target_id), None)
                    if index is None or target_index is None or index == target_index or placement not in {"before", "after"}:
                        raise WorkbenchError("Choose another sequence unit and a valid move direction.")
                    unit = units.pop(index)
                    target_index = next(i for i, item in enumerate(units) if item["id"] == target_id)
                    units.insert(target_index + (placement == "after"), unit)
                elif action == "reconcile":
                    if {unit["id"] for unit in units if unit["kind"] == "narration"} != {item["id"] for item in data["segments"]}:
                        raise WorkbenchError("Link every narration segment before reconciling playback order.", 409)
                elif action == "link":
                    if not isinstance(unit_id, str) or index is not None:
                        raise WorkbenchError("Narration unit is already linked.", 409)
                    if unit_id not in {item["id"] for item in data["segments"]}:
                        raise WorkbenchError("Narration segment not found.", 404)
                    units.append({"id": unit_id, "kind": "narration", "narration_segment_id": unit_id,
                                  "duration_seconds": body.get("duration_seconds", 3.0)})
                else:
                    raise WorkbenchError("Unsupported sequence action.")
                try:
                    validate_sequence(document, data)
                    raw = self._sequence_path().read_bytes()
                    if sha256_bytes(raw) != digest:
                        raise WorkbenchError("Sequence changed elsewhere. Reload before editing.", 409)
                    if action in {"move", "reconcile"}:
                        narrated = [unit["id"] for unit in units if unit["kind"] == "narration"]
                        linked = {item["id"] for item in data["segments"]}
                        if set(narrated) == linked:
                            by_id = {item["id"]: item for item in data["segments"]}
                            data["segments"] = [by_id[item_id] for item_id in narrated]
                            self._validate_candidate(data)
                            self._write_manifest(data, manifest_digest)
                    atomic_write_json(self._sequence_path(), document)
                except ValueError as exc:
                    raise WorkbenchError(str(exc)) from exc
                except OSError as exc:
                    raise WorkbenchError(f"Could not save sequence manifest: {exc}", 500) from exc
                return {"state": self.state_payload()}
        finally:
            self.manifest_operation_lock.release()

"""Project-local visual plan storage and validation."""

from __future__ import annotations

import json
import math
import os
import re
import subprocess
import sys
from pathlib import Path
from typing import Any

import generate_narration as narration
from workbench_common import (
    MAX_TEXT_CHARS, MAX_TITLE_CHARS, MAX_VISUAL_PLAN_BYTES,
    WorkbenchError, atomic_create_json, text_hash,
)


class VisualPlanMixin:
    def _visuals_dir(self, create: bool = False) -> Path:
        root = self.audio_root / "visuals"
        if root.is_symlink():
            raise WorkbenchError("The audio/visuals folder cannot be a symlink.")
        if not root.exists():
            if not create:
                return root
            try:
                root.mkdir()
            except FileExistsError:
                pass
            except OSError as exc:
                raise WorkbenchError(f"Could not create audio/visuals: {exc}", 500) from exc
        if root.is_symlink() or not root.is_dir():
            raise WorkbenchError("The audio/visuals folder must be a project-local directory.")
        try:
            root.resolve(strict=True).relative_to(self.audio_root.resolve(strict=True))
        except (OSError, ValueError) as exc:
            raise WorkbenchError("The visual plan folder must remain inside the selected audio folder.") from exc
        return root

    def _visual_plan_path(self, segment_id: str, create: bool = False) -> Path:
        if not isinstance(segment_id, str) or not narration.ID_PATTERN.fullmatch(segment_id):
            raise WorkbenchError("Invalid segment ID.")
        root = self._visuals_dir(create=create)
        path = root / f"{segment_id}.json"
        if path.is_symlink():
            raise WorkbenchError("A visual plan file cannot be a symlink.")
        if path.exists():
            if not path.is_file():
                raise WorkbenchError("The visual plan path is not a regular file.")
            try:
                path.resolve(strict=True).relative_to(root.resolve(strict=True))
            except (OSError, ValueError) as exc:
                raise WorkbenchError("The visual plan must remain inside audio/visuals.") from exc
        return path

    @staticmethod
    def _validate_visual_plan(plan: Any, segment_id: str, recipes: dict[str, str]) -> None:
        if not isinstance(plan, dict) or set(plan) != {"schema_version", "segment", "animation", "visual"}:
            raise ValueError("The plan must contain schema_version, segment, animation, and visual.")
        if isinstance(plan.get("schema_version"), bool) or plan.get("schema_version") != 1:
            raise ValueError("The visual plan schema version is unsupported.")
        segment = plan.get("segment")
        if not isinstance(segment, dict) or set(segment) != {"id", "title", "source_text_sha256"}:
            raise ValueError("The visual plan segment fields are invalid.")
        if segment.get("id") != segment_id:
            raise ValueError("The visual plan belongs to a different segment.")
        if not isinstance(segment.get("title"), str) or not segment["title"].strip() or len(segment["title"]) > MAX_TITLE_CHARS:
            raise ValueError("The visual plan segment title is invalid.")
        if not isinstance(segment.get("source_text_sha256"), str) or not re.fullmatch(r"[0-9a-f]{64}", segment["source_text_sha256"]):
            raise ValueError("The visual plan source-text hash is invalid.")

        animation = plan.get("animation")
        if not isinstance(animation, dict) or set(animation) != {"recipe_id", "recipe_title"}:
            raise ValueError("The visual plan animation reference is invalid.")
        recipe_id = animation.get("recipe_id")
        recipe_title = animation.get("recipe_title")
        if recipe_id is None:
            if recipe_title is not None:
                raise ValueError("A custom visual plan cannot name a library recipe.")
        elif (
            not isinstance(recipe_id, str)
            or not re.fullmatch(r"ANM-[A-Za-z0-9][A-Za-z0-9_-]{0,63}", recipe_id)
            or recipe_id not in recipes
            or not isinstance(recipe_title, str)
            or not recipe_title.strip()
            or len(recipe_title) > MAX_TITLE_CHARS
        ):
            raise ValueError("The selected animation recipe is unavailable or invalid.")

        visual = plan.get("visual")
        if not isinstance(visual, dict) or set(visual) != {"description", "start_seconds", "duration_seconds", "elements"}:
            raise ValueError("The visual plan fields are invalid.")
        if not isinstance(visual.get("description"), str) or len(visual["description"]) > MAX_TEXT_CHARS:
            raise ValueError("The visual description is invalid.")
        start = visual.get("start_seconds")
        duration = visual.get("duration_seconds")
        if isinstance(start, bool) or not isinstance(start, (int, float)) or not math.isfinite(start) or start < 0:
            raise ValueError("Visual start_seconds must be a non-negative finite number.")
        if duration is not None and (
            isinstance(duration, bool) or not isinstance(duration, (int, float))
            or not math.isfinite(duration) or duration < 0
        ):
            raise ValueError("Visual duration_seconds must be null or a non-negative finite number.")
        elements = visual.get("elements")
        if not isinstance(elements, list) or len(elements) > 500 or any(not isinstance(item, dict) for item in elements):
            raise ValueError("Visual elements must be a list of up to 500 objects.")

    def _read_visual_plan(self, path: Path) -> Any:
        try:
            with path.open("rb") as stream:
                raw = stream.read(MAX_VISUAL_PLAN_BYTES + 1)
        except OSError as exc:
            raise WorkbenchError("The visual plan could not be read.", 500) from exc
        if len(raw) > MAX_VISUAL_PLAN_BYTES:
            raise WorkbenchError("The visual plan is larger than the 1 MB workbench limit.", 413)
        try:
            return json.loads(raw.decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError) as exc:
            raise WorkbenchError("The visual plan is not valid UTF-8 JSON.") from exc

    def _visual_plan_summary(self, segment: dict[str, Any], recipes: dict[str, str]) -> dict[str, Any]:
        segment_id = segment["id"]
        relative_path = f"visuals/{segment_id}.json"
        try:
            path = self._visual_plan_path(segment_id)
        except WorkbenchError:
            return {"status": "invalid", "exists": False, "can_open": False, "relative_path": relative_path}
        if not path.exists():
            return {"status": "none", "exists": False, "can_open": False, "relative_path": relative_path}
        try:
            if path.is_symlink() or not path.is_file():
                raise WorkbenchError("The visual plan path is not a regular file.")
            if path.stat().st_size > MAX_VISUAL_PLAN_BYTES:
                return {"status": "invalid", "exists": True, "can_open": False, "relative_path": relative_path}
            plan = self._read_visual_plan(path)
            self._validate_visual_plan(plan, segment_id, recipes)
        except (OSError, WorkbenchError, ValueError):
            return {"status": "invalid", "exists": True, "can_open": True, "relative_path": relative_path}
        animation = plan["animation"]
        status = "needs_review" if plan["segment"]["source_text_sha256"] != text_hash(segment["text"]) else "saved"
        return {
            "status": status,
            "exists": True,
            "can_open": True,
            "relative_path": relative_path,
            "recipe_id": animation["recipe_id"],
            "recipe_title": animation["recipe_title"],
        }

    def create_visual_plan(self, segment_id: str, recipe_id: str | None, expected_hash: str) -> dict[str, Any]:
        if not self.manifest_operation_lock.acquire(blocking=False):
            raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
        try:
            with self.lock:
                data, current_hash = self.read_manifest()
                self._check_manifest_hash(expected_hash, current_hash)
                _, segment = self.find_segment(data, segment_id)
                recipes = {item["id"]: item["title"] for item in self._recipe_catalog()}
                if recipe_id is not None and not isinstance(recipe_id, str):
                    raise WorkbenchError("Choose a recipe from the Visual Animations Library or use a custom plan.")
                if recipe_id == "":
                    recipe_id = None
                if recipe_id is not None and recipe_id not in recipes:
                    raise WorkbenchError("Choose a recipe from the Visual Animations Library or use a custom plan.")
                recipe_path = self._visual_plan_path(segment_id, create=True)
                if recipe_path.exists() or recipe_path.is_symlink():
                    raise WorkbenchError("A visual plan already exists for this beat. Open it to review; it was not overwritten.", 409)
                segment_title = segment.get("title", segment_id)
                if not isinstance(segment_title, str) or not segment_title.strip() or len(segment_title) > MAX_TITLE_CHARS:
                    segment_title = segment_id
                plan = {
                    "schema_version": 1,
                    "segment": {
                        "id": segment_id,
                        "title": segment_title,
                        "source_text_sha256": text_hash(segment["text"]),
                    },
                    "animation": {
                        "recipe_id": recipe_id,
                        "recipe_title": recipes[recipe_id] if recipe_id else None,
                    },
                    "visual": {"description": "", "start_seconds": 0, "duration_seconds": None, "elements": []},
                }
                try:
                    atomic_create_json(recipe_path, plan)
                except FileExistsError as exc:
                    raise WorkbenchError("A visual plan already exists for this beat. Open it to review; it was not overwritten.", 409) from exc
                except OSError as exc:
                    raise WorkbenchError(f"Could not create the visual plan: {exc}", 500) from exc
                return {"relative_path": f"visuals/{segment_id}.json", "state": self.state_payload()}
        finally:
            self.manifest_operation_lock.release()

    def open_visual_plan(self, segment_id: str) -> None:
        with self.lock:
            data, _ = self.read_manifest()
            self.find_segment(data, segment_id)
            path = self._visual_plan_path(segment_id)
            if not path.is_file() or path.is_symlink():
                raise WorkbenchError("No safe visual plan file is available for this beat.", 404)
            if path.stat().st_size > MAX_VISUAL_PLAN_BYTES:
                raise WorkbenchError("The visual plan is larger than the 1 MB workbench limit.", 413)
            try:
                if os.name == "nt":
                    os.startfile(str(path))  # type: ignore[attr-defined]
                elif sys.platform == "darwin":
                    subprocess.Popen(["open", str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
                else:
                    subprocess.Popen(["xdg-open", str(path)], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, close_fds=True)
            except (OSError, AttributeError) as exc:
                raise WorkbenchError(f"Could not open the visual plan in the default app: {exc}", 500) from exc

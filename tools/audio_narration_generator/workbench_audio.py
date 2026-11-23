"""Selected take and assembled audio lookup for the local workbench."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import generate_narration as narration
from workbench_common import WorkbenchError


class AudioReadMixin:
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
            for folder in sorted(root.iterdir()):
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
                    paths.setdefault(key, path.relative_to(self.audio_root).as_posix())
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
                "folder_path": str((self.audio_root / Path(paths[key]).parent).resolve()) if key in paths else None,
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
        for folder in sorted(root.iterdir()):
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

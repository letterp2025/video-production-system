"""Tests for whole-spine visual takes and per-beat audio-layer mappings."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
from http.server import ThreadingHTTPServer
from pathlib import Path
from unittest import mock
from urllib.request import Request, urlopen

import workbench
import workbench_layer_mappings
import workbench_visual_takes
from workbench_layer_contracts import validate_audio_mapping, validate_project_music_manifest, validate_visual_take


class LayerProjectTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = self.root / "audio"
        self.audio.mkdir()
        self.manifest = self.audio / "narration_manifest.json"
        self.data = {
            "project": "layers-test",
            "project_status": "in_progress",
            "voice": {"reference_audio": "reference.wav", "reference_text": "A short reference transcript."},
            "voice_styles": {},
            "settings": {"speed": 1.0, "pause_ms": 350},
            "selected_takes": {},
            "segments": [
                {"id": "opening-hook", "title": "Opening hook", "status": "active", "text": "Start with a question."},
                {"id": "next-beat", "title": "Next beat", "status": "active", "text": "Then explain the result."},
                {"id": "inactive-beat", "title": "Inactive beat", "status": "inactive", "text": "Maybe use this later."},
            ],
        }
        self.write_manifest()
        self.project = workbench.Project(self.manifest)

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def create_take(self, take_id="v_layer_1"):
        digest = self.project.state_payload()["manifest_hash"]
        return self.project.create_visual_take(take_id, take_id.replace("_", " ").title(), "A coherent visual treatment across the full narration spine.", digest)

    def test_repeatable_requests_candidate_selection_and_sfx_stay_in_take(self):
        self.create_take("v_layer_1")
        self.project.catalog = mock.Mock()
        self.project.catalog.entry.return_value = {"id": "ELM-example"}
        digest = self.project.state_payload()["manifest_hash"]
        first = self.project.create_visual_request("opening-hook", "Retro text reveal", "gsap", [], digest)
        second = self.project.create_visual_request("opening-hook", "Try a different reveal", None,
            [{"visibility": "public", "library": "visual_elements_library", "entry_id": "ELM-example", "note": "Use only its palette"}], digest)
        self.assertEqual((first["request_id"], second["request_id"]), ("VIS-001", "VIS-002"))
        take = self.root / "visual_layer" / "v_layer_1.json"
        self.assertEqual(json.loads(take.read_text(encoding="utf-8"))["segments"]["opening-hook"]["request_ids"], ["VIS-001", "VIS-002"])
        folder = self.root / "visual_layer" / "v_layer_1" / "segments" / "opening-hook" / "requests" / "VIS-002"
        brief = json.loads((folder / "request.json").read_text(encoding="utf-8"))
        self.assertEqual(brief["references"][0]["note"], "Use only its palette")
        self.assertIn("paired result.json", brief["task"])
        self.assertNotIn(str(self.root), json.dumps(brief))
        scaffold = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        self.assertEqual(scaffold["schema_version"], 2)
        self.assertEqual((scaffold["take_id"], scaffold["segment_id"], scaffold["request_id"]),
                         ("v_layer_1", "opening-hook", "VIS-002"))
        self.assertEqual(scaffold["source_text_sha256"], brief["source_text_sha256"])
        self.assertEqual(scaffold["status"], "requested")
        self.project.create_visual_sfx("opening-hook", "VIS-002")
        self.assertTrue((folder / "sfx.json").is_file())
        self.assertFalse((folder.parent / "VIS-001" / "sfx.json").exists())
        with self.assertRaisesRegex(workbench.WorkbenchError, "Only a completed"):
            self.project.select_visual_request("opening-hook", "VIS-002")
        export = folder / "exports" / "segment.mp4"
        export.parent.mkdir()
        export.write_bytes(b"test")
        result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        result.update({"status": "completed", "export_path": export.relative_to(self.root).as_posix(),
                       "provider": "Codex", "updated_at": "2026-11-23T10:08:00+00:00",
                       "completed_at": "2026-11-23T10:08:00+00:00"})
        (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
        state = self.project.select_visual_request("opening-hook", "VIS-002")
        self.assertEqual(state["segments"][0]["visual_take_segment"]["selected_request_id"], "VIS-002")
        self.assertEqual(state["segments"][0]["visual_take_segment"]["status"], "saved")
        self.create_take("v_layer_2")
        self.assertEqual(self.project.state_payload()["segments"][0]["visual_take_segment"]["requests"], [])

    def test_library_reference_must_exist_and_result_paths_remain_confined(self):
        self.create_take()
        self.project.catalog = mock.Mock()
        self.project.catalog.entry.return_value = None
        digest = self.project.state_payload()["manifest_hash"]
        with self.assertRaisesRegex(workbench.WorkbenchError, "unavailable"):
            self.project.create_visual_request("opening-hook", "Use reference", None,
                [{"visibility": "private", "library": "visual_reference_library", "entry_id": "REF-example", "note": ""}], digest)
        made = self.project.create_visual_request("opening-hook", "Custom with no library", None, [], digest)
        folder = self.root / "visual_layer" / "v_layer_1" / "segments" / "opening-hook" / "requests" / made["request_id"]
        result = json.loads((folder / "result.json").read_text(encoding="utf-8"))
        result.update({"status": "completed", "export_path": "../escape.mp4",
                       "provider": "Codex", "updated_at": "2026-11-23T10:08:00+00:00",
                       "completed_at": "2026-11-23T10:08:00+00:00"})
        (folder / "result.json").write_text(json.dumps(result), encoding="utf-8")
        entry = self.project.state_payload()["segments"][0]["visual_take_segment"]
        self.assertEqual(entry["requests"][0]["result"]["status"], "invalid")
        with self.assertRaisesRegex(workbench.WorkbenchError, "Only a completed"):
            self.project.select_visual_request("opening-hook", made["request_id"])

    def test_visual_result_requires_matching_lineage_and_existing_export(self):
        self.create_take()
        digest = self.project.state_payload()["manifest_hash"]
        made = self.project.create_visual_request("opening-hook", "Create a simple title", None, [], digest)
        folder = self.root / "visual_layer" / "v_layer_1" / "segments" / "opening-hook" / "requests" / made["request_id"]
        result_path = folder / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result.update({"status": "completed", "export_path": f"{folder.relative_to(self.root).as_posix()}/exports/missing.mp4",
                       "provider": "Claude", "updated_at": "2026-11-23T10:08:00+00:00",
                       "completed_at": "2026-11-23T10:08:00+00:00"})

        result["segment_id"] = "next-beat"
        result_path.write_text(json.dumps(result), encoding="utf-8")
        entry = self.project.state_payload()["segments"][0]["visual_take_segment"]
        self.assertEqual(entry["requests"][0]["result"]["status"], "invalid")
        self.assertIn("identity or source-text hash", entry["requests"][0]["error"])

        result["segment_id"] = "opening-hook"
        result["source_text_sha256"] = "0" * 64
        result_path.write_text(json.dumps(result), encoding="utf-8")
        entry = self.project.state_payload()["segments"][0]["visual_take_segment"]
        self.assertEqual(entry["requests"][0]["result"]["status"], "invalid")
        self.assertIn("identity or source-text hash", entry["requests"][0]["error"])

        result["source_text_sha256"] = json.loads((folder / "request.json").read_text(encoding="utf-8"))["source_text_sha256"]
        result_path.write_text(json.dumps(result), encoding="utf-8")
        entry = self.project.state_payload()["segments"][0]["visual_take_segment"]
        self.assertEqual(entry["requests"][0]["result"]["status"], "invalid")
        self.assertIn("existing project file or folder", entry["requests"][0]["error"])

    def test_visual_result_tracks_progress_and_requires_failure_details(self):
        self.create_take()
        digest = self.project.state_payload()["manifest_hash"]
        made = self.project.create_visual_request("opening-hook", "Create a title", None, [], digest)
        folder = self.root / "visual_layer" / "v_layer_1" / "segments" / "opening-hook" / "requests" / made["request_id"]
        result_path = folder / "result.json"
        result = json.loads(result_path.read_text(encoding="utf-8"))
        result.update({"status": "in_progress", "provider": "Codex", "updated_at": "2026-11-23T10:05:00+00:00"})
        result_path.write_text(json.dumps(result), encoding="utf-8")
        item = self.project.state_payload()["segments"][0]["visual_take_segment"]["requests"][0]
        self.assertEqual(item["result"]["status"], "in_progress")
        self.assertEqual(item["result"]["provider"], "Codex")

        result.update({"status": "failed", "updated_at": "2026-11-23T10:06:00+00:00", "error": "Renderer setup failed."})
        result_path.write_text(json.dumps(result), encoding="utf-8")
        item = self.project.state_payload()["segments"][0]["visual_take_segment"]["requests"][0]
        self.assertEqual(item["result"]["status"], "failed")
        self.assertEqual(item["result"]["error"], "Renderer setup failed.")

        result["error"] = None
        result_path.write_text(json.dumps(result), encoding="utf-8")
        item = self.project.state_payload()["segments"][0]["visual_take_segment"]["requests"][0]
        self.assertEqual(item["result"]["status"], "invalid")
        self.assertIn("failed result needs an error", item["error"])

    def test_legacy_visual_result_remains_readable_but_paths_must_exist(self):
        self.create_take()
        digest = self.project.state_payload()["manifest_hash"]
        made = self.project.create_visual_request("opening-hook", "Legacy visual", None, [], digest)
        folder = self.root / "visual_layer" / "v_layer_1" / "segments" / "opening-hook" / "requests" / made["request_id"]
        export = folder / "exports" / "legacy.mp4"
        export.parent.mkdir()
        export.write_bytes(b"legacy")
        result_path = folder / "result.json"
        result_path.write_text(json.dumps({
            "schema_version": 1,
            "request_id": made["request_id"],
            "status": "completed",
            "implementation_path": None,
            "preview_path": None,
            "export_path": export.relative_to(self.root).as_posix(),
        }), encoding="utf-8")
        entry = self.project.state_payload()["segments"][0]["visual_take_segment"]
        self.assertEqual(entry["requests"][0]["result"]["status"], "completed")
        self.assertTrue(entry["requests"][0]["legacy_result"])
        selected = self.project.select_visual_request("opening-hook", made["request_id"])
        self.assertEqual(selected["segments"][0]["visual_take_segment"]["selected_request_id"], made["request_id"])

    def test_take_creation_creates_full_spine_skeleton_and_selects_without_touching_narration(self):
        manifest_before = self.manifest.read_bytes()
        result = self.create_take()
        path = self.root / "visual_layer" / "v_layer_1.json"
        pointer = self.root / "visual_layer" / "selected_take.json"
        document = json.loads(path.read_text(encoding="utf-8"))
        self.assertEqual(result["relative_path"], "visual_layer/v_layer_1.json")
        self.assertEqual(set(document["segments"]), {segment["id"] for segment in self.data["segments"]})
        self.assertEqual(json.loads(pointer.read_text(encoding="utf-8")), {"schema_version": 1, "selected_take": "v_layer_1.json"})
        self.assertEqual(self.manifest.read_bytes(), manifest_before)
        self.assertEqual(result["state"]["visual_layer"]["selected_take_id"], "v_layer_1")
        self.assertEqual(result["state"]["visual_layer"]["selected_take"]["status"], "in_progress")
        self.assertEqual(result["state"]["segments"][0]["visual_take_segment"]["status"], "pending")
        self.assertNotIn(str(self.root), json.dumps(result["state"]))

    def test_take_switching_preserves_each_take_and_uses_no_library_requirement(self):
        self.create_take("v_layer_1")
        self.create_take("v_layer_2")
        first = self.root / "visual_layer" / "v_layer_1.json"
        second = self.root / "visual_layer" / "v_layer_2.json"
        first_before = first.read_bytes()
        second_before = second.read_bytes()
        result = self.project.select_visual_take("v_layer_1")
        self.assertEqual(result["visual_layer"]["selected_take_id"], "v_layer_1")
        self.assertEqual(first.read_bytes(), first_before)
        self.assertEqual(second.read_bytes(), second_before)
        with self.assertRaisesRegex(workbench.WorkbenchError, "already exists"):
            self.create_take("v_layer_1")

    def test_failed_selection_after_creation_preserves_take_and_explains_recovery(self):
        with mock.patch.object(workbench_visual_takes, "atomic_write_json", side_effect=OSError("selection unavailable")):
            with self.assertRaisesRegex(workbench.WorkbenchError, "was created, but could not be selected") as raised:
                self.create_take()
        self.assertIn("select this existing take", str(raised.exception))
        take_path = self.root / "visual_layer" / "v_layer_1.json"
        self.assertTrue(take_path.is_file())
        self.assertFalse((self.root / "visual_layer" / "selected_take.json").exists())
        self.assertIn("v_layer_1", [item["take_id"] for item in self.project.state_payload()["visual_layer"]["takes"]])
        self.assertEqual(self.project.select_visual_take("v_layer_1")["visual_layer"]["selected_take_id"], "v_layer_1")
        with self.assertRaisesRegex(workbench.WorkbenchError, "already exists"):
            self.create_take()

    def test_editing_one_take_does_not_change_an_alternative_or_legacy_plan(self):
        self.create_take("v_layer_1")
        self.create_take("v_layer_2")
        first = self.root / "visual_layer" / "v_layer_1.json"
        second = self.root / "visual_layer" / "v_layer_2.json"
        legacy = self.project.create_visual_plan("opening-hook", None, self.project.state_payload()["manifest_hash"])
        legacy_path = self.audio / "visuals" / "opening-hook.json"
        second_before = second.read_bytes()
        legacy_before = legacy_path.read_bytes()
        edited = json.loads(first.read_text(encoding="utf-8"))
        edited["segments"]["opening-hook"]["visual_intent"] = "Make only this take feel like a paper collage."
        first.write_text(json.dumps(edited, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(second.read_bytes(), second_before)
        self.assertEqual(legacy_path.read_bytes(), legacy_before)
        self.assertEqual(legacy["relative_path"], "visuals/opening-hook.json")

    def test_take_tracks_stable_ids_after_reorder_and_new_active_beat_is_pending(self):
        self.create_take()
        digest = self.project.state_payload()["manifest_hash"]
        self.project.reorder_segment("next-beat", "opening-hook", "before", digest)
        reordered = self.project.state_payload()
        self.assertEqual(reordered["segments"][0]["id"], "next-beat")
        self.assertEqual(reordered["segments"][0]["visual_take_segment"]["status"], "pending")
        digest = reordered["manifest_hash"]
        added = self.project.insert_segment("opening-hook", "A new beat", "A newly approved line.", "active", digest)
        inserted = next(item for item in added["state"]["segments"] if item["id"] == added["segment_id"])
        self.assertEqual(inserted["visual_take_segment"]["status"], "pending")
        selected = added["state"]["visual_layer"]["selected_take"]
        self.assertEqual(selected["missing_active_segment_ids"], [added["segment_id"]])

    def test_ready_implementation_is_project_confined_and_text_changes_need_review(self):
        self.create_take()
        take_path = self.root / "visual_layer" / "v_layer_1.json"
        take = json.loads(take_path.read_text(encoding="utf-8"))
        entry = take["segments"]["opening-hook"]
        entry.update({
            "visual_intent": "Animate a retro title card.",
            "renderer": "gsap",
            "implementation": {
                "folder": "visual_layer/v_layer_1/opening-hook",
                "entry_file": "visual_layer/v_layer_1/opening-hook/scene.js",
            },
        })
        scene = self.root / "visual_layer" / "v_layer_1" / "opening-hook" / "scene.js"
        scene.parent.mkdir(parents=True)
        scene.write_text("// Renderer code is referenced, never executed by the workbench.\n", encoding="utf-8")
        take_path.write_text(json.dumps(take, indent=2) + "\n", encoding="utf-8")
        self.assertEqual(self.project.state_payload()["segments"][0]["visual_take_segment"]["status"], "saved")
        original_is_symlink = Path.is_symlink

        def pretend_entry_is_symlink(candidate):
            return candidate == scene or original_is_symlink(candidate)

        with mock.patch.object(Path, "is_symlink", pretend_entry_is_symlink):
            with self.assertRaisesRegex(ValueError, "symlink"):
                validate_visual_take(take, "v_layer_1", self.data["segments"], self.root)
        current_hash = self.project.state_payload()["manifest_hash"]
        self.project.save_segment("opening-hook", {"text": "Start with a different question."}, current_hash)
        changed = self.project.state_payload()
        self.assertEqual(changed["segments"][0]["visual_take_segment"]["status"], "needs_review")
        self.assertEqual(changed["visual_layer"]["selected_take"]["status"], "needs_review")

    def test_invalid_take_path_is_reported_and_can_be_opened_for_repair(self):
        self.create_take()
        path = self.root / "visual_layer" / "v_layer_1.json"
        take = json.loads(path.read_text(encoding="utf-8"))
        take["segments"]["opening-hook"].update({
            "renderer": "manim",
            "implementation": {"folder": "../../outside", "entry_file": "../../outside/scene.py"},
        })
        path.write_text(json.dumps(take), encoding="utf-8")
        state = self.project.state_payload()
        self.assertEqual(state["visual_layer"]["selected_take"]["status"], "invalid")
        with mock.patch.object(self.project, "_open_layer_file") as open_file:
            self.project.open_visual_take("v_layer_1")
            open_file.assert_called_once_with(path, "visual take")
        with self.assertRaisesRegex(ValueError, "must stay inside"):
            validate_visual_take(take, "v_layer_1", self.data["segments"], self.root)

    def test_invalid_renderer_type_is_reported_as_a_validation_error(self):
        digest = self.project.state_payload()["manifest_hash"]
        self.project.create_visual_take("v_layer_1", "Retro", "A retro treatment.", digest)
        path = self.root / "visual_layer" / "v_layer_1.json"
        take = json.loads(path.read_text(encoding="utf-8"))
        take["segments"]["opening-hook"]["renderer"] = []
        path.write_text(json.dumps(take), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "renderer.*effectcraft"):
            validate_visual_take(take, "v_layer_1", self.data["segments"], self.root)

    def test_visual_take_runtime_and_schema_reject_empty_direction_and_oversized_library_ids(self):
        self.create_take()
        take = json.loads((self.root / "visual_layer" / "v_layer_1.json").read_text(encoding="utf-8"))
        schema_path = Path(workbench.__file__).resolve().parent / "visual_take.schema.json"
        schema = json.loads(schema_path.read_text(encoding="utf-8"))
        self.assertEqual(schema["properties"]["creative_direction"]["minLength"], 1)
        self.assertEqual(schema["properties"]["creative_direction"]["pattern"], r"\S")
        for direction in ("", "   "):
            take["creative_direction"] = direction
            with self.assertRaisesRegex(ValueError, "creative direction"):
                validate_visual_take(take, "v_layer_1", self.data["segments"], self.root)
        take["creative_direction"] = "Retro treatment."
        entry = take["segments"]["opening-hook"]
        reference_schema = schema["$defs"]["segment"]["properties"]["library_reference"]["oneOf"][1]["properties"]
        for key, limit in (("library", 120), ("entry_id", 160)):
            self.assertEqual(reference_schema[key]["maxLength"], limit)
            entry["library_reference"] = {"library": "custom", "entry_id": "title"}
            entry["library_reference"][key] = "x" * (limit + 1)
            with self.assertRaisesRegex(ValueError, "Library reference"):
                validate_visual_take(take, "v_layer_1", self.data["segments"], self.root)

    def test_visual_take_creation_rejects_invalid_id_and_stale_manifest_hash(self):
        digest = self.project.state_payload()["manifest_hash"]
        with self.assertRaisesRegex(workbench.WorkbenchError, "Take ID"):
            self.project.create_visual_take("../outside", "Invalid", "Direction", digest)
        with self.assertRaisesRegex(workbench.WorkbenchError, "changed in another editor"):
            self.project.create_visual_take("v_layer_1", "Take", "Direction", "0" * 64)
        self.assertFalse((self.root / "visual_layer").exists())

    def test_music_and_sfx_mappings_are_independent_atomic_and_text_aware(self):
        manifest_before = self.manifest.read_bytes()
        digest = self.project.state_payload()["manifest_hash"]
        music = self.project.create_audio_mapping("music", "opening-hook", digest)
        sfx = self.project.create_audio_mapping("sfx", "opening-hook", digest)
        music_path = self.audio / "music" / "opening-hook.json"
        sfx_path = self.audio / "sfx" / "opening-hook.json"
        self.assertEqual(music["relative_path"], "music/opening-hook.json")
        self.assertEqual(sfx["relative_path"], "sfx/opening-hook.json")
        self.assertEqual(json.loads(music_path.read_text(encoding="utf-8"))["cues"], [])
        self.assertEqual(self.manifest.read_bytes(), manifest_before)
        before = music_path.read_bytes()
        with self.assertRaisesRegex(workbench.WorkbenchError, "already exists"):
            self.project.create_audio_mapping("music", "opening-hook", digest)
        self.assertEqual(music_path.read_bytes(), before)
        refreshed = self.project.state_payload()
        self.assertEqual(refreshed["segments"][0]["music_mapping"]["status"], "saved")
        self.assertEqual(refreshed["segments"][0]["sfx_mapping"]["status"], "saved")

    def test_audio_mapping_cues_validate_project_paths_timing_and_gain(self):
        self.create_take()
        digest = self.project.state_payload()["manifest_hash"]
        self.project.create_audio_mapping("music", "opening-hook", digest)
        path = self.audio / "music" / "opening-hook.json"
        mapping = json.loads(path.read_text(encoding="utf-8"))
        mapping["cues"] = [{
            "asset_path": "assets/music/theme.wav",
            "start_seconds": 0,
            "source_offset_seconds": 1.5,
            "duration_seconds": 12,
            "gain_db": -6,
        }]
        validate_audio_mapping(mapping, "music", "opening-hook", self.root)
        path.write_text(json.dumps(mapping), encoding="utf-8")
        payload = self.project.state_payload()
        self.assertEqual(payload["segments"][0]["music_mapping"]["cue_count"], 1)
        self.assertEqual(payload["segments"][0]["music_mapping"]["status"], "saved")
        mapping["cues"][0]["asset_path"] = "../../outside.wav"
        with self.assertRaisesRegex(ValueError, "inside the video project"):
            validate_audio_mapping(mapping, "music", "opening-hook", self.root)
        path.write_text(json.dumps(mapping), encoding="utf-8")
        self.assertEqual(self.project.state_payload()["segments"][0]["music_mapping"]["status"], "invalid")

    def test_audio_mapping_text_change_requires_review_without_rewriting_file(self):
        digest = self.project.state_payload()["manifest_hash"]
        self.project.create_audio_mapping("sfx", "opening-hook", digest)
        path = self.audio / "sfx" / "opening-hook.json"
        before = path.read_bytes()
        self.project.save_segment("opening-hook", {"text": "The approved narration changed."}, digest)
        result = self.project.state_payload()
        self.assertEqual(result["segments"][0]["sfx_mapping"]["status"], "needs_review")
        self.assertEqual(path.read_bytes(), before)

    def test_project_music_manifest_is_project_wide_and_resolves_current_segment_titles(self):
        digest = self.project.state_payload()["manifest_hash"]
        legacy_path = self.audio / "music" / "opening-hook.json"
        legacy_path.parent.mkdir()
        legacy_path.write_text("legacy file remains", encoding="utf-8")
        legacy_before = legacy_path.read_bytes()
        created = self.project.create_project_music_manifest(digest)
        path = self.root / "audio" / "music" / "manifest.json"
        self.assertEqual(created["relative_path"], "audio/music/manifest.json")
        self.assertEqual(legacy_path.read_bytes(), legacy_before)
        self.assertEqual(json.loads(path.read_text(encoding="utf-8")), {
            "schema_version": 1, "layer": "music", "items": [],
        })
        path.write_text(json.dumps({
            "schema_version": 1,
            "layer": "music",
            "items": [{
                "id": "MUS-001", "title": "Opening theme", "asset_path": "assets/music/theme.wav",
                "start_segment_id": "opening-hook", "end_segment_id": "next-beat",
            }],
        }), encoding="utf-8")
        layer = self.project.state_payload()["music_layer"]
        self.assertEqual(layer["status"], "saved")
        self.assertEqual(layer["item_count"], 1)
        item = layer["items"][0]
        self.assertEqual(item["start_segment_id"], "opening-hook")
        self.assertEqual(item["start_segment_title"], "Opening hook")
        self.assertEqual(item["start_segment_position"], 1)
        self.assertEqual(item["end_segment_id"], "next-beat")
        self.assertEqual(item["end_segment_title"], "Next beat")
        self.assertEqual(item["end_segment_position"], 2)
        self.assertEqual(item["asset_path"], "assets/music/theme.wav")
        self.assertNotIn(str(self.root), json.dumps(layer))
        self.data["segments"][0]["title"] = "Retitled opening"
        self.write_manifest()
        refreshed_item = self.project.state_payload()["music_layer"]["items"][0]
        self.assertEqual(refreshed_item["start_segment_id"], "opening-hook")
        self.assertEqual(refreshed_item["start_segment_title"], "Retitled opening")
        digest = self.project.state_payload()["manifest_hash"]
        with self.assertRaisesRegex(workbench.WorkbenchError, "already exists"):
            self.project.create_project_music_manifest(digest)

    def test_project_music_manifest_rejects_stale_or_reverse_segment_anchors_and_unsafe_assets(self):
        valid = {
            "schema_version": 1, "layer": "music", "items": [{
                "id": "MUS-001", "title": "Theme", "start_segment_id": "opening-hook", "end_segment_id": "next-beat",
            }],
        }
        validate_project_music_manifest(valid, self.data["segments"], self.root)
        for update, message in (
            ({"start_segment_id": "removed-beat"}, "does not exist"),
            ({"start_segment_id": "next-beat", "end_segment_id": "opening-hook"}, "ends before it starts"),
            ({"asset_path": "../outside.wav"}, "stay inside"),
            ({"id": "MUS-001"}, "duplicated"),
        ):
            candidate = json.loads(json.dumps(valid))
            candidate["items"].append(dict(candidate["items"][0]))
            candidate["items"][0].update(update)
            if update == {"id": "MUS-001"}:
                candidate["items"] = [candidate["items"][0], {**candidate["items"][0], "title": "Second"}]
            with self.subTest(update=update), self.assertRaisesRegex(ValueError, message):
                validate_project_music_manifest(candidate, self.data["segments"], self.root)

    def test_malformed_oversized_and_symlinked_mappings_are_reported_invalid(self):
        digest = self.project.state_payload()["manifest_hash"]
        self.project.create_audio_mapping("music", "opening-hook", digest)
        path = self.audio / "music" / "opening-hook.json"
        path.write_text("{bad json", encoding="utf-8")
        self.assertEqual(self.project.state_payload()["segments"][0]["music_mapping"]["status"], "invalid")
        path.write_text(json.dumps({
            "schema_version": 1, "layer": "music", "segment_id": "opening-hook",
            "source_text_sha256": workbench.text_hash(self.data["segments"][0]["text"]), "cues": [],
        }), encoding="utf-8")
        original_is_symlink = Path.is_symlink

        def pretend_mapping_is_symlink(candidate):
            return candidate == path or original_is_symlink(candidate)

        with mock.patch.object(Path, "is_symlink", pretend_mapping_is_symlink):
            self.assertEqual(self.project.state_payload()["segments"][0]["music_mapping"]["status"], "invalid")
        with mock.patch.object(workbench_visual_takes, "MAX_LAYER_JSON_BYTES", 4), mock.patch.object(workbench_layer_mappings, "MAX_LAYER_JSON_BYTES", 4):
            mapping = self.project.state_payload()["segments"][0]["music_mapping"]
            self.assertEqual(mapping["status"], "invalid")
            self.assertFalse(mapping["can_open"])

    def test_concurrent_mapping_creates_never_overwrite(self):
        digest = self.project.state_payload()["manifest_hash"]
        barrier = threading.Barrier(2)
        outcomes = []

        def create():
            barrier.wait()
            try:
                outcomes.append(self.project.create_audio_mapping("sfx", "opening-hook", digest))
            except workbench.WorkbenchError as exc:
                outcomes.append(exc)

        threads = [threading.Thread(target=create) for _ in range(2)]
        for thread in threads:
            thread.start()
        for thread in threads:
            thread.join(timeout=5)
        self.assertEqual(sum(isinstance(item, dict) for item in outcomes), 1)
        self.assertEqual(sum(isinstance(item, workbench.WorkbenchError) for item in outcomes), 1)
        self.assertTrue((self.audio / "sfx" / "opening-hook.json").is_file())


class LayerHttpTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = self.root / "audio"
        self.audio.mkdir()
        self.manifest = self.audio / "narration_manifest.json"
        self.manifest.write_text(json.dumps({
            "project": "layer-http",
            "project_status": "in_progress",
            "voice": {"reference_audio": "reference.wav", "reference_text": "A short reference transcript."},
            "voice_styles": {},
            "settings": {"speed": 1.0, "pause_ms": 350},
            "selected_takes": {},
            "segments": [{"id": "beat-one", "title": "Beat one", "status": "active", "text": "First words."}],
        }), encoding="utf-8")
        self.project = workbench.Project(self.manifest)
        self.server = ThreadingHTTPServer(("127.0.0.1", 0), workbench.create_handler(self.project, None, "python"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.close_server)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def close_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def post(self, path, payload):
        request = Request(self.base + path, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
        with urlopen(request) as response:
            return response.status, json.loads(response.read())

    def test_layer_routes_create_select_and_open_confined_files(self):
        digest = self.project.state_payload()["manifest_hash"]
        status, result = self.post("/api/music/manifest/create", {"manifest_hash": digest})
        self.assertEqual(status, 201)
        self.assertEqual(result["relative_path"], "audio/music/manifest.json")
        with mock.patch.object(self.project, "_open_layer_file") as open_file:
            status, _ = self.post("/api/music/manifest/open", {})
            self.assertEqual(status, 200)
            open_file.assert_called_once_with(self.audio / "music" / "manifest.json", "project Music manifest")
        status, result = self.post("/api/visual-takes/create", {
            "take_id": "v_layer_1", "title": "Retro", "creative_direction": "Bold retro movement.", "manifest_hash": digest,
        })
        self.assertEqual(status, 201)
        self.assertEqual(result["state"]["visual_layer"]["selected_take_id"], "v_layer_1")
        status, result = self.post("/api/layers/music/create", {"segment_id": "beat-one", "manifest_hash": digest})
        self.assertEqual(status, 201)
        self.assertEqual(result["relative_path"], "music/beat-one.json")
        with mock.patch.object(self.project, "_open_layer_file") as open_file:
            status, _ = self.post("/api/layers/music/open", {"segment_id": "beat-one"})
            self.assertEqual(status, 200)
            open_file.assert_called_once_with(self.audio / "music" / "beat-one.json", "music mapping")
        status, result = self.post("/api/visual-takes/select", {"take_id": "v_layer_1"})
        self.assertEqual(status, 200)
        self.assertEqual(result["state"]["visual_layer"]["selected_take_id"], "v_layer_1")

    def test_visual_request_and_library_routes(self):
        digest = self.project.state_payload()["manifest_hash"]
        self.post("/api/visual-takes/create", {"take_id": "v_layer_1", "title": "Retro", "creative_direction": "Retro type.", "manifest_hash": digest})
        status, catalog = self.post("/api/visual-requests/create", {"segment_id": "beat-one", "brief": "Animate text", "renderer": "gsap", "references": [], "manifest_hash": digest})
        self.assertEqual(status, 201)
        self.assertEqual(catalog["request_id"], "VIS-001")
        self.assertEqual(catalog["state"]["segments"][0]["visual_take_segment"]["requests"][0]["brief"], "Animate text")
        with urlopen(self.base + "/api/library/entries") as response:
            self.assertIn("entries", json.loads(response.read()))
        with mock.patch.object(self.project, "_open_layer_file") as open_file:
            status, _ = self.post("/api/visual-requests/open", {"segment_id": "beat-one", "request_id": "VIS-001", "filename": "request.json"})
            self.assertEqual(status, 200)
            self.assertEqual(open_file.call_args.args[0].name, "request.json")

    def test_layer_routes_reject_traversal_and_invalid_segment_ids(self):
        digest = self.project.state_payload()["manifest_hash"]
        for route, payload in (
            ("/api/visual-takes/create", {"take_id": "../escape", "title": "Bad", "creative_direction": "Bad", "manifest_hash": digest}),
            ("/api/layers/sfx/create", {"segment_id": "../escape", "manifest_hash": digest}),
        ):
            request = Request(self.base + route, data=json.dumps(payload).encode("utf-8"), headers={"Content-Type": "application/json"})
            with self.assertRaises(Exception):
                urlopen(request)
        self.assertFalse((self.root / "visual_layer").exists())
        self.assertFalse((self.audio / "sfx").exists())


class LayerInterfaceContractTest(unittest.TestCase):
    def test_layer_workspace_markup_has_labels_status_and_narrow_layout_rules(self):
        tool_dir = Path(workbench.__file__).resolve().parent
        html = (tool_dir / "workbench_static" / "index.html").read_text(encoding="utf-8")
        css = (tool_dir / "workbench_static" / "styles.css").read_text(encoding="utf-8")
        app = (tool_dir / "workbench_static" / "app.js").read_text(encoding="utf-8")
        for element_id in (
            "visual-take-select", "visual-take-id", "visual-take-title-input", "visual-take-direction-input",
            "create-visual-take", "open-visual-take", "create-music-manifest", "open-music-manifest",
            "music-item-list", "music-manifest-status", "shared-narration-position", "shared-narration-id",
            "visual-request-list", "create-visual-request", "library-entry-list", "attach-library-entry",
        ):
            self.assertIn(f'id="{element_id}"', html)
        self.assertNotIn('id="create-music-mapping"', html)
        self.assertNotIn('id="music-layer-beat"', html)
        self.assertIn('role="tablist" aria-label="Production layers"', html)
        self.assertNotIn('id="tab-soundeffects-layer"', html)
        self.assertIn('aria-live="polite"', html)
        self.assertIn("@media (max-width: 720px)", css)
        self.assertIn("@media (max-width: 420px)", css)
        self.assertIn(".music-item-range { grid-template-columns: 1fr; }", css)
        self.assertIn(".shared-narration-context", css)
        self.assertIn("[hidden] { display: none !important; }", css)
        for preset in ("flow", "natural", "clearer", "shorter", "opening"):
            self.assertIn(f'data-note-preset="{preset}"', html)
            self.assertIn(f"  {preset}:", app)
        for preset in ("suggest", "text", "process", "different", "reference"):
            self.assertIn(f'data-visual-preset="{preset}"', html)
            self.assertIn(f"  {preset}:", app)
        self.assertIn('field.dispatchEvent(new Event("input", { bubbles: true }))', app)
        self.assertIn('if (preset === "reference" && !draftReferences.length)', app)
        self.assertIn(".prompt-starter-buttons { display: flex; flex-wrap: wrap;", css)
        self.assertIn("createTake.disabled = state.busy || isDirty() || !state.project?.segments.length;", app)
        self.assertIn("if (state.busy || isDirty()) return toast(\"Save beat changes before creating a visual take.\");", app)
        self.assertIn("if (isDirty()) return toast(\"Save beat changes before creating the project Music manifest.\");", app)
        self.assertIn("musicAnchor(\"Starts at the beginning of\"", app)
        self.assertIn("musicAnchor(\"Ends at the end of\"", app)
        self.assertNotIn("eval(", app)
        self.assertNotIn("new Function(", app)

    def test_layer_schema_files_are_valid_json(self):
        tool_dir = Path(workbench.__file__).resolve().parent
        for schema_name in (
            "visual_take.schema.json", "selected_visual_take.schema.json",
            "music_mapping.schema.json", "music_manifest.schema.json", "sfx_mapping.schema.json",
        ):
            with self.subTest(schema=schema_name):
                schema = json.loads((tool_dir / schema_name).read_text(encoding="utf-8"))
                self.assertEqual(schema["$schema"], "https://json-schema.org/draft/2020-12/schema")


if __name__ == "__main__":
    unittest.main()

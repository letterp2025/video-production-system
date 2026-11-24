"""Small filesystem tests for incremental planning and completed-project cleanup."""

import copy
import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest import mock

import numpy as np
import soundfile as sf

import generate_narration as narration


class NarrationWorkflowTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.manifest = self.root / "narration_manifest.json"
        self.segment = {"id": "opening-hook", "title": "Opening", "text": "Hello there."}
        self.data = {
            "project": "test-project", "project_status": "in_progress",
            "voice": {"reference_audio": "reference.wav", "reference_text": "Reference words."},
            "settings": {"speed": 1.0}, "selected_takes": {}, "segments": [self.segment],
        }
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")

    def add_take(self, name=None, selected=True):
        return self.add_take_for(self.segment, name=name, selected=selected)

    def add_take_for(self, segment, name=None, selected=True):
        name = name or f"{segment['id']}_take-001.wav"
        folder = narration.segment_folder(self.root, segment)
        folder.mkdir(parents=True, exist_ok=True)
        path = folder / name
        path.write_bytes(b"WAV test data")
        relative = path.relative_to(self.root).as_posix()
        narration.write_json(path.with_suffix(".json"), {
            "segment_id": segment["id"], "take": relative,
            "text_sha256": narration.segment_text_sha256(segment),
            "generation_fingerprint": narration.generation_fingerprint(segment, self.data, self.manifest),
        })
        if selected:
            self.data["selected_takes"][segment["id"]] = relative
            self.write_manifest()
        return path

    def command(self, *args):
        return subprocess.run(
            [sys.executable, str(Path(narration.__file__)), "--manifest", str(self.manifest), *args],
            text=True, capture_output=True,
        )

    def test_only_changed_text_or_settings_regenerate(self):
        self.add_take()
        self.assertIn("Segments to generate: (none)", self.command("--dry-run").stdout)
        self.segment["title"] = "New title"
        self.assertIn("Segments to generate: (none)", self.command("--dry-run").stdout)
        self.segment["text"] = "Changed words."
        self.write_manifest()
        self.assertIn("opening-hook (narration text changed)", self.command("--dry-run").stdout)
        self.segment["text"] = "Hello there."
        self.data["settings"]["speed"] = 1.1
        self.write_manifest()
        self.assertIn("opening-hook (voice or speech settings changed)", self.command("--dry-run").stdout)

    def test_order_changes_playback_without_regeneration(self):
        self.add_take()
        second = {"id": "second-beat", "title": "Second", "text": "Another line."}
        self.data["segments"].append(second)
        self.add_take_for(second)
        previous_hash = narration.segments_array_sha256(self.data)
        self.data["segments_sha256"] = previous_hash
        self.data["segments"] = [second, self.segment]
        self.write_manifest()
        self.assertEqual([s["id"] for s in narration.ordered_segments(self.data)], ["second-beat", "opening-hook"])
        self.assertNotEqual(previous_hash, narration.segments_array_sha256(self.data))
        output = self.command("--dry-run").stdout
        self.assertIn("Segments to generate: (none)", output)
        self.assertIn("Unchanged segments: second-beat, opening-hook", output)
        self.assertIn("Segment array hash: changed since last assembly", output)
        master = self.root / "assembled.wav"
        master.write_bytes(b"assembled")
        assembled_ids = []

        def assemble_spy(_audio_root, _project, segments, *_args):
            assembled_ids.extend(segment["id"] for segment in segments)
            return master, None, 24000, 1.0

        args = ["tool", "--manifest", str(self.manifest), "--assemble-only"]
        with mock.patch.object(sys, "argv", args), mock.patch.object(
            narration, "assemble_audio", side_effect=assemble_spy
        ):
            self.assertEqual(narration.main(), 0)
        self.assertEqual(assembled_ids, ["second-beat", "opening-hook"])
        saved = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(saved["segments_sha256"], narration.segments_array_sha256(saved))
        self.data["segments"][0]["order"] = 1
        self.write_manifest()
        self.assertIn("obsolete order field", self.command("--dry-run").stderr)

    def test_take_reviews_do_not_change_assembly_fingerprint(self):
        original_hash = narration.segments_array_sha256(self.data)
        self.segment["take_reviews"] = {
            "take-001": {"rating": "favorite", "note": "Best read so far."}
        }
        self.assertEqual(narration.segments_array_sha256(self.data), original_hash)
        self.segment["text"] = "A changed line."
        self.assertNotEqual(narration.segments_array_sha256(self.data), original_hash)

    def test_take_review_schema_is_validated(self):
        self.segment["take_reviews"] = {
            "take-001": {"rating": "favorite", "note": "Good pacing."}
        }
        self.write_manifest()
        self.assertEqual(self.command("--dry-run").returncode, 0)
        self.segment["take_reviews"]["take-001"]["rating"] = "maybe"
        self.write_manifest()
        self.assertIn("rating must be one of", self.command("--dry-run").stderr)

    def test_next_take_does_not_reuse_reviewed_or_pruned_numbers(self):
        folder = narration.segment_folder(self.root, self.segment)
        folder.mkdir(parents=True)
        self.segment["take_reviews"] = {"take-002": {"rating": "rejected"}}
        self.data["pruned_takes"] = [{
            "segment_id": "opening-hook",
            "take": "segments/Opening/opening-hook_take-003.wav",
        }]
        self.assertEqual(narration.next_take(folder, "opening-hook", self.data).name, "opening-hook_take-004.wav")

    def test_status_defaults_active_and_non_active_segments_are_not_auditioned(self):
        self.add_take()
        inactive = {"id": "inactive-beat", "status": "inactive", "title": "Inactive", "text": "Pause me."}
        deleted = {"id": "deleted-beat", "status": "deleted", "title": "Deleted", "text": "Drop me."}
        self.data["segments"].extend([inactive, deleted])
        self.add_take_for(inactive)
        self.add_take_for(deleted)
        self.assertEqual(narration.load_manifest(self.manifest)["segments"][0]["status"], "active")

        output = self.command("--dry-run").stdout
        self.assertIn("Segments to generate: (none)", output)
        self.assertIn("Inactive segments: inactive-beat", output)
        self.assertIn("Deleted segments: deleted-beat", output)
        self.assertNotEqual(self.command("--segment", "inactive-beat", "--dry-run").returncode, 0)
        self.assertNotEqual(self.command("--segment", "deleted-beat", "--dry-run").returncode, 0)
        inactive["status"] = "paused"
        self.write_manifest()
        self.assertIn("retired status 'paused'", self.command("--dry-run").stderr)

    def test_assembly_uses_only_active_segments(self):
        active = self.segment
        inactive = {"id": "inactive-beat", "status": "inactive", "title": "Inactive", "text": "Pause me."}
        deleted = {"id": "deleted-beat", "status": "deleted", "title": "Deleted", "text": "Drop me."}
        self.data["segments"].extend([inactive, deleted])
        self.add_take_for(active)
        self.add_take_for(inactive)
        self.add_take_for(deleted)
        master = self.root / "assembled.wav"
        master.write_bytes(b"assembled")
        assembled_ids = []

        def assemble_spy(_audio_root, _project, segments, *_args):
            assembled_ids.extend(segment["id"] for segment in segments)
            return master, None, 24000, 1.0

        args = ["tool", "--manifest", str(self.manifest), "--assemble-only"]
        with mock.patch.object(sys, "argv", args), mock.patch.object(
            narration, "assemble_audio", side_effect=assemble_spy
        ):
            self.assertEqual(narration.main(), 0)
        self.assertEqual(assembled_ids, ["opening-hook"])
        saved = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(saved["segments_sha256"], narration.segments_array_sha256(saved))

    def test_real_assembly_preserves_order_and_pause(self):
        first = self.add_take()
        second_segment = {"id": "second-beat", "title": "Second", "text": "Another line."}
        self.data["segments"].append(second_segment)
        second = self.add_take_for(second_segment)
        sample_rate = 24000
        frame_count = sample_rate // 10
        sf.write(first, np.full(frame_count, 0.25, dtype=np.float32), sample_rate)
        sf.write(second, np.full(frame_count, -0.25, dtype=np.float32), sample_rate)
        self.data["settings"].update({"pause_ms": 50, "review_sample_rate": 48000})
        self.write_manifest()

        result = self.command("--assemble-only")
        self.assertEqual(result.returncode, 0, result.stderr)
        masters = list((self.root / "assembled").glob("*_24000hz_mono.wav"))
        self.assertEqual(len(masters), 1)
        audio, rate = sf.read(masters[0])
        self.assertEqual(rate, sample_rate)
        self.assertEqual(len(audio), frame_count * 2 + sample_rate // 20)
        self.assertAlmostEqual(float(np.mean(audio[:frame_count])), 0.25, places=3)
        self.assertTrue(np.all(audio[frame_count:frame_count + sample_rate // 20] == 0))
        self.assertAlmostEqual(float(np.mean(audio[-frame_count:])), -0.25, places=3)
        saved = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(saved["segments_sha256"], narration.segments_array_sha256(saved))

    def test_prune_requires_completion_and_keeps_selected_take(self):
        keep = self.add_take()
        self.segment["take_reviews"] = {
            "take-002": {"rating": "favorite", "note": "Keep this alternate."},
            "take-003": {"rating": "acceptable", "note": "Older option."},
        }
        favorite = self.add_take("opening-hook_take-002.wav", selected=False)
        remove = self.add_take("opening-hook_take-003.wav", selected=False)
        inactive = {"id": "inactive-beat", "status": "inactive", "title": "Inactive", "text": "Keep my auditions."}
        deleted = {"id": "deleted-beat", "status": "deleted", "title": "Deleted", "text": "Discard my takes."}
        deleted["take_reviews"] = {"take-001": {"rating": "favorite", "note": "Deleted beat override."}}
        self.data["segments"].extend([inactive, deleted])
        inactive_keep = self.add_take_for(inactive)
        inactive_alt = self.add_take_for(inactive, "inactive-beat_take-002.wav", selected=False)
        deleted_keep = self.add_take_for(deleted)
        deleted_alt = self.add_take_for(deleted, "deleted-beat_take-002.wav", selected=False)
        orphan_folder = self.root / "segments" / "S99_removed"
        orphan_folder.mkdir()
        orphan = orphan_folder / "take-001.wav"
        orphan.write_bytes(b"old take")
        orphan.with_suffix(".json").write_text("{}", encoding="utf-8")
        unrelated = keep.parent / "notes.txt"
        unrelated.write_text("keep", encoding="utf-8")
        self.assertNotEqual(self.command("--prune-unused").returncode, 0)
        self.data["project_status"] = "complete"
        self.write_manifest()
        preview = self.command("--prune-unused", "--dry-run")
        self.assertEqual(preview.returncode, 0, preview.stderr)
        self.assertTrue(remove.exists())
        self.assertNotIn("pruned_takes", json.loads(self.manifest.read_text(encoding="utf-8")))
        result = self.command("--prune-unused")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertTrue(keep.exists())
        self.assertTrue(keep.with_suffix(".json").exists())
        self.assertTrue(favorite.exists())
        self.assertTrue(favorite.with_suffix(".json").exists())
        self.assertFalse(remove.exists())
        self.assertTrue(inactive_keep.exists())
        self.assertTrue(inactive_alt.exists())
        self.assertFalse(deleted_keep.exists())
        self.assertFalse(deleted_alt.exists())
        updated = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertNotIn("deleted-beat", updated["selected_takes"])
        self.assertEqual(next(item for item in updated["segments"] if item["id"] == "deleted-beat")["status"], "deleted")
        pruned = {record["take"]: record for record in updated["pruned_takes"]}
        removed_take = remove.relative_to(self.root).as_posix()
        self.assertIn(removed_take, pruned)
        self.assertEqual(pruned[removed_take]["segment_id"], "opening-hook")
        self.assertEqual(pruned[removed_take]["receipt"]["text_sha256"], narration.segment_text_sha256(self.segment))
        self.assertEqual(pruned[removed_take]["take_review"]["rating"], "acceptable")
        self.assertEqual(
            {item["path"] for item in pruned[removed_take]["files"]},
            {removed_take, remove.with_suffix(".json").relative_to(self.root).as_posix()},
        )
        self.assertIn(deleted_keep.relative_to(self.root).as_posix(), pruned)
        self.assertEqual(
            pruned[deleted_keep.relative_to(self.root).as_posix()]["take_review"]["rating"],
            "favorite",
        )
        self.assertIn(orphan.relative_to(self.root).as_posix(), pruned)
        self.assertNotIn(inactive_keep.relative_to(self.root).as_posix(), pruned)
        self.assertTrue(unrelated.exists())
        self.assertFalse(remove.exists())
        self.assertFalse(remove.with_suffix(".json").exists())
        self.assertFalse(orphan_folder.exists())
        self.assertEqual(len(list((self.root / "performance").glob("run_*.json"))), 1)
        repeat = self.command("--prune-unused")
        self.assertEqual(repeat.returncode, 0, repeat.stderr)
        repeated = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(repeated["pruned_takes"], updated["pruned_takes"])

    def test_normal_run_regenerates_changed_take(self):
        original = self.add_take()
        self.segment["take_reviews"] = {
            "take-001": {"rating": "favorite", "note": "Keep this preference."}
        }
        previous_assembly_hash = narration.segments_array_sha256(self.data)
        self.data["segments_sha256"] = previous_assembly_hash
        self.segment["text"] = "A revised line."
        self.write_manifest()
        (self.root / "reference.wav").write_bytes(b"stub")
        engine = mock.Mock()
        engine.preprocess_ref_audio_text.return_value = ("reference", "Reference words.")
        engine.infer_process.return_value = (np.zeros(240, dtype=np.float32), 24000, None)
        args = ["tool", "--manifest", str(self.manifest), "--generate-only"]
        with mock.patch.object(sys, "argv", args), mock.patch.object(
            narration, "load_f5_engine", return_value=(engine, object(), object(), "test", "stub")
        ):
            self.assertEqual(narration.main(), 0)
        updated = json.loads(self.manifest.read_text(encoding="utf-8"))
        selected = self.root / updated["selected_takes"]["opening-hook"]
        self.assertEqual(selected.name, "opening-hook_take-002.wav")
        self.assertTrue(original.exists())
        self.assertTrue(selected.exists())
        self.assertEqual(
            updated["segments"][0]["take_reviews"]["take-001"]["rating"],
            "favorite",
        )
        self.assertEqual(updated["segments"][0]["text_sha256"], narration.segment_text_sha256(self.segment))
        self.assertEqual(updated["segments_sha256"], previous_assembly_hash)

    def test_segment_voice_style_uses_its_reference_and_invalidates_old_take(self):
        reference = self.root / "hook-excited.wav"
        reference.write_bytes(b"reference")
        self.data["voice_styles"] = {
            "hook_excited": {
                "reference_audio": str(reference),
                "reference_text": "Hook reference words.",
            }
        }
        original = self.add_take()
        self.segment["voice_style"] = "hook_excited"
        self.write_manifest()
        self.assertIn(
            "opening-hook (voice or speech settings changed)",
            self.command("--dry-run").stdout,
        )

        engine = mock.Mock()
        engine.preprocess_ref_audio_text.return_value = ("processed reference", "Hook reference words.")
        engine.infer_process.return_value = (np.zeros(240, dtype=np.float32), 24000, None)
        args = ["tool", "--manifest", str(self.manifest), "--generate-only"]
        with mock.patch.object(sys, "argv", args), mock.patch.object(
            narration, "load_f5_engine", return_value=(engine, object(), object(), "test", "stub")
        ):
            self.assertEqual(narration.main(), 0)

        engine.preprocess_ref_audio_text.assert_called_once_with(str(reference), "Hook reference words.")
        updated = json.loads(self.manifest.read_text(encoding="utf-8"))
        selected = self.root / updated["selected_takes"]["opening-hook"]
        self.assertNotEqual(selected, original)
        receipt = json.loads(selected.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(receipt["voice_style"], "hook_excited")
        self.assertEqual(receipt["reference_audio_name"], "hook-excited.wav")

    def test_project_default_voice_overrides_manifest_fallback_and_segment_style_overrides_project(self):
        project_root = self.root / "video-project"
        audio_root = project_root / "audio"
        audio_root.mkdir(parents=True)
        manifest_path = audio_root / "narration_manifest.json"
        data = copy.deepcopy(self.data)
        data["voice_styles"] = {
            "warm": {"reference_audio": "references/warm.wav", "reference_text": "Warm style words."}
        }
        data["voice"]["reference_audio"] = "references/legacy.wav"
        data["voice"]["reference_text"] = "Legacy fallback words."
        data["segments"][0]["voice_style"] = None
        manifest_path.write_text(json.dumps(data), encoding="utf-8")
        project_manifest_path = project_root / "video_project.json"
        project_manifest = {
            "narration": {
                "default_voice": {
                    "reference_audio": "references/project-default.wav",
                    "reference_text": "Project voice words.",
                }
            }
        }
        project_manifest_path.write_text(json.dumps(project_manifest), encoding="utf-8")
        for filename in ("project-default.wav", "legacy.wav"):
            reference = project_root / "references" / filename
            reference.parent.mkdir(parents=True, exist_ok=True)
            reference.write_bytes(b"reference")
        warm_reference = audio_root / "references" / "warm.wav"
        warm_reference.parent.mkdir(parents=True, exist_ok=True)
        warm_reference.write_bytes(b"reference")

        engine = mock.Mock()
        engine.preprocess_ref_audio_text.return_value = ("processed reference", "Project voice words.")
        engine.infer_process.return_value = (np.zeros(240, dtype=np.float32), 24000, None)
        args = ["tool", "--manifest", str(manifest_path), "--generate-only"]
        with mock.patch.object(sys, "argv", args), mock.patch.object(
            narration, "load_f5_engine", return_value=(engine, object(), object(), "test", "stub")
        ):
            self.assertEqual(narration.main(), 0)

        engine.preprocess_ref_audio_text.assert_called_once_with(
            str(project_root / "references" / "project-default.wav"), "Project voice words."
        )
        saved = json.loads(manifest_path.read_text(encoding="utf-8"))
        first_take = audio_root / saved["selected_takes"]["opening-hook"]
        first_receipt = json.loads(first_take.with_suffix(".json").read_text(encoding="utf-8"))
        self.assertEqual(first_receipt["voice_style"], "project_default")

        changed_project_manifest = copy.deepcopy(project_manifest)
        changed_project_manifest["narration"]["default_voice"]["reference_text"] = "Changed project voice words."
        project_manifest_path.write_text(json.dumps(changed_project_manifest), encoding="utf-8")
        dry_run = subprocess.run(
            [sys.executable, str(Path(narration.__file__)), "--manifest", str(manifest_path), "--dry-run"],
            text=True, capture_output=True,
        )
        self.assertIn("opening-hook (voice or speech settings changed)", dry_run.stdout)

        saved["segments"][0]["voice_style"] = "warm"
        manifest_path.write_text(json.dumps(saved), encoding="utf-8")
        override_engine = mock.Mock()
        override_engine.preprocess_ref_audio_text.return_value = ("processed warm reference", "Warm style words.")
        override_engine.infer_process.return_value = (np.zeros(240, dtype=np.float32), 24000, None)
        with mock.patch.object(sys, "argv", args), mock.patch.object(
            narration, "load_f5_engine", return_value=(override_engine, object(), object(), "test", "stub")
        ):
            self.assertEqual(narration.main(), 0)
        override_engine.preprocess_ref_audio_text.assert_called_once_with(
            str(warm_reference), "Warm style words."
        )

    def test_invalid_project_default_voice_is_rejected(self):
        project_root = self.root / "invalid-project"
        audio_root = project_root / "audio"
        audio_root.mkdir(parents=True)
        manifest_path = audio_root / "narration_manifest.json"
        (project_root / "video_project.json").write_text(
            json.dumps({"narration": {"default_voice": {"reference_audio": "voice.wav"}}}),
            encoding="utf-8",
        )
        with self.assertRaisesRegex(ValueError, "reference_text"):
            narration.project_default_voice(manifest_path)


if __name__ == "__main__":
    unittest.main()

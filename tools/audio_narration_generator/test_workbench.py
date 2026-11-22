"""Tests for manifest editing, temporary notes, and confined local workbench routes."""

from __future__ import annotations

import json
import tempfile
import threading
import unittest
import wave
from pathlib import Path
from unittest import mock
from urllib.error import HTTPError
from urllib.request import Request, urlopen

import generate_narration as narration
import workbench


class ProjectTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.audio = self.root / "audio"
        self.audio.mkdir()
        self.manifest = self.audio / "narration_manifest.json"
        self.data = {
            "project": "test-project",
            "project_status": "in_progress",
            "custom_project_field": {"keep": True},
            "voice": {"reference_audio": "private/reference.wav", "reference_text": "Private voice transcript."},
            "voice_styles": {"warm": {"reference_audio": "private/warm.wav", "reference_text": "Warm transcript."}},
            "settings": {"speed": 1.0, "pause_ms": 350},
            "selected_takes": {},
            "segments": [
                {"id": "opening-hook", "title": "Opening hook", "status": "active", "text": "Start with a question.", "voice_style": "warm", "tts": {}, "custom_segment_field": "keep"},
                {"id": "next-beat", "title": "Next beat", "status": "active", "text": "Then explain the result.", "voice_style": None, "tts": {}},
            ],
        }
        self.write_manifest()
        self.project = workbench.Project(self.manifest)

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")

    def test_work_state_persists_separately_and_never_enters_generation_hash(self):
        before = narration.segments_array_sha256(self.data)
        self.project.save_note("opening-hook", "Give this line more context before the reveal.")
        after = narration.segments_array_sha256(self.data)
        self.assertEqual(before, after)
        self.assertTrue(self.project.work_path.is_file())
        self.assertTrue(self.project.work_path.is_relative_to(self.audio))
        self.assertEqual(workbench.Project(self.manifest).read_state()["segments"]["opening-hook"]["note"], "Give this line more context before the reveal.")
        saved_manifest = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertNotIn("note", saved_manifest["segments"][0])

    def test_full_work_queue_does_not_replace_existing_state(self):
        self.project.save_note("opening-hook", "Keep this saved note.")
        before = self.project.work_path.read_bytes()
        with mock.patch.object(workbench, "MAX_WORK_STATE_BYTES", len(before) + 10):
            with self.assertRaisesRegex(workbench.WorkbenchError, "queue is full"):
                self.project.save_note("opening-hook", "A" * 1_000)
        self.assertEqual(self.project.work_path.read_bytes(), before)

    def test_state_view_omits_private_voice_references_and_local_paths(self):
        payload = self.project.state_payload()
        encoded = json.dumps(payload)
        self.assertNotIn("reference.wav", encoded)
        self.assertNotIn("Private voice transcript", encoded)
        self.assertNotIn(str(self.root), encoded)
        self.assertEqual([item["id"] for item in payload["segments"]], ["opening-hook", "next-beat"])

    def test_state_includes_active_take_durations_for_playback_following(self):
        durations = {"opening-hook": 1.0, "next-beat": 0.5}
        for segment_id, duration in durations.items():
            relative = f"segments/{segment_id}/take-001.wav"
            path = self.audio / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            with wave.open(str(path), "wb") as audio:
                audio.setnchannels(1)
                audio.setsampwidth(2)
                audio.setframerate(8_000)
                audio.writeframes(b"\0\0" * round(duration * 8_000))
            self.data["selected_takes"][segment_id] = relative
        self.write_manifest()

        with mock.patch.object(narration, "take_problem", return_value=None):
            payload = self.project.state_payload()

        self.assertEqual(payload["pause_ms"], 350)
        self.assertEqual([item["duration_seconds"] for item in payload["segments"]], [1.0, 0.5])

    def test_save_edits_known_fields_preserves_unknown_fields_and_array_order(self):
        digest = self.project.state_payload()["manifest_hash"]
        result = self.project.save_segment("opening-hook", {
            "title": "A clearer opening", "text": "Here is the revised opening.", "status": "inactive",
            "voice_style": None, "tts": {"speed": 1.12},
        }, digest)
        saved = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual([s["id"] for s in saved["segments"]], ["opening-hook", "next-beat"])
        self.assertEqual(saved["custom_project_field"], {"keep": True})
        self.assertEqual(saved["segments"][0]["custom_segment_field"], "keep")
        self.assertEqual(saved["segments"][0]["voice_style"], None)
        self.assertEqual(saved["segments"][0]["tts"], {"speed": 1.12})
        self.assertEqual(saved["segments"][0]["status"], "inactive")
        self.assertEqual(result["manifest_hash"], result["state"]["manifest_hash"])

    def test_reorder_moves_manifest_objects_without_changing_take_fingerprints(self):
        self.data["segments"].append({"id": "last-beat", "status": "deleted", "text": "Retired line."})
        self.write_manifest()
        before = narration.generation_fingerprint(self.data["segments"][0], self.data, self.manifest)
        old_array_hash = narration.segments_array_sha256(self.data)
        digest = self.project.state_payload()["manifest_hash"]
        result = self.project.reorder_segment("opening-hook", "last-beat", "after", digest)
        saved = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual([item["id"] for item in saved["segments"]], ["next-beat", "last-beat", "opening-hook"])
        self.assertEqual(saved["segments"][-1]["custom_segment_field"], "keep")
        self.assertEqual(narration.generation_fingerprint(saved["segments"][-1], saved, self.manifest), before)
        self.assertNotEqual(narration.segments_array_sha256(saved), old_array_hash)
        self.assertEqual(result["manifest_hash"], workbench.sha256_bytes(self.manifest.read_bytes()))
        with self.assertRaisesRegex(workbench.WorkbenchError, "changed in another editor"):
            self.project.reorder_segment("opening-hook", "next-beat", "before", digest)

    def test_reorder_rejects_invalid_target_without_writing(self):
        before = self.manifest.read_bytes()
        digest = self.project.state_payload()["manifest_hash"]
        with self.assertRaisesRegex(workbench.WorkbenchError, "not found"):
            self.project.reorder_segment("opening-hook", "missing", "before", digest)
        with self.assertRaisesRegex(workbench.WorkbenchError, "valid move direction"):
            self.project.reorder_segment("opening-hook", "next-beat", "middle", digest)
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_title_edit_preserves_unchanged_tts_number_and_take_fingerprint(self):
        self.data["segments"][0]["tts"] = {"speed": 1.0}
        self.write_manifest()
        before = narration.generation_fingerprint(self.data["segments"][0], self.data, self.manifest)
        digest = self.project.state_payload()["manifest_hash"]
        self.project.save_segment("opening-hook", {
            "title": "New title", "tts": {"speed": 1},
        }, digest)
        saved = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertIsInstance(saved["segments"][0]["tts"]["speed"], float)
        self.assertEqual(
            narration.generation_fingerprint(saved["segments"][0], saved, self.manifest),
            before,
        )

    def test_manifest_conflicts_are_rejected_and_invalid_values_do_not_write(self):
        digest = self.project.state_payload()["manifest_hash"]
        self.manifest.write_text(self.manifest.read_text(encoding="utf-8") + " ", encoding="utf-8")
        with self.assertRaisesRegex(workbench.WorkbenchError, "changed in another editor"):
            self.project.save_segment("opening-hook", {"text": "No overwrite."}, digest)
        data_before = self.manifest.read_bytes()
        current_hash = workbench.sha256_bytes(data_before)
        with self.assertRaisesRegex(workbench.WorkbenchError, "positive"):
            self.project.save_segment("opening-hook", {"tts": {"nfe_step": 0}}, current_hash)
        self.assertEqual(self.manifest.read_bytes(), data_before)

    def test_manifest_replace_failure_keeps_original_and_reports_error(self):
        before = self.manifest.read_bytes()
        digest = self.project.state_payload()["manifest_hash"]
        with mock.patch.object(workbench.os, "replace", side_effect=PermissionError("file is open")):
            with self.assertRaisesRegex(workbench.WorkbenchError, "Could not save narration manifest"):
                self.project.save_segment("opening-hook", {"text": "A revised line."}, digest)
        self.assertEqual(self.manifest.read_bytes(), before)
        self.assertEqual(list(self.audio.glob(".narration_manifest.*.tmp")), [])

    def test_suggestion_acceptance_requires_matching_base_text_and_updates_only_on_accept(self):
        context, _ = self.project.codex_context("opening-hook", "Make it less abrupt.")
        proposal = {"segment_id": "opening-hook", "proposed_text": "Let's start with a question.", "rationale": "Adds a natural lead-in."}
        suggestion = self.project.store_suggestion("opening-hook", "Make it less abrupt.", proposal, context["text"])
        unchanged = json.loads(self.manifest.read_text(encoding="utf-8"))["segments"][0]["text"]
        self.assertEqual(unchanged, "Start with a question.")
        current_hash = self.project.state_payload()["manifest_hash"]
        self.project.accept_suggestion("opening-hook", suggestion["id"], current_hash)
        updated = json.loads(self.manifest.read_text(encoding="utf-8"))
        self.assertEqual(updated["segments"][0]["text"], proposal["proposed_text"])
        self.assertEqual(updated["segments"][0]["id"], "opening-hook")
        saved_state = self.project.read_state()["segments"]["opening-hook"]["suggestions"][0]
        self.assertEqual(saved_state["status"], "accepted")

    def test_pending_suggestion_becomes_stale_if_manifest_text_changes(self):
        context, _ = self.project.codex_context("opening-hook", "Clarify it.")
        proposal = {"segment_id": "opening-hook", "proposed_text": "Try a clearer line.", "rationale": "Clarifies."}
        suggestion = self.project.store_suggestion("opening-hook", "Clarify it.", proposal, context["text"])
        self.data["segments"][0]["text"] = "Edited outside the workbench."
        self.write_manifest()
        current_state = self.project.state_payload()
        self.assertEqual(current_state["segments"][0]["work"]["suggestions"][0]["status"], "stale")
        saved_status = self.project.read_state()["segments"]["opening-hook"]["suggestions"][0]["status"]
        self.assertEqual(saved_status, "stale")
        with self.assertRaisesRegex(workbench.WorkbenchError, "no longer pending"):
            self.project.accept_suggestion("opening-hook", suggestion["id"], current_state["manifest_hash"])

    def test_result_is_marked_stale_if_manifest_changes_while_codex_is_responding(self):
        context, _ = self.project.codex_context("opening-hook", "Clarify this line.")
        self.data["segments"][0]["text"] = "Edited while Codex was responding."
        self.write_manifest()
        suggestion = self.project.store_suggestion(
            "opening-hook", "Clarify this line.",
            {"segment_id": "opening-hook", "proposed_text": "A new line.", "rationale": "Clearer."},
            context["text"],
        )
        self.assertEqual(suggestion["status"], "stale")

    def test_assistant_context_contains_only_selected_and_adjacent_script_fields(self):
        context, guide = self.project.codex_context("opening-hook", "Improve the start.")
        prompt = workbench.build_codex_prompt(guide, context)
        self.assertIn("Start with a question.", prompt)
        self.assertIn("Then explain the result.", prompt)
        self.assertIn("Improve the start.", prompt)
        self.assertNotIn("reference.wav", prompt)
        self.assertNotIn("Private voice transcript", prompt)
        self.assertNotIn(str(self.root), prompt)
        self.assertNotIn("custom_project_field", prompt)

    def test_codex_adapter_is_ephemeral_read_only_and_parses_structured_output(self):
        captured = {}

        def fake_run(command, **kwargs):
            captured["command"] = command
            captured["prompt"] = kwargs["input"]
            captured["cwd"] = Path(kwargs["cwd"])
            output_file = Path(command[command.index("--output-last-message") + 1])
            output_file.write_text(json.dumps({
                "segment_id": "opening-hook", "proposed_text": "A better spoken line.", "rationale": "More natural."
            }), encoding="utf-8")
            return mock.Mock(returncode=0, stdout="", stderr="")

        with mock.patch.object(workbench.subprocess, "run", side_effect=fake_run):
            result = workbench.run_codex_suggestion("codex", self.project, "opening-hook", "Smooth this out.")
        self.assertEqual(result["proposed_text"], "A better spoken line.")
        self.assertIn("--ephemeral", captured["command"])
        self.assertIn("--ignore-user-config", captured["command"])
        self.assertEqual(captured["command"][captured["command"].index("--sandbox") + 1], "read-only")
        self.assertNotEqual(captured["cwd"], self.root)
        self.assertNotIn(str(self.root), captured["prompt"])
        self.assertNotIn("Private voice transcript", captured["prompt"])

    def test_resolved_queue_cleanup_preserves_note_and_pending_suggestions(self):
        context, _ = self.project.codex_context("opening-hook", "Consider a cleaner phrase.")
        proposal = {"segment_id": "opening-hook", "proposed_text": "A cleaner phrase.", "rationale": "Shorter."}
        self.project.store_suggestion("opening-hook", "Consider a cleaner phrase.", proposal, context["text"])
        self.project.dismiss_suggestion("opening-hook", self.project.read_state()["segments"]["opening-hook"]["suggestions"][0]["id"])
        self.project.save_note("next-beat", "Keep this pending note.")
        self.assertEqual(self.project.clear_resolved(), 1)
        state = self.project.read_state()
        self.assertEqual(state["segments"]["opening-hook"]["note"], "Consider a cleaner phrase.")
        self.assertEqual(state["segments"]["opening-hook"]["suggestions"], [])
        self.assertEqual(state["segments"]["next-beat"]["note"], "Keep this pending note.")

    def test_audio_route_resolution_rejects_paths_outside_selected_audio_folder(self):
        self.data["selected_takes"]["opening-hook"] = "../../outside.wav"
        self.write_manifest()
        with self.assertRaises(workbench.WorkbenchError):
            self.project._selected_audio("opening-hook")
        payload = self.project.state_payload()
        self.assertEqual(payload["segments"][0]["generation_state"], "take-needed")

    def test_assembly_status_checks_recorded_selected_takes_and_review_wav(self):
        assembled = self.audio / "assembled"
        performance = self.audio / "performance"
        assembled.mkdir()
        performance.mkdir()
        master = assembled / "test_mono.wav"
        review = assembled / "test_stereo-review.wav"
        master.write_bytes(b"mono")
        review.write_bytes(b"review")
        self.manifest.write_text(json.dumps(self.data, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        current = narration.segments_array_sha256(self.data)
        self.data["segments_sha256"] = current
        self.write_manifest()
        (performance / "run_20261122-120000-000001.json").write_text(json.dumps({
            "status": "complete",
            "segments_sha256": current,
            "assembly": {
                "master_mono": "assembled/test_mono.wav",
                "review_stereo": "assembled/test_stereo-review.wav",
                "selected_takes": {},
            },
        }), encoding="utf-8")
        payload = self.project.state_payload()
        self.assertEqual(payload["assembled_audio_name"], review.name)
        self.assertTrue(payload["assembly_current"])

        self.data["selected_takes"]["opening-hook"] = "segments/opening-hook/take-001.wav"
        self.write_manifest()
        self.assertFalse(self.project.state_payload()["assembly_current"])


class HttpTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        root = Path(self.temp.name)
        audio = root / "audio"
        audio.mkdir()
        self.manifest = audio / "narration_manifest.json"
        self.manifest.write_text(json.dumps({
            "project": "http-test", "voice": {"reference_audio": "ref.wav", "reference_text": "ref words"},
            "settings": {}, "selected_takes": {},
            "segments": [{"id": "beat-one", "text": "First words.", "status": "active"}],
        }), encoding="utf-8")
        self.project = workbench.Project(self.manifest)
        self.server = workbench.ThreadingHTTPServer(("127.0.0.1", 0), workbench.create_handler(self.project, None, "python"))
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        self.addCleanup(self.stop_server)
        self.base = f"http://127.0.0.1:{self.server.server_port}"

    def stop_server(self):
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=2)

    def test_api_returns_project_content_without_voice_reference_fields(self):
        with urlopen(self.base + "/api/state") as response:
            payload = json.loads(response.read())
        self.assertEqual(payload["project"], "http-test")
        encoded = json.dumps(payload)
        self.assertNotIn("ref.wav", encoded)
        self.assertNotIn("ref words", encoded)

    def test_reorder_route_updates_manifest_array(self):
        data = json.loads(self.manifest.read_text(encoding="utf-8"))
        data["segments"].append({"id": "beat-two", "text": "Second words.", "status": "inactive"})
        self.manifest.write_text(json.dumps(data), encoding="utf-8")
        digest = self.project.state_payload()["manifest_hash"]
        body = json.dumps({"segment_id": "beat-two", "target_id": "beat-one", "placement": "before", "manifest_hash": digest}).encode("utf-8")
        request = Request(self.base + "/api/segments/reorder", data=body,
                          headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request) as response:
            payload = json.loads(response.read())
        self.assertEqual([item["id"] for item in payload["state"]["segments"]], ["beat-two", "beat-one"])
        self.assertEqual([item["id"] for item in json.loads(self.manifest.read_text(encoding="utf-8"))["segments"]], ["beat-two", "beat-one"])

    def test_assembled_wav_supports_browser_byte_ranges(self):
        assembled = self.manifest.parent / "assembled"
        assembled.mkdir()
        path = assembled / "review.wav"
        with wave.open(str(path), "wb") as audio:
            audio.setnchannels(1)
            audio.setsampwidth(2)
            audio.setframerate(8_000)
            audio.writeframes(b"\0\0" * 800)
        with urlopen(Request(self.base + "/api/audio/assembly", headers={"Range": "bytes=0-63"})) as response:
            self.assertEqual(response.status, 206)
            self.assertEqual(response.headers["Content-Type"], "audio/wav")
            self.assertEqual(response.headers["Content-Range"], f"bytes 0-63/{path.stat().st_size}")
            self.assertTrue(response.read().startswith(b"RIFF"))

    def test_host_header_rejects_non_local_origin(self):
        request = Request(self.base + "/api/state", headers={"Host": "example.org"})
        with self.assertRaises(HTTPError) as context:
            urlopen(request)
        self.assertEqual(context.exception.code, 403)

    def test_codex_unavailable_preserves_note_and_manifest(self):
        before = self.manifest.read_bytes()
        note = json.dumps({"segment_id": "beat-one", "note": "Make the line easier to say aloud."}).encode("utf-8")
        request = Request(self.base + "/api/note", data=note, headers={"Content-Type": "application/json"}, method="POST")
        with urlopen(request) as response:
            self.assertEqual(response.status, 200)
        ask = json.dumps({"segment_id": "beat-one", "note": "Make the line easier to say aloud."}).encode("utf-8")
        request = Request(self.base + "/api/codex/suggest", data=ask, headers={"Content-Type": "application/json"}, method="POST")
        with self.assertRaises(HTTPError) as context:
            urlopen(request)
        self.assertEqual(context.exception.code, 503)
        project_state = json.loads((self.manifest.parent / ".workbench" / "workbench_state.json").read_text(encoding="utf-8"))
        self.assertEqual(project_state["segments"]["beat-one"]["note"], "Make the line easier to say aloud.")
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_generation_blocks_concurrent_manifest_edits(self):
        started = threading.Event()
        release = threading.Event()
        generated = []

        def fake_run(command, timeout, input_text=None):
            generated.append(command)
            started.set()
            if not release.wait(3):
                raise RuntimeError("The test generation was not released.")
            return {"ok": True, "returncode": 0, "output": "done", "error": ""}

        def generate():
            request = Request(
                self.base + "/api/generate", data=b"{}",
                headers={"Content-Type": "application/json"}, method="POST",
            )
            with urlopen(request) as response:
                self.assertEqual(response.status, 200)

        with mock.patch.object(workbench, "run_tool", side_effect=fake_run):
            thread = threading.Thread(target=generate)
            thread.start()
            try:
                self.assertTrue(started.wait(2))
                digest = self.project.state_payload()["manifest_hash"]
                body = json.dumps({
                    "segment_id": "beat-one", "manifest_hash": digest,
                    "updates": {"text": "Do not overwrite during generation."},
                }).encode("utf-8")
                request = Request(
                    self.base + "/api/segment/save", data=body,
                    headers={"Content-Type": "application/json"}, method="POST",
                )
                with self.assertRaises(HTTPError) as context:
                    urlopen(request)
                self.assertEqual(context.exception.code, 409)
            finally:
                release.set()
                thread.join(timeout=3)
        self.assertEqual(generated[0][-1], "--generate-only")
        self.assertEqual(json.loads(self.manifest.read_text(encoding="utf-8"))["segments"][0]["text"], "First words.")


if __name__ == "__main__":
    unittest.main()

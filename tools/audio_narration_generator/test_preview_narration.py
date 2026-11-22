"""Unit tests for transient narration preview input and platform handling."""

import io
import json
import tempfile
from types import SimpleNamespace
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest import mock

import preview_narration as preview


class ManifestLookupTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.manifest = Path(self.temp.name) / "narration_manifest.json"
        self.data = {
            "segments": [
                {"id": "active", "text": "Active line."},
                {"id": "inactive", "status": "inactive", "text": "Inactive line."},
                {"id": "deleted", "status": "deleted", "text": "Deleted line."},
            ]
        }
        self.write_manifest()

    def write_manifest(self):
        self.manifest.write_text(json.dumps(self.data), encoding="utf-8")

    def test_reads_active_and_inactive_without_mutating_manifest(self):
        before = self.manifest.read_bytes()
        self.assertEqual(preview.manifest_segment_text(self.manifest, "active"), "Active line.")
        self.assertEqual(preview.manifest_segment_text(self.manifest, "inactive"), "Inactive line.")
        self.assertEqual(self.manifest.read_bytes(), before)

    def test_missing_and_deleted_segments_are_rejected(self):
        with self.assertRaisesRegex(preview.PreviewError, "Segment ID not found"):
            preview.manifest_segment_text(self.manifest, "missing")
        with self.assertRaisesRegex(preview.PreviewError, "marked deleted"):
            preview.manifest_segment_text(self.manifest, "deleted")

    def test_duplicate_segment_id_is_rejected(self):
        self.data["segments"].append({"id": "active", "text": "Ambiguous."})
        self.write_manifest()
        with self.assertRaisesRegex(preview.PreviewError, "ambiguous"):
            preview.manifest_segment_text(self.manifest, "active")

    def test_invalid_manifest_and_empty_text_are_rejected(self):
        self.manifest.write_text("{", encoding="utf-8")
        with self.assertRaisesRegex(preview.PreviewError, "Invalid JSON"):
            preview.manifest_segment_text(self.manifest, "active")
        self.data["segments"][0]["text"] = "  "
        self.write_manifest()
        with self.assertRaisesRegex(preview.PreviewError, "does not contain narration text"):
            preview.manifest_segment_text(self.manifest, "active")

    def test_malformed_status_type_is_rejected_cleanly(self):
        self.data["segments"][0]["status"] = ["active"]
        self.write_manifest()
        with self.assertRaisesRegex(preview.PreviewError, "unsupported status"):
            preview.manifest_segment_text(self.manifest, "active")


class PreviewCommandTest(unittest.TestCase):
    def test_non_windows_fails_without_fallback(self):
        with mock.patch.object(preview.platform, "system", return_value="Linux"), mock.patch.object(
            preview, "run_powershell"
        ) as run_ps:
            with redirect_stderr(io.StringIO()):
                result = preview.main(["--text", "Draft line."])
        self.assertEqual(result, 2)
        run_ps.assert_not_called()

    def test_windows_inline_text_is_passed_to_powershell_without_file_output(self):
        args = preview.parse_args(["--text", "Draft line.", "--rate", "2"])
        with mock.patch.object(preview.platform, "system", return_value="Windows"), mock.patch.object(
            preview, "run_powershell", return_value=0
        ) as run_ps:
            self.assertEqual(preview.main(["--text", "Draft line.", "--rate", "2"]), 0)
        run_ps.assert_called_once_with(args, "Draft line.")

    def test_stdin_text_is_forwarded(self):
        with mock.patch.object(preview.platform, "system", return_value="Windows"), mock.patch.object(
            preview.sys, "stdin"
        ) as stdin, mock.patch.object(preview, "run_powershell", return_value=0) as run_ps:
            stdin.buffer.read.return_value = b"Piped draft."
            self.assertEqual(preview.main(["--text", "-"]), 0)
        run_ps.assert_called_once()
        self.assertEqual(run_ps.call_args.args[1], "Piped draft.")

    def test_piped_stdin_requires_valid_utf8(self):
        with mock.patch.object(preview.sys, "stdin", SimpleNamespace(buffer=io.BytesIO(b"\xff"))):
            with self.assertRaisesRegex(preview.PreviewError, "valid UTF-8"):
                preview.read_utf8_stdin()

    def test_voice_listing_uses_supported_backend(self):
        with mock.patch.object(preview.platform, "system", return_value="Windows"), mock.patch.object(
            preview, "run_powershell", return_value=0
        ) as run_ps:
            self.assertEqual(preview.main(["--list-voices"]), 0)
        self.assertTrue(run_ps.call_args.args[0].list_voices)

    def test_missing_windows_powershell_fails_without_fallback(self):
        with mock.patch.object(preview.platform, "system", return_value="Windows"), mock.patch.object(
            preview, "powershell_executable", side_effect=preview.PreviewError("Windows PowerShell was not found.")
        ), redirect_stderr(io.StringIO()):
            self.assertEqual(preview.main(["--text", "Draft line."]), 2)

    def test_keyboard_interrupt_returns_interrupted_status(self):
        with mock.patch.object(preview.platform, "system", return_value="Windows"), mock.patch.object(
            preview, "run_powershell", side_effect=KeyboardInterrupt
        ), redirect_stderr(io.StringIO()):
            self.assertEqual(preview.main(["--text", "Draft line."]), 130)

    def test_cli_rejects_invalid_combinations_and_rates(self):
        invalid_commands = [
            ["--manifest", "narration_manifest.json"],
            ["--segment-id", "opening-hook", "--text", "Line."],
            ["--text", "Line.", "--rate", "11"],
            ["--list-voices", "--text", "Line."],
        ]
        for command in invalid_commands:
            with self.subTest(command=command), self.assertRaises(SystemExit):
                preview.parse_args(command)


if __name__ == "__main__":
    unittest.main()

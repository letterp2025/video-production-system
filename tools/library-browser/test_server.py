import tempfile
import unittest
import json
from pathlib import Path

from server import Catalog, private_root_from_config, safe_child


class CatalogTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.base = Path(self.temp.name)
        self.public = self.base / "public"
        self.private = self.base / "private"
        self.public.mkdir()
        self.private.mkdir()
        self._entry(self.public, "visual_elements_library", "ELM-demo-element", "Demo element", "Public example.")
        self._entry(self.private, "visual_reference_library", "REF-private-study", "Private study", "Local source notes.")
        preview = self.private / "visual_reference_library" / "REF-private-study" / "reference" / "element-sheets" / "board.png"
        preview.parent.mkdir(parents=True)
        preview.write_bytes(b"png")
        self.catalog = Catalog(self.public, self.private)

    def tearDown(self):
        self.temp.cleanup()

    @staticmethod
    def _entry(root, library, folder, title, summary):
        notes = root / library / folder / "NOTES.md"
        notes.parent.mkdir(parents=True)
        notes.write_text(f"# {folder} - {title}\n\n- **Status:** Draft\n\n{summary}\n", encoding="utf-8")

    def test_scans_public_and_private_entries_with_scope(self):
        entries = self.catalog.entries()
        self.assertEqual({item["visibility"] for item in entries}, {"public", "private"})
        self.assertEqual({item["id"] for item in entries}, {"ELM-demo-element", "REF-private-study"})

    def test_entry_details_return_notes_without_absolute_paths(self):
        record = self.catalog.entry("private", "visual_reference_library", "REF-private-study")
        self.assertIn("Local source notes", record["notes"])
        self.assertEqual(record["id"], "REF-private-study")
        self.assertNotIn(str(self.base), str(record))

    def test_private_preview_is_found_under_ignored_media_folder(self):
        record = self.catalog.entry("private", "visual_reference_library", "REF-private-study")
        self.assertEqual(record["preview_type"], "png")
        self.assertIn("/media/private/", record["preview"])

    def test_entry_lookup_requires_full_id_and_matching_library_type(self):
        self.assertIsNone(self.catalog.entry("private", "visual_reference_library", "REF-private"))
        self.assertIsNone(self.catalog.entry("private", "visual_elements_library", "REF-private-study"))
        self.assertIsNone(self.catalog.entry("private", "visual_reference_library", "REF-0001"))

    def test_safe_child_rejects_path_traversal(self):
        outside = self.base / "outside.txt"
        outside.write_text("private", encoding="utf-8")
        with self.assertRaises(ValueError):
            safe_child(self.public, "../outside.txt")

    def test_config_reads_only_an_absolute_private_root(self):
        config_path = self.base / "library-browser.json"
        config_path.write_text(json.dumps({"private_root": str(self.private)}), encoding="utf-8")
        self.assertEqual(private_root_from_config(config_path), self.private)

    def test_config_rejects_relative_paths_and_unrelated_properties(self):
        config_path = self.base / "library-browser.json"
        config_path.write_text(json.dumps({"private_root": "private"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "absolute path"):
            private_root_from_config(config_path)
        config_path.write_text(json.dumps({"private_root": str(self.private), "theme": "red"}), encoding="utf-8")
        with self.assertRaisesRegex(ValueError, "only the private_root"):
            private_root_from_config(config_path)


if __name__ == "__main__":
    unittest.main()
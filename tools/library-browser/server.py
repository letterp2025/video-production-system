#!/usr/bin/env python3
"""Read-only localhost browser for public and explicitly configured private libraries."""

from __future__ import annotations

import argparse
import json
import mimetypes
import re
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import parse_qs, quote, unquote, urlparse


LIBRARY_LABELS = {
    "visual_reference_library": "References",
    "visual_elements_library": "Elements",
    "visual_animations_library": "Animations",
}
LIBRARY_PREFIXES = {
    "visual_reference_library": "REF",
    "visual_elements_library": "ELM",
    "visual_animations_library": "ANM",
}
ENTRY_ID = re.compile(r"^(?:REF|ELM|ANM)-[a-z0-9]+(?:-[a-z0-9]+)*$")
MEDIA_SUFFIXES = {".avif", ".gif", ".jpeg", ".jpg", ".png", ".webp", ".mp4", ".webm"}
STATIC_FILES = {"/": ("index.html", "text/html; charset=utf-8"),
                "/app.js": ("app.js", "text/javascript; charset=utf-8"),
                "/styles.css": ("styles.css", "text/css; charset=utf-8")}
STATIC_ROOT = Path(__file__).resolve().parent / "static"


def is_entry_id(library_name: str, identifier: str) -> bool:
    """Validate a descriptive folder ID and its library-type prefix."""
    prefix = LIBRARY_PREFIXES.get(library_name)
    return bool(prefix and ENTRY_ID.fullmatch(identifier) and identifier.startswith(prefix + "-"))


def safe_child(root: Path, relative: str) -> Path:
    """Resolve a relative path and reject traversal or symlink escapes."""
    resolved_root = root.resolve(strict=True)
    candidate = (resolved_root / relative).resolve(strict=True)
    try:
        candidate.relative_to(resolved_root)
    except ValueError as exc:
        raise ValueError("Path is outside the configured library root") from exc
    if not candidate.is_file():
        raise ValueError("Requested path is not a file")
    return candidate


def private_root_from_config(config_path: Path) -> Path:
    """Read the single private_root setting from a workspace-owned JSON file."""
    try:
        config = json.loads(config_path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError) as exc:
        raise ValueError(f"Could not read a valid JSON config: {exc}") from exc
    if not isinstance(config, dict) or set(config) != {"private_root"}:
        raise ValueError("Config must contain only the private_root property")
    value = config["private_root"]
    if not isinstance(value, str) or not value.strip():
        raise ValueError("Config private_root must be a non-empty absolute path")
    private_root = Path(value)
    if not private_root.is_absolute():
        raise ValueError("Config private_root must be an absolute path")
    return private_root


class Catalog:
    def __init__(self, public_root: Path, private_root: Path | None = None):
        self.roots = {"public": public_root.resolve()}
        if private_root is not None:
            self.roots["private"] = private_root.resolve()

    @staticmethod
    def _read_entry(notes_path: Path, root: Path, visibility: str,
                    library_name: str, entry_dir: Path) -> dict:
        notes = notes_path.read_text(encoding="utf-8-sig", errors="replace")
        first_heading = next((line.lstrip("# ").strip() for line in notes.splitlines()
                              if line.startswith("# ")), entry_dir.name)
        separator = "-" + chr(0x2013) + chr(0x2014)
        heading_pattern = r"^" + re.escape(entry_dir.name) + r"\s*[" + re.escape(separator) + r"]\s*"
        title = re.sub(heading_pattern, "", first_heading)
        status_match = re.search(r"^\s*-\s*\*\*Status:\*\*\s*(.+)$", notes, re.MULTILINE)
        status = status_match.group(1).strip() if status_match else "Status not recorded"

        summary_lines = []
        for line in notes.splitlines():
            stripped = line.strip()
            if not stripped or stripped.startswith(("#", "- **", "|", "```")):
                continue
            summary_lines.append(stripped)
            if len(" ".join(summary_lines)) >= 280:
                break
        summary = re.sub(r"[`*_]", "", " ".join(summary_lines))[:320]

        entry_root = entry_dir.resolve()
        preview = Catalog._find_preview(entry_root)
        relative_entry = entry_dir.relative_to(root).as_posix()
        return {
            "visibility": visibility,
            "id": entry_dir.name,
            "title": title,
            "library": library_name,
            "library_label": LIBRARY_LABELS[library_name],
            "status": status,
            "summary": summary,
            "entry_path": relative_entry,
            "preview": ("/media/" + visibility + "/" + quote(preview.relative_to(root).as_posix(), safe="/")) if preview else None,
            "preview_type": preview.suffix.lower().lstrip(".") if preview else None,
        }

    @staticmethod
    def _find_preview(entry_root: Path) -> Path | None:
        priorities = (
            "preview", "render/LOW", "styles", "reference/element-sheets",
            "reference/frames", "reference/captures", "reference/contact_sheets", "assets",
        )
        for relative_dir in priorities:
            folder = entry_root / relative_dir
            if not folder.is_dir():
                continue
            candidates = sorted((p for p in folder.rglob("*")
                                 if p.is_file() and p.suffix.lower() in MEDIA_SUFFIXES),
                                key=lambda p: (p.suffix.lower() == ".mp4", p.name.casefold()))
            if candidates:
                return candidates[0]
        return None

    def entries(self) -> list[dict]:
        results = []
        for visibility, root in self.roots.items():
            if not root.is_dir():
                continue
            for library_name, library_label in LIBRARY_LABELS.items():
                library_root = root / library_name
                if not library_root.is_dir():
                    continue
                for entry_dir in sorted(library_root.iterdir(), key=lambda p: p.name.casefold()):
                    if not entry_dir.is_dir():
                        continue
                    if not is_entry_id(library_name, entry_dir.name):
                        continue
                    notes_path = entry_dir / "NOTES.md"
                    if notes_path.is_file():
                        results.append(self._read_entry(notes_path, root, visibility,
                                                         library_name, entry_dir))
        return sorted(results, key=lambda item: (item["visibility"], item["library_label"], item["id"]))

    def entry(self, visibility: str, library_name: str, identifier: str) -> dict | None:
        if visibility not in self.roots or not is_entry_id(library_name, identifier):
            return None
        root = self.roots[visibility]
        library_root = root / library_name
        if not library_root.is_dir():
            return None
        entry_dir = library_root / identifier
        notes_path = entry_dir / "NOTES.md"
        if not entry_dir.is_dir() or not notes_path.is_file():
            return None
        record = self._read_entry(notes_path, root, visibility, library_name, entry_dir)
        record["notes"] = notes_path.read_text(encoding="utf-8-sig", errors="replace")
        return record

    def media(self, visibility: str, relative_path: str) -> Path:
        if visibility not in self.roots:
            raise ValueError("Unknown visibility scope")
        path = safe_child(self.roots[visibility], relative_path)
        if path.suffix.lower() not in MEDIA_SUFFIXES:
            raise ValueError("File type is not available in the preview viewer")
        return path


def make_handler(catalog: Catalog):
    class Handler(BaseHTTPRequestHandler):
        server_version = "VisualLibraryBrowser/1.0"

        def _headers(self, content_type: str, length: int):
            self.send_response(200)
            self.send_header("Content-Type", content_type)
            self.send_header("Content-Length", str(length))
            self.send_header("Cache-Control", "no-store")
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Content-Security-Policy", "default-src 'self'; img-src 'self' data:; media-src 'self'; style-src 'self'; script-src 'self'; connect-src 'self'; frame-ancestors 'none'")
            self.end_headers()

        def _bytes(self, body: bytes, content_type: str):
            self._headers(content_type, len(body))
            self.wfile.write(body)

        def _json(self, data, status=200):
            body = json.dumps(data, ensure_ascii=False).encode("utf-8")
            if status != 200:
                self.send_response(status)
                self.send_header("Content-Type", "application/json; charset=utf-8")
                self.send_header("Content-Length", str(len(body)))
                self.send_header("Cache-Control", "no-store")
                self.send_header("X-Content-Type-Options", "nosniff")
                self.end_headers()
                self.wfile.write(body)
                return
            self._bytes(body, "application/json; charset=utf-8")

        def do_GET(self):
            parsed = urlparse(self.path)
            if parsed.path in STATIC_FILES:
                filename, content_type = STATIC_FILES[parsed.path]
                body = (STATIC_ROOT / filename).read_bytes()
                self._bytes(body, content_type)
                return
            query = parse_qs(parsed.query)
            if parsed.path == "/api/entries":
                self._json({"entries": catalog.entries(), "private_available": "private" in catalog.roots})
                return
            if parsed.path == "/api/entry":
                visibility = query.get("visibility", [""])[0]
                library = query.get("library", [""])[0]
                identifier = query.get("id", [""])[0]
                result = catalog.entry(visibility, library, identifier)
                self._json(result or {"error": "Entry not found"}, 200 if result else 404)
                return
            if parsed.path.startswith("/media/"):
                parts = parsed.path.removeprefix("/media/").split("/", 1)
                if len(parts) != 2:
                    self._json({"error": "Invalid media path"}, 400)
                    return
                try:
                    path = catalog.media(parts[0], unquote(parts[1]))
                    self._bytes(path.read_bytes(), mimetypes.guess_type(path.name)[0] or "application/octet-stream")
                except (ValueError, OSError):
                    self._json({"error": "Preview not found"}, 404)
                return
            self._json({"error": "Not found"}, 404)

        def do_POST(self):
            self._json({"error": "Read-only catalog"}, 405)

        do_PUT = do_POST
        do_PATCH = do_POST
        do_DELETE = do_POST

        def log_message(self, fmt, *args):
            print("%s - %s" % (self.address_string(), fmt % args))

    return Handler


def main() -> None:
    parser = argparse.ArgumentParser(description="Browse public and private visual libraries on this computer.")
    parser.add_argument("--public-root", type=Path,
                        help="folder containing public visual_*_library directories")
    parser.add_argument("--config", type=Path,
                        help="JSON file containing only the private_root absolute path")
    parser.add_argument("--private-root", type=Path,
                        help="optional private folder containing visual_*_library directories; overrides --config")
    parser.add_argument("--port", type=int, help="local server port (default: 8765)")
    args = parser.parse_args()
    public_root = (args.public_root or Path(__file__).resolve().parents[2] / "libraries").resolve()
    configured_private_root = None
    if args.config:
        try:
            configured_private_root = private_root_from_config(args.config)
        except ValueError as exc:
            parser.error(str(exc))
    private_root = args.private_root or configured_private_root
    port = args.port if args.port is not None else 8765
    if not 1 <= port <= 65535:
        parser.error("Port must be between 1 and 65535")
    if not public_root.is_dir():
        parser.error(f"Public library root does not exist: {public_root}")
    if private_root and not private_root.is_dir():
        parser.error("Private library root does not exist")
    catalog = Catalog(public_root, private_root)
    server = ThreadingHTTPServer(("127.0.0.1", port), make_handler(catalog))
    print(f"Visual Library Browser listening at http://127.0.0.1:{port}")
    print(f"Loaded {len(catalog.entries())} entries. Press Ctrl+C to stop.")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\nStopping local browser.")
    finally:
        server.server_close()


if __name__ == "__main__":
    main()

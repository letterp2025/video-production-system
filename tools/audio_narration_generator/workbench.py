#!/usr/bin/env python3
"""Loopback-only script and narration workbench for one selected project."""

from __future__ import annotations

import argparse
import importlib.util
import ipaddress
import json
import mimetypes
import os
import platform
import shutil
import subprocess
import sys
import tempfile
import threading
import wave
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import parse_qs, unquote, urlparse

import generate_narration as narration

from workbench_common import (
    AI_SCHEMA_PATH, MAX_REQUEST_BYTES, MAX_RESPONSE_CHARS, MAX_TEXT_CHARS,
    STATIC_DIR, TOOL_DIR, WorkbenchError, now_iso, sha256_bytes, text_hash,
    visual_animation_recipes,
)
from workbench_project import Project


def library_catalog(config_path: Path | None = None):
    """Reuse the browser's read-only catalog without starting its server."""
    path = TOOL_DIR.parent / "library-browser" / "server.py"
    spec = importlib.util.spec_from_file_location("vps_visual_library", path)
    if spec is None or spec.loader is None:
        raise WorkbenchError("Visual Library Browser code is unavailable.")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    try:
        private_root = module.private_root_from_config(config_path) if config_path else None
    except ValueError as exc:
        raise WorkbenchError(str(exc)) from exc
    if private_root and not private_root.is_dir():
        raise WorkbenchError("Configured private library folder is unavailable.")
    return module.Catalog(TOOL_DIR.parents[1] / "libraries", private_root)


def build_codex_prompt(guide_json: str, context: dict[str, Any]) -> str:
    return (
        "Revise one narration segment using the guide and context below. The creator explicitly requested "
        "a suggestion. Return a complete replacement for the selected segment only. Keep facts and meaning "
        "grounded in the supplied words. Do not make changes to files or use tools.\n\n"
        "AI GUIDE (tracked public tool file):\n"
        f"{guide_json}\n\n"
        "REQUEST CONTEXT (only this segment, its note, and immediate neighbors):\n"
        f"{json.dumps(context, ensure_ascii=False, indent=2)}\n"
    )


def run_codex_suggestion(codex_path: str, project: Project, segment_id: str, note: str) -> dict[str, str]:
    if not note.strip():
        raise WorkbenchError("Add a wording note before asking Codex.")
    context, guide = project.codex_context(segment_id, note)
    prompt = build_codex_prompt(guide, context)
    with tempfile.TemporaryDirectory(prefix="narration-workbench-codex-") as temp_dir:
        response_path = Path(temp_dir) / "suggestion.json"
        command = [
            codex_path, "exec", "--ephemeral", "--sandbox", "read-only",
            "--ignore-user-config", "--skip-git-repo-check", "--output-schema", str(AI_SCHEMA_PATH),
            "--output-last-message", str(response_path), "--color", "never", "-",
        ]
        try:
            completed = subprocess.run(
                command, input=prompt, text=True, encoding="utf-8", errors="replace",
                capture_output=True, cwd=temp_dir, timeout=240, check=False,
            )
        except subprocess.TimeoutExpired as exc:
            raise WorkbenchError("Codex took more than four minutes. The note is still saved for another try.", 504) from exc
        except OSError as exc:
            raise WorkbenchError(f"Could not start Codex: {exc}. The note is still saved.", 503) from exc
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout).strip()[-1600:]
            raise WorkbenchError(f"Codex could not return a suggestion. {detail or 'Check Codex sign-in and CLI setup.'}", 502)
        try:
            result = json.loads(response_path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            raise WorkbenchError("Codex returned a response that could not be read as structured JSON.", 502) from exc
    if not isinstance(result, dict) or set(result) != {"segment_id", "proposed_text", "rationale"}:
        raise WorkbenchError("Codex response did not match the suggestion format.", 502)
    if result["segment_id"] != segment_id:
        raise WorkbenchError("Codex response targeted a different segment. No suggestion was saved.", 502)
    if not isinstance(result["proposed_text"], str) or not result["proposed_text"].strip() or len(result["proposed_text"]) > MAX_TEXT_CHARS:
        raise WorkbenchError("Codex returned empty or oversized narration text.", 502)
    if not isinstance(result["rationale"], str):
        raise WorkbenchError("Codex returned an invalid explanation.", 502)
    return result


def resolve_codex(requested: str | None) -> str | None:
    if requested:
        candidate = Path(requested).expanduser()
        if candidate.is_file():
            return str(candidate.resolve())
        return shutil.which(requested)
    return shutil.which("codex")


def run_tool(command: list[str], timeout: int, input_text: str | None = None) -> dict[str, Any]:
    try:
        result = subprocess.run(
            command, input=input_text, text=True, encoding="utf-8", errors="replace",
            capture_output=True, cwd=TOOL_DIR, timeout=timeout, check=False,
        )
    except subprocess.TimeoutExpired as exc:
        raise WorkbenchError(f"The command exceeded its {timeout}-second limit.", 504) from exc
    except OSError as exc:
        raise WorkbenchError(f"Could not start the narration tool: {exc}", 503) from exc
    output = (result.stdout or "").strip()
    errors = (result.stderr or "").strip()
    return {
        "ok": result.returncode == 0,
        "returncode": result.returncode,
        "output": output[-MAX_RESPONSE_CHARS:],
        "error": errors[-MAX_RESPONSE_CHARS:],
    }


def create_handler(project: Project, codex_path: str | None, python_path: str) -> type[BaseHTTPRequestHandler]:
    if not hasattr(project, "catalog"):
        project.catalog = library_catalog()
    sequence_run_lock = threading.Lock()
    sequence_state_lock = threading.Lock()
    sequence_process: subprocess.Popen[str] | None = None
    sapi_render_lock = threading.Lock()
    sapi_temp: tempfile.TemporaryDirectory[str] | None = None
    sapi_cache: dict[str, Any] = {}

    class Handler(BaseHTTPRequestHandler):
        server_version = "NarrationWorkbench/1.0"
        sys_version = ""

        def log_message(self, fmt: str, *args: Any) -> None:
            # Avoid putting script text or user notes in the terminal log.
            print(f"{self.address_string()} - {fmt % args}")

        def _local_request(self) -> bool:
            try:
                if not ipaddress.ip_address(self.client_address[0]).is_loopback:
                    return False
            except ValueError:
                return False
            host_header = urlparse("//" + self.headers.get("Host", "")).hostname
            try:
                host_port = urlparse("//" + self.headers.get("Host", "")).port
            except ValueError:
                return False
            if (host_header or "").lower() not in {"127.0.0.1", "localhost"} or host_port != self.server.server_port:
                return False
            origin = self.headers.get("Origin")
            if origin:
                parsed = urlparse(origin)
                try:
                    origin_port = parsed.port
                except ValueError:
                    return False
                if (parsed.scheme not in {"http", "https"}
                    or (parsed.hostname or "").lower() not in {"127.0.0.1", "localhost"}
                    or origin_port != self.server.server_port):
                    return False
            return True

        def _headers(self, content_type: str) -> None:
            self.send_header("Content-Type", content_type)
            self.send_header("X-Content-Type-Options", "nosniff")
            self.send_header("Referrer-Policy", "no-referrer")
            self.send_header("Cache-Control", "no-store")
            self.send_header("Content-Security-Policy", "default-src 'self'; media-src 'self'; style-src 'self'; script-src 'self'; img-src 'self' data:; connect-src 'self'; frame-ancestors 'none'; base-uri 'none'")

        def _json(self, status: int, value: dict[str, Any]) -> None:
            payload = json.dumps(value, ensure_ascii=False).encode("utf-8")
            self.send_response(status)
            self._headers("application/json; charset=utf-8")
            self.send_header("Content-Length", str(len(payload)))
            self.end_headers()
            self.wfile.write(payload)

        def _read_json(self) -> dict[str, Any]:
            if self.headers.get_content_type() != "application/json":
                raise WorkbenchError("Send this request as application/json.", 415)
            try:
                length = int(self.headers.get("Content-Length", "0"))
            except ValueError as exc:
                raise WorkbenchError("Invalid request size.") from exc
            if length < 2 or length > MAX_REQUEST_BYTES:
                raise WorkbenchError(f"Request must be between 2 and {MAX_REQUEST_BYTES} bytes.", 413)
            try:
                value = json.loads(self.rfile.read(length).decode("utf-8"))
            except (UnicodeDecodeError, json.JSONDecodeError) as exc:
                raise WorkbenchError("Request body is not valid UTF-8 JSON.") from exc
            if not isinstance(value, dict):
                raise WorkbenchError("Request body must be a JSON object.")
            return value

        def do_GET(self) -> None:  # noqa: N802
            if not self._local_request():
                self._json(403, {"error": "This workbench accepts requests only from its local browser."})
                return
            try:
                if self.path in {"/", "/index.html", "/app.js", "/styles.css"}:
                    filename = {"/": "index.html", "/index.html": "index.html", "/app.js": "app.js", "/styles.css": "styles.css"}[self.path]
                    path = STATIC_DIR / filename
                    content_type = mimetypes.guess_type(filename)[0] or "application/octet-stream"
                    if filename.endswith(".js"):
                        content_type += "; charset=utf-8"
                    elif filename.endswith(".html") or filename.endswith(".css"):
                        content_type += "; charset=utf-8"
                    self._send_file(path, content_type)
                elif self.path == "/api/state":
                    self._json(200, project.state_payload())
                elif self.path == "/api/library/entries":
                    self._json(200, {"entries": project.catalog.entries(), "private_available": "private" in project.catalog.roots})
                elif self.path.startswith("/api/library/entry?"):
                    query = parse_qs(urlparse(self.path).query)
                    entry = project.catalog.entry(query.get("visibility", [""])[0], query.get("library", [""])[0], query.get("id", [""])[0])
                    self._json(200, entry) if entry else self._json(404, {"error": "Library entry unavailable."})
                elif self.path.startswith("/api/library/media/"):
                    parts = self.path.removeprefix("/api/library/media/").split("/", 1)
                    if len(parts) != 2:
                        raise WorkbenchError("Invalid library preview.", 404)
                    try:
                        media_path = project.catalog.media(parts[0], unquote(parts[1]))
                    except (ValueError, OSError) as exc:
                        raise WorkbenchError("Library preview unavailable.", 404) from exc
                    self._send_file(media_path, mimetypes.guess_type(media_path.name)[0] or "application/octet-stream", allow_range=True)
                elif self.path == "/api/provider":
                    self._json(200, {
                        "preview": {"available": platform.system() == "Windows", "backend": "Windows SAPI" if platform.system() == "Windows" else "unsupported on this system"},
                    })
                elif self.path.startswith("/api/audio/segment/"):
                    segment_id = self.path.removeprefix("/api/audio/segment/")
                    self._send_file(project._selected_audio(segment_id), "audio/wav", allow_range=True)
                elif self.path.startswith("/api/audio/take/"):
                    parts = self.path.removeprefix("/api/audio/take/").split("/")
                    if len(parts) != 2:
                        raise WorkbenchError("Invalid take audio request.", 404)
                    self._send_file(project.take_audio_path(parts[0], parts[1]), "audio/wav", allow_range=True)
                elif self.path == "/api/audio/assembly":
                    self._send_file(project.assembly_audio_path(), "audio/wav", allow_range=True)
                elif self.path.split("?", 1)[0] == "/api/audio/sapi-preview":
                    if not sapi_cache.get("path"):
                        raise WorkbenchError("Build the SAPI preview first.", 404)
                    self._send_file(sapi_cache["path"], "audio/wav", allow_range=True)
                else:
                    self._json(404, {"error": "Not found."})
            except WorkbenchError as exc:
                self._json(exc.status, {"error": str(exc)})

        def _send_file(self, path: Path, content_type: str, allow_range: bool = False) -> None:
            if not path.is_file() or path.is_symlink():
                raise WorkbenchError("Requested file is unavailable.", 404)
            size = path.stat().st_size
            start, end, status = 0, size - 1, 200
            range_header = self.headers.get("Range") if allow_range else None
            if range_header:
                try:
                    unit, spec = range_header.split("=", 1)
                    if unit != "bytes" or "," in spec:
                        raise ValueError
                    left, right = spec.split("-", 1)
                    if left:
                        start = int(left)
                        end = int(right) if right else size - 1
                    else:
                        length = int(right)
                        start = max(0, size - length)
                        end = size - 1
                    if start < 0 or end < start or start >= size:
                        raise ValueError
                    end = min(end, size - 1)
                    status = 206
                except (ValueError, IndexError):
                    self.send_response(416)
                    self._headers("text/plain; charset=utf-8")
                    self.send_header("Content-Range", f"bytes */{size}")
                    self.send_header("Content-Length", "0")
                    self.end_headers()
                    return
            length = max(0, end - start + 1)
            self.send_response(status)
            self._headers(content_type)
            self.send_header("Accept-Ranges", "bytes" if allow_range else "none")
            self.send_header("Content-Length", str(length))
            if status == 206:
                self.send_header("Content-Range", f"bytes {start}-{end}/{size}")
            self.end_headers()
            with path.open("rb") as stream:
                stream.seek(start)
                remaining = length
                while remaining:
                    chunk = stream.read(min(64 * 1024, remaining))
                    if not chunk:
                        break
                    self.wfile.write(chunk)
                    remaining -= len(chunk)

        def do_POST(self) -> None:  # noqa: N802
            if not self._local_request():
                self._json(403, {"error": "This workbench accepts requests only from its local browser."})
                return
            try:
                body = self._read_json()
                if self.path == "/api/visual-takes/create":
                    result = project.create_visual_take(
                        self._required_string(body, "take_id"),
                        self._required_string(body, "title"),
                        self._string(body, "creative_direction"),
                        self._required_string(body, "manifest_hash"),
                    )
                    self._json(201, result)
                elif self.path == "/api/visual-takes/select":
                    self._json(200, {"state": project.select_visual_take(self._required_string(body, "take_id"))})
                elif self.path == "/api/visual-takes/open":
                    project.open_visual_take(self._required_string(body, "take_id"))
                    self._json(200, {"ok": True})
                elif self.path == "/api/visual-requests/create":
                    result = project.create_visual_request(self._required_string(body, "segment_id"), self._required_string(body, "brief"),
                        body.get("renderer"), body.get("references", []), self._required_string(body, "manifest_hash"))
                    self._json(201, result)
                elif self.path == "/api/visual-requests/select":
                    self._json(200, {"state": project.select_visual_request(self._required_string(body, "segment_id"), self._required_string(body, "request_id"))})
                elif self.path == "/api/visual-requests/sfx/create":
                    self._json(201, project.create_visual_sfx(self._required_string(body, "segment_id"), self._required_string(body, "request_id")))
                elif self.path == "/api/visual-requests/open":
                    project.open_visual_request_file(self._required_string(body, "segment_id"), self._required_string(body, "request_id"), self._required_string(body, "filename"))
                    self._json(200, {"ok": True})
                elif self.path in {"/api/layers/music/create", "/api/layers/sfx/create"}:
                    layer = self.path.split("/")[-2]
                    result = project.create_audio_mapping(
                        layer,
                        self._required_string(body, "segment_id"),
                        self._required_string(body, "manifest_hash"),
                    )
                    self._json(201, result)
                elif self.path in {"/api/layers/music/open", "/api/layers/sfx/open"}:
                    layer = self.path.split("/")[-2]
                    project.open_audio_mapping(layer, self._required_string(body, "segment_id"))
                    self._json(200, {"ok": True})
                elif self.path == "/api/visuals/create":
                    recipe_id = body.get("recipe_id")
                    if recipe_id is not None and not isinstance(recipe_id, str):
                        raise WorkbenchError("recipe_id must be a library recipe ID or null.")
                    result = project.create_visual_plan(
                        self._required_string(body, "segment_id"),
                        recipe_id,
                        self._required_string(body, "manifest_hash"),
                    )
                    self._json(201, result)
                elif self.path == "/api/visuals/open":
                    project.open_visual_plan(self._required_string(body, "segment_id"))
                    self._json(200, {"ok": True})
                elif self.path == "/api/segment/save":
                    result = project.save_segment(
                        self._required_string(body, "segment_id"), self._object(body, "updates"),
                        self._required_string(body, "manifest_hash"),
                    )
                    self._json(200, result)
                elif self.path == "/api/take/rate":
                    self._json(200, project.rate_take(
                        self._required_string(body, "segment_id"),
                        self._required_string(body, "take_key"),
                        self._required_string(body, "rating"),
                        self._required_string(body, "manifest_hash"),
                    ))
                elif self.path == "/api/segments/reorder":
                    self._json(200, {"state": project.reorder_segment(
                        self._required_string(body, "segment_id"), self._required_string(body, "target_id"),
                        self._required_string(body, "placement"), self._required_string(body, "manifest_hash"),
                    )})
                elif self.path == "/api/segments/insert":
                    self._json(200, project.insert_segment(
                        self._required_string(body, "after_id"), self._required_string(body, "title"),
                        self._required_string(body, "text"), self._required_string(body, "status"),
                        self._required_string(body, "manifest_hash"),
                    ))
                elif self.path == "/api/note":
                    segment_id = self._required_string(body, "segment_id")
                    project.save_note(segment_id, self._string(body, "note"))
                    self._json(200, {"ok": True, "state": project.state_payload()})
                elif self.path == "/api/codex/suggest":
                    segment_id = self._required_string(body, "segment_id")
                    note = self._string(body, "note")
                    project.save_note(segment_id, note)
                    if not codex_path:
                        raise WorkbenchError("Codex CLI was not found. Install or sign in to Codex, then restart this workbench. Your note is saved.", 503)
                    context, _ = project.codex_context(segment_id, note)
                    result = run_codex_suggestion(codex_path, project, segment_id, note)
                    suggestion = project.store_suggestion(segment_id, note, result, context["text"])
                    self._json(200, {"suggestion": suggestion, "state": project.state_payload()})
                elif self.path == "/api/suggestion/accept":
                    state = project.accept_suggestion(
                        self._required_string(body, "segment_id"),
                        self._required_string(body, "suggestion_id"),
                        self._required_string(body, "manifest_hash"),
                    )
                    self._json(200, {"state": state})
                elif self.path == "/api/suggestion/dismiss":
                    project.dismiss_suggestion(
                        self._required_string(body, "segment_id"),
                        self._required_string(body, "suggestion_id"),
                    )
                    self._json(200, {"ok": True, "state": project.state_payload()})
                elif self.path == "/api/work/clear":
                    self._json(200, {"removed_suggestions": project.clear_resolved(), "state": project.state_payload()})
                elif self.path == "/api/preview":
                    self._json(200, self._preview(self._string(body, "text")))
                elif self.path == "/api/preview/sequence":
                    self._preview_sequence(body.get("texts"))
                elif self.path == "/api/preview/stop":
                    with sequence_state_lock:
                        process = sequence_process
                        if process is not None and process.poll() is None:
                            process.terminate()
                    self._json(200, {"ok": True})
                elif self.path == "/api/preview/render":
                    self._json(200, self._render_sapi_preview())
                elif self.path == "/api/generate":
                    self._json(200, self._run_generation(assemble=False))
                elif self.path == "/api/assemble":
                    self._json(200, self._run_generation(assemble=True))
                else:
                    self._json(404, {"error": "Not found."})
            except WorkbenchError as exc:
                self._json(exc.status, {"error": str(exc)})
            except (KeyError, TypeError) as exc:
                self._json(400, {"error": f"Invalid request: {exc}"})

        @staticmethod
        def _required_string(body: dict[str, Any], key: str) -> str:
            value = body.get(key)
            if not isinstance(value, str) or not value.strip():
                raise WorkbenchError(f"{key} is required.")
            return value

        @staticmethod
        def _string(body: dict[str, Any], key: str) -> str:
            value = body.get(key)
            if not isinstance(value, str):
                raise WorkbenchError(f"{key} must be text.")
            return value

        @staticmethod
        def _object(body: dict[str, Any], key: str) -> dict[str, Any]:
            value = body.get(key)
            if not isinstance(value, dict):
                raise WorkbenchError(f"{key} must be an object.")
            return value

        def _preview(self, text: str) -> dict[str, Any]:
            if not text.strip() or len(text) > MAX_TEXT_CHARS:
                raise WorkbenchError("Preview text must not be empty or exceed the narration text limit.")
            script = TOOL_DIR / "preview_narration.py"
            result = run_tool([python_path, str(script), "--text", "-"], timeout=180, input_text=text)
            if not result["ok"]:
                message = result["error"] or result["output"] or "Transient preview failed."
                return {"ok": False, "error": message, "unsupported": "unavailable" in message.lower() or platform.system() != "Windows"}
            return {"ok": True, "message": result["output"] or "Preview finished."}

        def _render_sapi_preview(self) -> dict[str, Any]:
            nonlocal sapi_temp
            if platform.system() != "Windows":
                raise WorkbenchError("SAPI preview is available only on Windows.", 503)
            executable = shutil.which("powershell.exe") or shutil.which("powershell")
            if not executable:
                raise WorkbenchError("Windows PowerShell was not found.", 503)
            if not sapi_render_lock.acquire(blocking=False):
                raise WorkbenchError("A SAPI preview is already being rendered.", 409)
            try:
                data, _ = project.read_manifest()
                active = narration.active_segments(data)
                if not active or len(active) > 500:
                    raise WorkbenchError("SAPI preview needs 1 to 500 active beats.")
                texts = [segment["text"] for segment in active]
                if sum(len(text) for text in texts) > 250_000:
                    raise WorkbenchError("The active narration is too long for a quick SAPI preview.")
                pause_ms = int(data["settings"].get("pause_ms", 350))
                digest = text_hash(json.dumps([[(segment["id"], segment["text"]) for segment in active], pause_ms], ensure_ascii=False))
                if sapi_cache.get("digest") == digest and sapi_cache["path"].is_file():
                    return {"ok": True, "url": f"/api/audio/sapi-preview?v={digest}", "beats": sapi_cache["beats"], "cached": True}

                if sapi_temp is None:
                    sapi_temp = tempfile.TemporaryDirectory(prefix="vps-sapi-preview-")
                with tempfile.TemporaryDirectory(dir=sapi_temp.name, prefix="beats-") as beat_dir:
                    try:
                        result = subprocess.run(
                            [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                             "-File", str(TOOL_DIR / "preview_narration.ps1"), "-RenderSequence",
                             "-OutputDirectory", beat_dir],
                            input=json.dumps(texts, ensure_ascii=False), capture_output=True,
                            text=True, encoding="utf-8", errors="replace", timeout=300,
                            creationflags=getattr(subprocess, "CREATE_NO_WINDOW", 0),
                        )
                    except (OSError, subprocess.TimeoutExpired) as exc:
                        raise WorkbenchError(f"Could not render SAPI preview: {exc}", 503) from exc
                    if result.returncode:
                        raise WorkbenchError(result.stderr.strip() or "SAPI preview rendering failed.", 503)

                    timeline: list[dict[str, Any]] = []
                    cursor = 0
                    frames = bytearray()
                    format_key: tuple[Any, ...] | None = None
                    sample_rate = 0
                    for index, segment in enumerate(active):
                        beat_path = Path(beat_dir) / f"beat-{index:04d}.wav"
                        try:
                            with wave.open(str(beat_path), "rb") as beat_audio:
                                current_format = (beat_audio.getnchannels(), beat_audio.getsampwidth(),
                                                  beat_audio.getframerate(), beat_audio.getcomptype())
                                if format_key is None:
                                    format_key = current_format
                                    sample_rate = beat_audio.getframerate()
                                elif current_format != format_key:
                                    raise WorkbenchError("SAPI returned inconsistent audio formats between beats.", 503)
                                frame_count = beat_audio.getnframes()
                                frames.extend(beat_audio.readframes(frame_count))
                        except (OSError, EOFError, wave.Error) as exc:
                            raise WorkbenchError(f"Could not read SAPI beat {index + 1}: {exc}", 503) from exc
                        timeline.append({"id": segment["id"], "start": cursor / sample_rate,
                                         "end": (cursor + frame_count) / sample_rate})
                        cursor += frame_count
                        if index < len(active) - 1:
                            silent_frames = round(sample_rate * pause_ms / 1000)
                            frames.extend(b"\0" * silent_frames * format_key[0] * format_key[1])
                            cursor += silent_frames

                    output_path = Path(sapi_temp.name) / f"{digest}.wav"
                    with wave.open(str(output_path), "wb") as output:
                        output.setnchannels(format_key[0])
                        output.setsampwidth(format_key[1])
                        output.setframerate(sample_rate)
                        output.writeframes(frames)
                sapi_cache.update(digest=digest, path=output_path, beats=timeline)
                return {"ok": True, "url": f"/api/audio/sapi-preview?v={digest}", "beats": timeline, "cached": False}
            finally:
                sapi_render_lock.release()

        def _preview_sequence(self, texts: Any) -> None:
            nonlocal sequence_process
            if platform.system() != "Windows":
                raise WorkbenchError("SAPI sequence preview is available only on Windows.", 503)
            if (not isinstance(texts, list) or not texts or len(texts) > 500
                or any(not isinstance(text, str) or not text.strip() or len(text) > MAX_TEXT_CHARS for text in texts)):
                raise WorkbenchError("Preview sequence needs 1 to 500 nonempty narration beats.")
            executable = shutil.which("powershell.exe") or shutil.which("powershell")
            if not executable:
                raise WorkbenchError("Windows PowerShell was not found.", 503)
            if not sequence_run_lock.acquire(blocking=False):
                raise WorkbenchError("A SAPI sequence preview is already running.", 409)
            process: subprocess.Popen[str] | None = None
            try:
                process = subprocess.Popen(
                    [executable, "-NoLogo", "-NoProfile", "-NonInteractive", "-ExecutionPolicy", "Bypass",
                     "-File", str(TOOL_DIR / "preview_narration.ps1"), "-Sequence"],
                    stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                    text=True, encoding="utf-8", errors="replace", cwd=TOOL_DIR,
                )
                with sequence_state_lock:
                    sequence_process = process
                assert process.stdin is not None
                process.stdin.write(json.dumps(texts, ensure_ascii=False))
                process.stdin.close()
                self.send_response(200)
                self._headers("application/x-ndjson; charset=utf-8")
                self.send_header("Connection", "close")
                self.end_headers()
                self.close_connection = True

                def emit(event: str, **details: Any) -> None:
                    payload = json.dumps({"event": event, **details}, ensure_ascii=False).encode("utf-8") + b"\n"
                    self.wfile.write(payload)
                    self.wfile.flush()

                assert process.stdout is not None
                for line in process.stdout:
                    kind, _, number = line.strip().partition(" ")
                    if kind in {"START", "DONE"} and number.isdecimal() and int(number) < len(texts):
                        emit(kind.lower(), index=int(number))
                returncode = process.wait()
                if returncode:
                    assert process.stderr is not None
                    emit("error", message=process.stderr.read().strip() or "SAPI preview stopped unexpectedly.")
                else:
                    emit("complete")
            except (BrokenPipeError, ConnectionResetError):
                pass
            finally:
                if process is not None and process.poll() is None:
                    process.terminate()
                    try:
                        process.wait(timeout=5)
                    except subprocess.TimeoutExpired:
                        process.kill()
                        process.wait()
                with sequence_state_lock:
                    if sequence_process is process:
                        sequence_process = None
                sequence_run_lock.release()

        def _run_generation(self, assemble: bool) -> dict[str, Any]:
            if not project.manifest_operation_lock.acquire(blocking=False):
                raise WorkbenchError("A manifest edit, narration generation, or assembly is already running.", 409)
            try:
                project.read_manifest()
                if assemble:
                    command = [python_path, str(TOOL_DIR / "generate_narration.py"), "--manifest", str(project.manifest_path), "--assemble-only"]
                else:
                    command = [python_path, str(TOOL_DIR / "generate_narration.py"), "--manifest", str(project.manifest_path), "--generate-only"]
                result = run_tool(command, timeout=3600)
                result["state"] = project.state_payload()
                return result
            finally:
                project.manifest_operation_lock.release()

    return Handler


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Open a local script and narration workbench for one project.")
    parser.add_argument("--manifest", required=True, type=Path, help="The selected project's narration_manifest.json file.")
    parser.add_argument("--port", type=int, default=8766, help="Local browser port (default: 8766).")
    parser.add_argument("--codex", help="Optional path or command name for the Codex CLI.")
    parser.add_argument("--python", default=sys.executable, help="Python executable used by the existing narration scripts.")
    parser.add_argument("--library-config", type=Path, help="Local JSON config for an optional private Visual Library root.")
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    if not 1024 <= args.port <= 65535:
        print("Port must be between 1024 and 65535.", file=sys.stderr)
        return 2
    try:
        project = Project(args.manifest)
        project.read_manifest()
        project.catalog = library_catalog(args.library_config)
    except WorkbenchError as exc:
        print(str(exc), file=sys.stderr)
        return 2
    codex_path = resolve_codex(args.codex)
    server_type = type("WorkbenchHTTPServer", (ThreadingHTTPServer,), {"daemon_threads": True})
    try:
        server = server_type(("127.0.0.1", args.port), create_handler(project, codex_path, args.python))
    except OSError as exc:
        print(f"Could not start local server on 127.0.0.1:{args.port}: {exc}", file=sys.stderr)
        return 2
    print(f"Narration workbench for {project.manifest_path.parent.parent.name}")
    print(f"Open http://127.0.0.1:{args.port} in your browser. Press Ctrl+C to stop.")
    print(f"Codex CLI: {'available' if codex_path else 'not found'}; Windows SAPI preview: {'available' if platform.system() == 'Windows' else 'unavailable on this system'}")
    try:
        server.serve_forever(poll_interval=0.25)
    except KeyboardInterrupt:
        print("\nStopping the narration workbench.")
    finally:
        server.server_close()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

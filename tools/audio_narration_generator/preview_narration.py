"""Play a narration draft through the Windows SAPI voice without saving audio."""

from __future__ import annotations

import argparse
import json
import platform
import shutil
import subprocess
import sys
from pathlib import Path


POWERSHELL_SCRIPT = Path(__file__).with_suffix(".ps1")


class PreviewError(ValueError):
    """An actionable preview-input or runtime error."""


def manifest_segment_text(manifest_path: Path, segment_id: str) -> str:
    """Read one segment's text without changing the manifest."""
    try:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8-sig"))
    except FileNotFoundError as exc:
        raise PreviewError(f"Manifest not found: {manifest_path}") from exc
    except (OSError, UnicodeError) as exc:
        raise PreviewError(f"Could not read manifest: {exc}") from exc
    except json.JSONDecodeError as exc:
        raise PreviewError(f"Invalid JSON in {manifest_path}: {exc}") from exc

    if not isinstance(manifest, dict) or not isinstance(manifest.get("segments"), list):
        raise PreviewError("Manifest must contain a 'segments' array.")

    matches = [
        segment for segment in manifest["segments"]
        if isinstance(segment, dict) and segment.get("id") == segment_id
    ]
    if not matches:
        raise PreviewError(f"Segment ID not found: {segment_id}")
    if len(matches) != 1:
        raise PreviewError(f"Segment ID is ambiguous because it appears more than once: {segment_id}")

    segment = matches[0]
    status = segment.get("status", "active")
    if status == "deleted":
        raise PreviewError(f"Segment '{segment_id}' is marked deleted and cannot be previewed.")
    if not isinstance(status, str) or status not in {"active", "inactive"}:
        raise PreviewError(f"Segment '{segment_id}' has an unsupported status: {status!r}.")

    text = segment.get("text")
    if not isinstance(text, str) or not text.strip():
        raise PreviewError(f"Segment '{segment_id}' does not contain narration text.")
    return text


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Audition narration through Windows SAPI without creating an audio file."
    )
    source = parser.add_mutually_exclusive_group()
    source.add_argument("--manifest", type=Path, help="Narration manifest JSON to read")
    source.add_argument("--text", help="Inline draft text; use '-' to read UTF-8 text from stdin")
    parser.add_argument("--segment-id", help="Stable segment ID to read from --manifest")
    parser.add_argument("--voice", help="Optional installed Windows SAPI voice name")
    parser.add_argument("--rate", type=int, default=0, help="SAPI speaking rate from -10 to 10 (default: 0)")
    parser.add_argument("--list-voices", action="store_true", help="List installed Windows SAPI voices")
    args = parser.parse_args(argv)

    if not -10 <= args.rate <= 10:
        parser.error("--rate must be between -10 and 10.")
    if args.list_voices:
        if args.manifest is not None or args.segment_id is not None or args.text is not None:
            parser.error("--list-voices cannot be combined with text or manifest options.")
        return args
    if args.manifest is not None:
        if not args.segment_id:
            parser.error("--manifest requires --segment-id.")
    elif args.segment_id is not None:
        parser.error("--segment-id requires --manifest.")
    elif args.text is None:
        parser.error("Provide --manifest with --segment-id, or provide --text.")
    return args


def powershell_executable() -> str:
    executable = shutil.which("powershell.exe") or shutil.which("powershell")
    if not executable:
        raise PreviewError(
            "Windows PowerShell was not found. Install or enable Windows PowerShell 5.1, then retry."
        )
    return executable


def read_utf8_stdin() -> str:
    """Read piped draft text as UTF-8, independent of the Windows code page."""
    try:
        return sys.stdin.buffer.read().decode("utf-8-sig")
    except UnicodeDecodeError as exc:
        raise PreviewError("Piped preview text must be valid UTF-8.") from exc


def run_powershell(args: argparse.Namespace, spoken_text: str = "") -> int:
    if not POWERSHELL_SCRIPT.is_file():
        raise PreviewError(f"The SAPI playback script is missing: {POWERSHELL_SCRIPT}")

    command = [
        powershell_executable(), "-NoLogo", "-NoProfile", "-NonInteractive",
        "-ExecutionPolicy", "Bypass", "-File", str(POWERSHELL_SCRIPT),
        "-Rate", str(args.rate),
    ]
    if args.voice:
        command.extend(["-Voice", args.voice])
    if args.list_voices:
        command.append("-ListVoices")

    try:
        completed = subprocess.run(
            command,
            input=spoken_text,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            check=False,
        )
    except OSError as exc:
        raise PreviewError(f"Could not start Windows PowerShell: {exc}") from exc

    if completed.stdout:
        print(completed.stdout, end="")
    if completed.returncode:
        detail = completed.stderr.strip() or "Windows SAPI could not play the preview."
        print(detail, file=sys.stderr)
    elif completed.stderr.strip():
        print(completed.stderr, end="", file=sys.stderr)
    return completed.returncode


def main(argv: list[str] | None = None) -> int:
    try:
        args = parse_args(argv)
        if platform.system() != "Windows":
            raise PreviewError(
                "Transient narration preview currently supports Windows with Windows PowerShell 5.1 and SAPI. "
                "No alternate engine or audio-file fallback was started."
            )

        if args.list_voices:
            return run_powershell(args)
        if args.manifest is not None:
            spoken_text = manifest_segment_text(args.manifest, args.segment_id)
        elif args.text == "-":
            spoken_text = read_utf8_stdin()
        else:
            spoken_text = args.text
        if not spoken_text.strip():
            raise PreviewError("Preview text is empty.")
        return run_powershell(args, spoken_text)
    except PreviewError as exc:
        print(f"Preview unavailable: {exc}", file=sys.stderr)
        return 2
    except KeyboardInterrupt:
        print("Preview interrupted.", file=sys.stderr)
        return 130


if __name__ == "__main__":
    raise SystemExit(main())

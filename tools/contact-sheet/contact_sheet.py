#!/usr/bin/env python3
"""Create timestamped contact sheets from one video or a folder of videos.

Requires Python 3.10+, Pillow, FFmpeg, and FFprobe.
"""

from __future__ import annotations

import argparse
import json
import math
import shutil
import subprocess
import sys
import time
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont


THUMB_W = 480
THUMB_H = 270
DEFAULT_COLS = 5
DEFAULT_ROWS = 6
TARGET_FRAMES = 30
MIN_ADAPTIVE_INTERVAL = 0.5
MAX_ADAPTIVE_INTERVAL = 8.0
BG = (18, 18, 18)
LABEL_BG = (32, 32, 32)
TEXT_FG = (225, 225, 225)
BORDER = (66, 66, 66)
LABEL_H = 24
HEADER_H = 38
VIDEO_EXTENSIONS = {
    ".avi", ".flv", ".m2ts", ".m4v", ".mkv", ".mov", ".mp4",
    ".mpeg", ".mpg", ".mts", ".webm", ".wmv",
}


def require_tools() -> None:
    missing = [name for name in ("ffmpeg", "ffprobe") if shutil.which(name) is None]
    if missing:
        raise RuntimeError(
            f"Missing executable(s): {', '.join(missing)}. Install FFmpeg and add it to PATH."
        )


def video_duration(path: Path) -> float:
    result = subprocess.run(
        [
            "ffprobe", "-v", "error", "-show_entries", "format=duration",
            "-of", "json", str(path),
        ],
        capture_output=True,
        text=True,
        check=True,
    )
    duration = float(json.loads(result.stdout)["format"]["duration"])
    if duration <= 0:
        raise RuntimeError(f"Could not read a positive video duration: {path}")
    return duration


def adaptive_interval(duration: float, density: float = 1.0) -> float:
    """Choose a duration-aware interval, then scale it for more or fewer samples."""
    interval = duration / TARGET_FRAMES
    interval = max(MIN_ADAPTIVE_INTERVAL, min(MAX_ADAPTIVE_INTERVAL, interval))
    return max(0.01, round(interval / density, 2))


def extract_frames(path: Path, interval: float, temp_dir: Path) -> list[Path]:
    """Extract one evenly spaced frame per interval in a single sequential pass."""
    if temp_dir.exists():
        shutil.rmtree(temp_dir)
    temp_dir.mkdir(parents=True)

    scale_and_pad = (
        f"fps=1/{interval},"
        f"scale={THUMB_W}:{THUMB_H}:force_original_aspect_ratio=decrease,"
        f"pad={THUMB_W}:{THUMB_H}:(ow-iw)/2:(oh-ih)/2:color=black,setsar=1"
    )
    command = [
        "ffmpeg", "-hide_banner", "-loglevel", "error", "-i", str(path),
        "-map", "0:v:0", "-vf", scale_and_pad,
        str(temp_dir / "frame_%05d.png"), "-y",
    ]
    result = subprocess.run(command, capture_output=True, text=True)
    if result.returncode != 0:
        details = result.stderr.strip() or "FFmpeg returned an error without details."
        raise RuntimeError(f"Frame extraction failed for {path.name}:\n{details}")

    frames = sorted(temp_dir.glob("frame_*.png"))
    if not frames:
        raise RuntimeError(f"No video frames were extracted from {path}.")
    return frames


def load_font(size: int) -> ImageFont.ImageFont:
    for candidate in (
        "arial.ttf",
        "DejaVuSans.ttf",
    ):
        try:
            return ImageFont.truetype(candidate, size)
        except OSError:
            continue
    return ImageFont.load_default()


def timecode(seconds: float, interval: float) -> str:
    hours, remainder = divmod(seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    if abs(interval - round(interval)) > 1e-6:
        return f"{int(hours):02d}:{int(minutes):02d}:{seconds:05.2f}"
    return f"{int(hours):02d}:{int(minutes):02d}:{int(seconds):02d}"


def fit_title(draw: ImageDraw.ImageDraw, title: str, font: ImageFont.ImageFont, max_width: int) -> str:
    if draw.textbbox((0, 0), title, font=font)[2] <= max_width:
        return title
    shortened = title
    while shortened and draw.textbbox((0, 0), shortened + "…", font=font)[2] > max_width:
        shortened = shortened[:-1]
    return shortened + "…"


def build_page(
    frame_times: list[tuple[Path, float]],
    page_number: int,
    cols: int,
    rows: int,
    title: str,
    interval: float,
) -> Image.Image:
    cell_h = THUMB_H + LABEL_H
    canvas_w = cols * THUMB_W
    canvas_h = HEADER_H + rows * cell_h
    image = Image.new("RGB", (canvas_w, canvas_h), BG)
    draw = ImageDraw.Draw(image)
    small_font = load_font(14)
    header_font = load_font(16)

    heading = fit_title(draw, f"{title}  |  sheet {page_number}", header_font, canvas_w - 20)
    draw.text((10, 10), heading, fill=TEXT_FG, font=header_font)

    for index, (frame_path, seconds) in enumerate(frame_times):
        column = index % cols
        row = index // cols
        x = column * THUMB_W
        y = HEADER_H + row * cell_h

        with Image.open(frame_path) as frame:
            image.paste(frame.convert("RGB"), (x, y))

        label_y = y + THUMB_H
        draw.rectangle([x, label_y, x + THUMB_W, label_y + LABEL_H], fill=LABEL_BG)
        draw.text((x + 7, label_y + 4), timecode(seconds, interval), fill=TEXT_FG, font=small_font)
        draw.rectangle([x, y, x + THUMB_W - 1, label_y + LABEL_H - 1], outline=BORDER)

    return image


def interval_slug(interval: float) -> str:
    value = f"{interval:g}".replace(".", "p")
    return f"every-{value}s"


def render_video(
    video: Path,
    output_dir: Path,
    interval_override: float | None,
    density: float,
    cols: int,
    rows: int,
) -> tuple[int, int, float, float]:
    started = time.perf_counter()
    duration = video_duration(video)
    interval = (
        interval_override
        if interval_override is not None
        else adaptive_interval(duration, density)
    )
    temp_dir = output_dir / ".contact-sheet-frames"
    output_dir.mkdir(parents=True, exist_ok=True)

    try:
        frames = extract_frames(video, interval, temp_dir)
        pairs = [(frame, index * interval) for index, frame in enumerate(frames)]
        per_page = cols * rows
        pages = [pairs[index:index + per_page] for index in range(0, len(pairs), per_page)]
        prefix = f"{video.stem}_{interval_slug(interval)}"

        for page_number, page_pairs in enumerate(pages, start=1):
            page = build_page(page_pairs, page_number, cols, rows, video.stem, interval)
            destination = output_dir / f"{prefix}_sheet_{page_number:03d}.png"
            page.save(destination, "PNG", optimize=False, compress_level=3)

        elapsed = time.perf_counter() - started
        return len(frames), len(pages), elapsed, interval
    finally:
        shutil.rmtree(temp_dir, ignore_errors=True)


def discover_videos(source: Path) -> tuple[list[Path], Path, bool]:
    if source.is_file():
        if source.suffix.lower() not in VIDEO_EXTENSIONS:
            raise ValueError(f"Unsupported video extension: {source.suffix}")
        return [source], source.parent, False
    if source.is_dir():
        videos = sorted(
            path for path in source.rglob("*")
            if path.is_file() and path.suffix.lower() in VIDEO_EXTENSIONS
        )
        if not videos:
            raise ValueError(f"No supported video files found under {source}")
        return videos, source, True
    raise FileNotFoundError(f"Input path does not exist: {source}")


def main() -> int:
    # Windows consoles may use a legacy code page that cannot print some legal
    # filename characters. Keep those names from aborting an otherwise valid batch.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, "reconfigure"):
            stream.reconfigure(errors="backslashreplace")

    parser = argparse.ArgumentParser(
        description="Create timestamped contact sheets from a video or a folder of videos."
    )
    parser.add_argument("input", help="Video file or folder to scan for videos")
    parser.add_argument(
        "--out-dir", help="Output root (default: contact-sheets next to the input)"
    )
    sampling_group = parser.add_mutually_exclusive_group()
    sampling_group.add_argument(
        "--every", type=float,
        help="Use a fixed number of seconds between frames instead of adaptive sampling",
    )
    sampling_group.add_argument(
        "--density", type=float, default=1.0,
        help="Scale adaptive sampling: 2 gives about twice as many frames; 0.5 gives half as many (default: 1)",
    )
    parser.add_argument("--cols", type=int, default=DEFAULT_COLS)
    parser.add_argument("--rows", type=int, default=DEFAULT_ROWS)
    args = parser.parse_args()

    if args.every is not None and (not math.isfinite(args.every) or args.every <= 0):
        parser.error("--every must be greater than zero")
    if not math.isfinite(args.density) or args.density <= 0:
        parser.error("--density must be greater than zero")
    if args.cols <= 0 or args.rows <= 0:
        parser.error("--cols and --rows must be greater than zero")

    try:
        require_tools()
        source = Path(args.input).expanduser().resolve()
        videos, source_root, is_batch = discover_videos(source)
        output_root = (
            Path(args.out_dir).expanduser().resolve()
            if args.out_dir
            else source_root / "contact-sheets"
        )

        sampling = (
            f"fixed every {args.every:g}s"
            if args.every is not None
            else f"adaptive (~{TARGET_FRAMES} frames for short videos, density {args.density:g}x)"
        )
        print(f"Videos: {len(videos)} | Sampling: {sampling} | Grid: {args.cols}x{args.rows}")
        print(f"Output: {output_root}\n")
        total_started = time.perf_counter()
        failures = 0

        for index, video in enumerate(videos, start=1):
            if is_batch:
                relative = video.relative_to(source_root)
                video_output = output_root / relative.parent / video.stem
            else:
                video_output = output_root / video.stem

            print(f"[{index}/{len(videos)}] {video.name}")
            try:
                frames, pages, elapsed, interval = render_video(
                    video, video_output, args.every, args.density, args.cols, args.rows
                )
                print(
                    f"  {frames} frames at {interval:g}s -> {pages} sheet(s) in {elapsed:.1f}s"
                )
            except (OSError, RuntimeError, ValueError, subprocess.SubprocessError) as error:
                failures += 1
                print(f"  ERROR: {error}", file=sys.stderr)

        print(f"\nFinished in {time.perf_counter() - total_started:.1f}s; failures: {failures}")
        return 1 if failures else 0
    except (OSError, RuntimeError, ValueError) as error:
        print(f"Error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())

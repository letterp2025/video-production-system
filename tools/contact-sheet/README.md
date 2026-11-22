# Contact Sheet

Create timestamped frame sheets from one video or a folder of videos. Use an adaptive overview first, then sample a short passage more densely to inspect motion.

## Requirements

- Python 3.10 or newer
- Pillow
- FFmpeg and FFprobe available on PATH

Install Pillow with:

    python -m pip install Pillow

## Commands

From the repository root:

    python tools/contact-sheet/contact_sheet.py path/to/video.mp4

By default, the tool chooses an interval based on the video length and aims for roughly 30 frames per source. Output is written to a contact-sheets folder next to the input.

Increase the adaptive sample density:

    python tools/contact-sheet/contact_sheet.py path/to/video.mp4 --density 2

Sample at a fixed interval, such as one frame every quarter second:

    python tools/contact-sheet/contact_sheet.py path/to/short-clip.mp4 --every 0.25 --cols 4 --rows 4

Choose another output root:

    python tools/contact-sheet/contact_sheet.py path/to/video.mp4 --out-dir path/to/output

Run --help for all options. Trim a long source to the passage of interest before using a very dense interval. Dense sheets grow with the number of extracted frames.

## Output and limits

The tool writes timestamped contact-sheet images and per-video outputs under the selected output folder. It uses FFmpeg to extract frames and Pillow to lay out the sheets. It does not identify objects, describe a scene, or infer animation curves; use the sheets as visual evidence for human analysis.

The font is selected from fonts available to Pillow, with its built-in fallback if common fonts are unavailable. Exact appearance can therefore vary by system.
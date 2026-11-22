# Word Focus Subtitles

Generate an Advanced SubStation Alpha (ASS) subtitle file from plain text. The full text remains visible while one word at a time changes to the active color.

## Requirements

- Node.js 18 or newer
- No npm packages

## Input

Use a UTF-8 text file with the words to display. Whitespace is normalized. The tool wraps lines based on the chosen resolution and font size, then estimates timing from the word count and punctuation. Adjust the pacing to match the actual narration.

The sample input.txt is generic example content. Replace it or supply another text file.

## Generate

From the repository root:

    node tools/word-focus-subtitles/generate.mjs path/to/input.txt

By default, the ASS file is written to an output folder in the current working directory. Specify a destination with:

    node tools/word-focus-subtitles/generate.mjs path/to/input.txt --output path/to/subtitles.ass

Use --help to list timing, font, color, resolution, and wrapping options.

## Limits

The script estimates timing from text; it does not analyze speech or align words to an audio waveform. Review and adjust the generated ASS timing before final video export. The selected font must be available to the subtitle renderer.
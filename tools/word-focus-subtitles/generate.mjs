#!/usr/bin/env node

import fs from 'node:fs';
import path from 'node:path';

const defaults = {
  secondsPerWord: 0.42,
  commaPause: 0.08,
  sentencePause: 0.28,
  font: 'Arial',
  fontSize: 72,
  width: 1920,
  height: 1080,
  gray: 'AAAAAA',
  black: '000000',
  charsPerLine: null,
};

function showHelp() {
  process.stdout.write(`Word Focus Subtitles\n\nUsage:\n  node generate.mjs <input.txt> [options]\n\nOptions:\n  --output <file.ass>       Output file (default: output/<input-name>.ass)\n  --seconds-per-word <n>    Base time per word in seconds (default: ${defaults.secondsPerWord})\n  --comma-pause <n>         Extra pause after commas, colons, and semicolons (default: ${defaults.commaPause})\n  --sentence-pause <n>      Extra pause after . ! ? (default: ${defaults.sentencePause})\n  --font <name>             Regular font family (default: ${defaults.font})\n  --font-size <n>           Font size in pixels at the chosen resolution (default: ${defaults.fontSize})\n  --width <n>               Video width (default: ${defaults.width})\n  --height <n>              Video height (default: ${defaults.height})\n  --gray <RRGGBB>           Inactive word color (default: ${defaults.gray})\n  --black <RRGGBB>          Active word color (default: ${defaults.black})\n  --chars-per-line <n>      Override automatic line wrapping\n  -h, --help                Show this help\n`);
}

function parseArgs(args) {
  const options = { ...defaults };
  let inputFile = null;
  let outputFile = null;

  for (let i = 0; i < args.length; i += 1) {
    const arg = args[i];
    if (arg === '-h' || arg === '--help') {
      showHelp();
      process.exit(0);
    }
    if (!arg.startsWith('--')) {
      if (inputFile) throw new Error(`Unexpected argument: ${arg}`);
      inputFile = arg;
      continue;
    }

    const value = args[i + 1];
    if (!value || value.startsWith('--')) throw new Error(`Missing value for ${arg}`);
    i += 1;

    switch (arg) {
      case '--output': outputFile = value; break;
      case '--seconds-per-word': options.secondsPerWord = Number(value); break;
      case '--comma-pause': options.commaPause = Number(value); break;
      case '--sentence-pause': options.sentencePause = Number(value); break;
      case '--font': options.font = value; break;
      case '--font-size': options.fontSize = Number(value); break;
      case '--width': options.width = Number(value); break;
      case '--height': options.height = Number(value); break;
      case '--gray': options.gray = value.replace(/^#/, '').toUpperCase(); break;
      case '--black': options.black = value.replace(/^#/, '').toUpperCase(); break;
      case '--chars-per-line': options.charsPerLine = Number(value); break;
      default: throw new Error(`Unknown option: ${arg}`);
    }
  }

  if (!inputFile) throw new Error('Provide a text file. Use --help to see options.');
  for (const key of ['secondsPerWord', 'commaPause', 'sentencePause', 'fontSize']) {
    if (!Number.isFinite(options[key]) || options[key] < 0 || (key === 'fontSize' && options[key] === 0)) {
      throw new Error(`Invalid value for ${key.replace(/[A-Z]/g, (letter) => `-${letter.toLowerCase()}`)}.`);
    }
  }
  for (const key of ['width', 'height']) {
    if (!Number.isInteger(options[key]) || options[key] < 100) throw new Error(`${key} must be an integer of at least 100.`);
  }
  if (options.charsPerLine !== null && (!Number.isInteger(options.charsPerLine) || options.charsPerLine < 1)) {
    throw new Error('--chars-per-line must be a positive integer.');
  }
  for (const key of ['gray', 'black']) {
    if (!/^[0-9A-F]{6}$/u.test(options[key])) throw new Error(`--${key} must be a six-digit RGB color.`);
  }
  if (!options.font.trim() || /[\r\n,]/u.test(options.font)) throw new Error('--font must be a single font name.');

  return { inputFile, outputFile, options };
}

function escapeAssText(word) {
  return word.replaceAll('\\', '\\\\').replaceAll('{', '\\{').replaceAll('}', '\\}');
}

function wrapWords(words, options) {
  const maxChars = options.charsPerLine ?? Math.max(12, Math.floor((options.width / (options.fontSize * 0.52)) * 0.88));
  const lines = [];
  let line = [];
  let lineLength = 0;

  for (const word of words) {
    const nextLength = lineLength + (line.length ? 1 : 0) + word.length;
    if (line.length && nextLength > maxChars) {
      lines.push(line);
      line = [];
      lineLength = 0;
    }
    line.push(word);
    lineLength += (line.length > 1 ? 1 : 0) + word.length;
  }
  if (line.length) lines.push(line);
  return lines;
}

function timecode(seconds) {
  const centiseconds = Math.max(0, Math.round(seconds * 100));
  const hours = Math.floor(centiseconds / 360000);
  const minutes = Math.floor((centiseconds % 360000) / 6000);
  const remainingSeconds = Math.floor((centiseconds % 6000) / 100);
  const fraction = centiseconds % 100;
  return `${hours}:${String(minutes).padStart(2, '0')}:${String(remainingSeconds).padStart(2, '0')}.${String(fraction).padStart(2, '0')}`;
}

function punctuationPause(word, options) {
  const ending = word.replace(/["')}\]]+$/u, '');
  if (/[.!?]$/u.test(ending)) return options.sentencePause;
  if (/[,;:]$/u.test(ending)) return options.commaPause;
  return 0;
}

function makeSubtitle(text, options) {
  const words = text.replace(/\r\n?/gu, '\n').trim().split(/\s+/u).filter(Boolean);
  if (!words.length) throw new Error('The input file is empty. Add the text you want to display.');

  const lines = wrapWords(words, options);
  const color = (rgb) => `&H00${rgb.match(/../gu).reverse().join('')}&`;
  const gray = color(options.gray);
  const black = color(options.black);
  const events = [];
  let cursor = 0;

  for (let activeIndex = 0; activeIndex < words.length; activeIndex += 1) {
    const duration = options.secondsPerWord + punctuationPause(words[activeIndex], options);
    const end = cursor + Math.max(duration, 0.01);
    let globalIndex = 0;
    const renderedLines = lines.map((line) => {
      const rendered = line.map((word) => {
        const active = globalIndex === activeIndex;
        globalIndex += 1;
        return `{\\1c${active ? black : gray}}${escapeAssText(word)}`;
      });
      return rendered.join(' ');
    });
    const textLine = `{\\an5\\pos(${Math.round(options.width / 2)},${Math.round(options.height / 2)})}${renderedLines.join('\\N')}`;
    events.push(`Dialogue: 1,${timecode(cursor)},${timecode(end)},Default,,0,0,0,,${textLine}`);
    cursor = end;
  }

  const background = `Dialogue: 0,0:00:00.00,${timecode(cursor)},Default,,0,0,0,,{\\an7\\pos(0,0)\\bord0\\shad0\\1c&H00FFFFFF&\\p1}m 0 0 l ${options.width} 0 ${options.width} ${options.height} 0 ${options.height} 0 0{\\p0}`;
  const script = `[Script Info]\nTitle: Word Focus Subtitles\nScriptType: v4.00+\nWrapStyle: 2\nScaledBorderAndShadow: yes\nPlayResX: ${options.width}\nPlayResY: ${options.height}\n\n[V4+ Styles]\nFormat: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding\nStyle: Default,${options.font},${options.fontSize},${gray},${gray},&H00000000,&H00000000,0,0,0,0,100,100,0,0,1,0,0,5,40,40,40,1\n\n[Events]\nFormat: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text\n${background}\n${events.join('\n')}\n`;

  return { script, duration: cursor, wordCount: words.length };
}

function main() {
  try {
    const { inputFile, outputFile, options } = parseArgs(process.argv.slice(2));
    const inputPath = inputFile === '-' ? null : path.resolve(inputFile);
    const input = inputPath ? fs.readFileSync(inputPath, 'utf8') : fs.readFileSync(0, 'utf8');
    const { script, duration, wordCount } = makeSubtitle(input, options);
    const defaultName = inputPath ? `${path.basename(inputPath, path.extname(inputPath))}.ass` : 'word-focus.ass';
    const destination = path.resolve(outputFile ?? path.join('output', defaultName));
    fs.mkdirSync(path.dirname(destination), { recursive: true });
    fs.writeFileSync(destination, script, 'utf8');
    process.stdout.write(`Created ${destination}\n${wordCount} words, ${duration.toFixed(2)} seconds\n`);
  } catch (error) {
    process.stderr.write(`${error.message}\n`);
    process.exitCode = 1;
  }
}

main();

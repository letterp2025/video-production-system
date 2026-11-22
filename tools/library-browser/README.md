# Visual Library Browser

The Visual Library Browser is a read-only local website for browsing the public visual libraries alongside an explicitly configured private library folder. It scans `NOTES.md` entry files, shows each entry's Public or Private scope, and displays local previews when available.

The server uses only Python's standard library. It binds to `127.0.0.1`, has no edit or upload endpoints, and serves files only from the configured library roots. It does not send library content to a remote service.

## Run it

From the public repository root in PowerShell, connect a private library root with a JSON config:

```powershell
python tools/library-browser/server.py `
  --config 'C:\path\to\library-browser.config.json'
```

The JSON config contains only one property, `private_root`, whose value is an absolute path:

```json
{
  "private_root": "C:\\path\\to\\private_visual_libraries"
}
```

The config belongs with the private workspace that owns those entries. Do not put a private path or config file in this public repository. The server accepts `--private-root` directly for quick runs; if both options are supplied, `--private-root` takes precedence. `--config` configures only the private library path, not the page appearance or other server behavior.

Open `http://127.0.0.1:8765`. Stop the server with `Ctrl+C`. The public root defaults to this repository's `libraries/` folder. Use `--port 8766` if the default port is busy. To browse public entries only, omit `--config` and `--private-root`.

The private root must contain one or more library folders directly, for example:

```text
private_visual_libraries/
  visual_reference_library/
  visual_elements_library/
  visual_animations_library/
```

Each entry needs its own folder with a `NOTES.md` file. The full folder basename is its stable ID, for example `REF-pindown-labasad-design`, `ELM-pixel-cell-grid`, or `ANM-cell-grid-shape-reveal`. Use the matching type prefix and a descriptive kebab-case slug, and keep IDs unique across the public and private roots. The browser searches common local preview folders such as `preview/`, `render/LOW/`, and `reference/element-sheets/`. Media and project files can remain ignored by Git while still appearing in the browser on this computer.

## Use the browser

- Choose Everything, Public, or Private to control which entries appear.
- Filter by References, Elements, or Animations.
- Search IDs, names, status text, and note summaries.
- Select an entry to inspect its local preview and full notes.

Every card repeats its visibility label. Private items are read from the private root at runtime; no private path is stored in this public repository.

## Limits

- This is a local catalog, not a content manager. Edit Markdown and source files in their normal folders.
- It does not publish, synchronize, copy, rename, or delete entries.
- Markdown is displayed as text in the detail view; embedded links and formatting are not rendered.
- The preview picker chooses the first supported local image or video it finds in the documented folders.
- The app must remain bound to `127.0.0.1`; do not change it to listen on a network interface.

## Test

```powershell
python -m unittest discover -s tools/library-browser -v
```

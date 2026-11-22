# Video Production System Repository Instructions

These instructions apply to this public repository.

## Local-only Codex notes

- The root-level `IGNORED_DOCS/` folder is intentionally Git-ignored and is for private, machine-specific Codex reference notes, such as local tool locations and workflows.
- Read the relevant note there when a task depends on local tools. Keep personal paths, private workflow details, and other local-only information in that ignored folder; do not force-add or copy it into public files unless the user explicitly asks.
- Preserve the root-level ignore rule for this folder. `IGNORED_DOCS/how_to_use.md` contains the local narration workbench launch command.

## Git commits

- Commit completed task changes before handing work back to the user. Include the related source, tests, and documentation in the same logical commit.
- Do not include unrelated changes, generated media, voice recordings, rendered outputs, caches, secrets, or local project files. Report unrelated changes and leave them untouched.
- Before committing, run relevant checks, `git status --short`, and `git diff --check`. Review the staged paths and sizes; treat 10 MiB as the default maximum for a tracked file.
- Use a concise imperative commit message. Verify that Git reports a successful commit, then report its hash. Do not push unless requested.

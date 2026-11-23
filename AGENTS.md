# Video Production System Repository Instructions

These instructions apply to this public repository.

## Local-only Codex notes

- The root-level `IGNORED_DOCS/` folder is intentionally Git-ignored and is for private, machine-specific Codex reference notes, such as local tool locations and workflows.
- Read the relevant note there when a task depends on local tools. Keep personal paths, private workflow details, and other local-only information in that ignored folder; do not force-add or copy it into public files unless the user explicitly asks.
- Preserve the root-level ignore rule for this folder. `IGNORED_DOCS/how_to_use.md` contains the local narration workbench launch command.

## Task-order documents

- Put repository-wide task orders in `docs/TASKS/` and name each file `TASK-ORDER_<CONCISE_TOPIC>.md`, using uppercase words separated by underscores.
- A task order should capture the objective, user workflow, data ownership and storage, requirements, boundaries, implementation phases, acceptance checks, status, and related documents.
- When asked to plan a task order first, document the requested future behavior without implementing it in the same pass unless the user separately asks for implementation.
- Keep tool-specific task histories in their owning tool's documentation folder; link to a repository-wide task order when the scopes are related.

## Git commits

- Commit completed task changes before handing work back to the user. Include the related source, tests, and documentation in the same logical commit.
- Do not include unrelated changes, generated media, voice recordings, rendered outputs, caches, secrets, or local project files. Report unrelated changes and leave them untouched.
- Before committing, run relevant checks, `git status --short`, and `git diff --check`. Review the staged paths and sizes; treat 10 MiB as the default maximum for a tracked file.
- Use a concise imperative commit message. Verify that Git reports a successful commit, then report its hash. Do not push unless requested.

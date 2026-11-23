# Global rule template: project document conventions

This is the rule agents read in every session of every project. It is part of the skill and holds nothing of any
one person: `docs.mjs setup` fills in this computer's values and installs the section between the markers for
Claude Code (`~/.claude/rules/rein-managing-project-docs.md`) and Codex (between the same markers in
`~/.codex/AGENTS.md`). After upgrading the skill, run `setup` again so the installed copy follows.

Placeholders: `__STORE__` becomes this computer's store path (or a sentence saying there is none); `__TOOL__` becomes
`node "<installed skill>/scripts/docs.mjs"`; `__TEMPLATES__` becomes the installed skill's `assets/templates/` folder.

When editing the section, keep four things:

- The table of what goes where stays here. It must be in front of the agent every time; a skill is not always
  remembered.
- Whether a project commits `docs/process/` is the user's decision per project. No default is written here, only
  "check whether it is decided; if not, follow what the user said or ask".
- Multi-step, occasional work (setting up, changing the switch, adding a project's own documents, restoring, wrapping
  up, tidying) belongs in the skill, not here.
- At most 30 lines. Every extra line makes every other rule a little less likely to be followed.

<!-- rein-managing-project-docs:begin -->
## Project documents (all projects)

Every project keeps its documents under `docs/`, named the same way everywhere. Tool: __TOOL__, written `docs.mjs` below. Templates: __TEMPLATES__. Backup store: __STORE__.

**Whether a project commits `docs/process/` is my decision, per project. Never pick it for me.**

- No `docs/process/` yet (or in a git worktree): run `docs.mjs where` before writing a document there and do what it says. Decided by its registry entry or a group rule I wrote: `docs.mjs init` if it says so, no question. Not managed: follow the project's own rules, ask nothing. Not decided: if my words settle it ("open source", "company repository, add no files" → `--no-commit`; "keep docs with the code" → `--commit`), run `docs.mjs init` with that and tell me; otherwise ask me once: commit `docs/process/` with the code, or keep it out (ignored on this computer, backed up to the store)? Until I answer, drafts go in `.scratch/`.

| What | Where |
| --- | --- |
| Rules for agents | `AGENTS.md`, with a "where documents are" section; `CLAUDE.md` holds only `@AGENTS.md` |
| Code map · coding conventions · business terms (optional) | `docs/ARCHITECTURE.md` · `docs/CONVENTION.md` (long: `docs/conventions/` with a `README.md` index) · `docs/CONTEXT.md` |
| One piece of work: plan, test record, scripts, data, mockups, screenshots | `docs/process/work/YYYY-MM-DD-<short-name>/`: `plan.md`, `test.md` or `test.html`, `scripts/`, `data/`, `mockups/`, `evidence/`; when done, into `work/archive/` |
| A choice someone will ask "why" about, with options turned down | `docs/process/decisions/YYYY-MM-DD-<short-name>.md` |
| Research, open ideas | `docs/process/notes/YYYY-MM-DD-<short-name>.md` or `.html` |
| A page explaining to me how something works | `docs/process/explain/<topic>.html` or `.md`, no date, edited in place |
| A product requirement document to analyze | The requirements skill; ask me where its folder goes, `docs/process/requirements/` if I do not say |
| Drafts, trial output | `.scratch/`; delete when done |

- The first two rows are the project's own: you keep their names and places; their content is the project's; they are not backed up; whether they are committed is the project's business. Never move them into `docs/process/` or the store.
- HTML pages start from the templates `explain.html`, `test.html` or `note.html`: copy one, translate every word, fill it, keep its styles. Plans and decisions are Markdown.
- Names: lowercase English words joined by hyphens; today's date. Text: in my language. No status block: `work/` is ongoing, `work/archive/` is done. No `PLAN.md`, `SUMMARY.md`, `*-v2.*`, no working documents loose at the project root or the top of `docs/`.
- In a project that does not commit `docs/process/`: after writing or changing documents there, run `docs.mjs backup` (it commits in the store; never push). Never edit the store's copy.
- `docs/process/` may be ignored by git, and searching the whole project then skips it: look there directly. To understand a project, read `AGENTS.md`, the documents it lists and the open `work/` (skip `work/archive/` unless I mention it).
- "Write it down", "keep a record" mean a file here, not your own memory and not an online document. A small change is explained by its commit message.
- Tools with their own document home (`.rein/`, `.kiro/`, `.specify/`, `openspec/`, ticket tools' work items): requirements, specs, tasks and acceptance go through that tool's commands; never write its files by hand.
- Setting up, changing whether a project commits, adding a project's own documents, restoring on a new computer, wrapping up work, tidying scattered documents: use the skill rein-managing-project-docs.
<!-- rein-managing-project-docs:end -->

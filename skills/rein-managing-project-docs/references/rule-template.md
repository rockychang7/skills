# Global rule template: project document conventions

This is the rule agents read in every session of every project. It is part of the skill and holds nothing of any
one person: `docs.mjs setup` fills in this computer's two values and installs the section between the markers for
Claude Code (`~/.claude/rules/rein-managing-project-docs.md`) and Codex (between the same markers in
`~/.codex/AGENTS.md`). After upgrading the skill, run `setup` again so the installed copy follows.

Placeholders: `__STORE__` becomes this computer's store path (or a sentence saying there is none); `__TOOL__` becomes
`node "<installed skill>/scripts/docs.mjs"`.

When editing the section, keep four things:

- The table of what to write, what to call it and where it goes stays here. It must be in front of the agent every
  time; a skill is not always remembered.
- Where each project's documents go is the user's decision per project. No default is written here, only "check
  whether it is decided; if not, follow what the user said or ask".
- Multi-step, occasional work (creating the store, registering, changing an arrangement, moving documents, wrapping
  up, tidying) belongs in the skill, not here.
- At most 40 lines. Every extra line makes every other rule a little less likely to be followed.

<!-- rein-managing-project-docs:begin -->
## Project documents (all projects)

Private store (another git repository, outside every project, for documents kept out of project repositories): __STORE__. Tool: __TOOL__, written `docs.mjs` below.

**Whether a project's documents go in its repository or in the store is my decision, per project, recorded in the registry. Never pick a default for me.**

- Before writing any type marked "per project" below, run `docs.mjs where` and do what it says:
  - Decided (by the project's entry or a group rule I wrote): put files there. Not registered yet: run `docs.mjs init` first; no need to ask.
  - Not managed: the project follows its own rules; write documents the way its rule files say and ask nothing.
  - Not decided: if my words already settle it ("this will be open source, keep internal docs out", "keep docs with the code", "this is the company's repository, add no files"), record it with `docs.mjs init --in-repo …` and tell me what you set; otherwise ask me once, offering the choices `where` lists. Until I answer, write none of these types; drafts go in `.scratch/`.
  - The store is needed but this computer has none: create one with the skill rein-managing-project-docs; its name and place are mine to say, so ask.

| Type | When | Name | Where |
| --- | --- | --- | --- |
| User-facing docs | Usage, install or public interfaces change | `README.md`, `docs/<topic>.md`, `CHANGELOG.md` | Repository |
| Internal docs | Explaining how the project works now (architecture, runtime, deployment, data); update in place when code changes | `internals/<topic>.md`, e.g. `architecture.md`; no date or version | Per project |
| Decision records | A choice someone will later ask "why" about, with options turned down | `decisions/YYYY-MM-DD-<short-name>.md` | Per project |
| Work folders (one per piece of work) | A plan to show me first, work across sessions, or a test record to keep | `work/YYYY-MM-DD-<short-name>/`: `plan.md`, `test.md`, `test/` data and throwaway scripts, `evidence/` screenshots and logs | Per project |
| Notes | Research or open ideas worth keeping | `notes/YYYY-MM-DD-<short-name>.md` | Per project |
| Scratch | Drafts, trial output | `.scratch/` in the project; delete when done | Never committed |

- "Per project": in the repository, `docs/` plus the path above; in the store, `<store>/projects/<project>/` plus the same path.
- If I say "keep this one out" or "put this one in", do that. If a type goes in the repository but this document holds accounts, internal addresses, customer names, costs or unfixed security weaknesses, ask me first.
- Do not write what is not needed: a small change is explained by its commit message. No `PLAN.md`, `SUMMARY.md`, `*-v2.md`; no working documents loose at the project root or the root of `docs/`.
- File names: lowercase English words joined by hyphens; today's date. Titles and text: in my language.
- Front matter. Internal docs: `title`, `updated`. Decisions: `title`, `date`, `status` (`accepted`; when replaced, `superseded` plus `superseded_by: <new file>`, keep the old file). Work folder `plan.md` (or `test.md` without a plan): `title`, `date`, `status` (`active`, `done`, `dropped`). Notes: `title`, `date`.
- "Write it down", "make it a document", "keep a record" mean a file by this table, not your own memory and not an online document.
- To understand a project, besides the code read its `internals/`, `decisions/` and open `work/` (skip `work/archive/` unless I mention it).
- After writing into the store, commit it there (never push) and tell me where. If the store cannot be found or written, do not fall back to the repository: use `.scratch/` and tell me.
- Re-runnable tests belong to the code, in the project's own test folder.
- Tools with their own document home (`.rein/`, `.kiro/`, `.specify/`, `openspec/`, ticket tools' work items): requirements, specs, tasks, acceptance and ticket material go through that tool's commands; never write its files by hand or add a `plan.md` beside it. If the tool cannot be used, tell me and follow this table meanwhile.
- Creating the store, registering a project, changing an arrangement, moving documents between repository and store, wrapping up finished work, tidying scattered documents: use the skill rein-managing-project-docs.
<!-- rein-managing-project-docs:end -->

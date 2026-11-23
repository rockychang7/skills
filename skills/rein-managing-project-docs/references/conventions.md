# Project document conventions: what to write, what to call it, where it goes, what to do when it is out of date

This is the full text of the conventions in the skill `rein-managing-project-docs`, and the only place that says
where project documents go: other tools and repositories that need it link here instead of keeping a copy.
It is the same for every person and every project. Only two things differ per person, and neither is written here:
the store's name and place (in the config file), and whether each project commits `docs/process/` (in the registry).

## In one minute

- **Every project keeps its documents under `docs/`, named the same way everywhere.**
- **The project's own documents** sit at fixed names and places: `AGENTS.md`, `CLAUDE.md` (only `@AGENTS.md`),
  `docs/ARCHITECTURE.md`, `docs/CONVENTION.md`, optionally `docs/CONTEXT.md`. These conventions fix their names and
  places and keep a short "where documents are" section in `AGENTS.md`; what they say is the project's; they are not
  backed up; whether they are committed is the project's business.
- **What is made while working with an agent** goes in `docs/process/`: plans, test records, throwaway scripts and
  data, mockups, screenshots, explainer pages, decision records, research. Any format: Markdown, HTML, SQL, scripts,
  images.
- **One switch per project: commit `docs/process/` or not.** The user decides, per project or per group of projects;
  there is no default. Not committed means git ignores the folder on this computer only (`.git/info/exclude`; no file
  in the project changes, so it works in repositories that are not the user's to add files to).
- **The store is a backup, not a place to work in.** Documents that are not committed have no history and are lost
  with the disk or with `git clean -x`. `docs.mjs backup` copies them, one way, into a private git repository outside
  every project (the store) and commits there. The project's copy is always the original; nobody edits the store's.
  The store is optional: someone who commits every project's `docs/process/` never needs one.

## Where everything is

```text
skill rein-managing-project-docs/     the same for everyone; installed and upgraded with the skill, holds no one's data
├── SKILL.md                          multi-step work: set up, register, change the switch, own documents, pages, backup, wrap up, tidy
├── references/
│   ├── conventions.md                these conventions
│   ├── checklist.md                  what to check by hand when changing the switch
│   └── rule-template.md              the global rule template (setup fills in this computer's paths)
├── assets/templates/                 plan.md, test.md, decision.md, note.md; explain.html, test.html, note.html
│   └── project/                      skeletons of the project's own documents
├── assets/store/                     the first files of a new store
└── scripts/docs.mjs                  setup / where / init / check / backup / restore / group

~/.config/rein-managing-project-docs/
├── config.json                       this computer: where the store is (null without one)
└── local.json                        this computer: where each project sits, and when it was last backed up

<project>/
├── AGENTS.md, CLAUDE.md              the project's own: rules for agents
└── docs/
    ├── ARCHITECTURE.md, CONVENTION.md, CONTEXT.md    the project's own
    ├── <user-facing docs>.md         the project's own: usage, install
    └── process/                      made while working with an agent; committed or not, as the user decided
<store>/                              the person's own backup; name and place are theirs to choose; absent without one
├── README.md                         what this store is (written when it is created)
├── projects.json                     the registry: group rules and one entry per project (next to config.json without a store)
└── projects/<project>/               a copy of that project's docs/process/ (what is not committed), made by docs.mjs backup
```

Upgrading the skill replaces only the first block; a person's config, registry, store and documents stay untouched.

## The project's own documents

| File | What it is | Skeleton |
| --- | --- | --- |
| `AGENTS.md` | Rules for agents, read in every session; short. Ends with the "where documents are" section | `project/AGENTS.md` |
| `CLAUDE.md` | Only the line `@AGENTS.md`, so Claude Code reads the same rules; Claude-only additions may follow it | `project/CLAUDE.md` |
| `docs/ARCHITECTURE.md` | Code map: the parts, their boundaries, how data moves. Short; changes rarely | `project/ARCHITECTURE.md` |
| `docs/CONVENTION.md` | Coding conventions. Past about 200 lines: `docs/conventions/` with a `README.md` index and one file per topic | `project/CONVENTION.md`, `project/conventions-README.md` |
| `docs/CONTEXT.md` | Optional: business terms and what they mean | `project/CONTEXT.md` |
| `README.md`, user-facing `docs/<topic>.md`, `CHANGELOG.md` | For people who use the project | — |

- Skeletons have headings only; the agent translates them and leaves the sections empty. An existing file is never
  overwritten.
- The "where documents are" section of `AGENTS.md` sits between `<!-- rein-managing-project-docs:docs-map -->` and
  `<!-- /rein-managing-project-docs:docs-map -->`: one line per document that exists, plus `docs/process/` with a note
  that it may be ignored by git. It is the only part of these documents this skill writes; it holds no rules.
- `check` reports what it can see: `CLAUDE.md` that does not import `AGENTS.md` (`own-docs`); the same documents under
  other names or places (`own-docs-name`: a root `ARCHITECTURE.md`, a `docs/conventions.md`); conventions past 200
  lines (`long-rules`); a "where documents are" section missing, incomplete or pointing at files that are gone
  (`docs-map`). All are warnings: renaming, moving rules out of `CLAUDE.md` and splitting the conventions wait for
  the user's yes.
- Re-runnable tests (unit tests, fixtures) belong to the code, in the project's own test folder.

## What goes in docs/process/

| Type | When to create | Name | What it says | When to clean up |
| --- | --- | --- | --- | --- |
| Work folders | A plan comes before the work, the work spans sessions, a test record should be kept, or one piece of work needs scripts, data or mockups | `work/YYYY-MM-DD-<short-name>/` | See "Inside a work folder" | When done: keep what matters, then move the whole folder to `work/archive/` |
| Decision records | A choice someone will later ask "why" about, with options that were turned down | `decisions/YYYY-MM-DD-<short-name>.md` | Context, decision, options turned down and why, consequences | Never deleted; when overturned, a new one, and the old one says at its top which replaced it |
| Notes | Research or ideas not yet decided, worth keeping | `notes/YYYY-MM-DD-<short-name>.md` or `.html` | What was found, how sure, sources, open questions | Delete when no longer useful; notes are not a basis for anything |
| Explainers | A page that explains to the user how something works (a mechanism, a flow), kept and updated as it changes | `explain/<topic>.html` or `.md`, no date | How it works now | Edit in place when it changes; delete when the thing is gone |
| Requirements | A product requirement document analyzed by the requirements skill (rein-analyzing-requirements) | `requirements/`, only when the user put that skill's folder here | That skill's own files | That skill's way; this skill does not check inside |

Outside `docs/process/` and the project's own documents: drafts, trial output and screenshots tools save on their own
go in `.scratch/` in the project, ignored on this computer; delete when done.

An explainer is written for the user. A document that tells agents how to work in the project (a code map, coding
conventions) is the project's own, even when an agent wrote it.

**Do not write what is not needed:** a change that one sentence explains belongs in the commit message. Without an
option that was turned down, it is not a decision.

### Inside a work folder

```text
docs/process/work/2026-11-22-export-csv/
├── plan.md        the plan: what it achieves, how, what the user must decide
├── test.md        the test record (test.html from the template when a page reads better)
├── scripts/       throwaway scripts, any language (run from the project root; paths relative to it)
├── data/          test data, SQL
├── mockups/       page drafts
└── evidence/      screenshots, logs. Large raw logs go in evidence/raw/, which is never backed up or committed
```

These are the usual names, so that every project looks the same; use them when the thing exists, and name anything
else freely. Not every part is needed: checking one question needs only `test.md`; a plan alone needs only `plan.md`.
Work that touches several projects (say, a shared library) lives in the project where it started, with one line per
project in the plan.

A throwaway script that must sit inside the project's code to run (because it imports project code) lives in
`.scratch/` while working; afterwards copy what is worth keeping into `scripts/` and say in `test.md` how to run it.
Anything worth running again becomes a real test in the project's test folder.

### Plans and requirement documents

Work that starts from a product requirement document belongs to the requirements skill: its pages (the brief with the
questions to answer, the backend plan with owners and status, the SQL, the release checklist, the frontend guide) are
that work's plan. Its folder is the user's choice; when they have none, `docs/process/requirements/`, so that it follows
the project's switch and the backup. Other work gets a `plan.md` in its work folder; questions for the user go in it
and are answered in the conversation.

### Pages in HTML

Markdown is the default. An explainer, a test record or research may be a web page when it needs a picture, a filter
or a layout; plans and decision records stay Markdown; mockups follow the product they draft.

| Page | Template |
| --- | --- |
| How something works | `assets/templates/explain.html` |
| What was tested, the verdict, the evidence | `assets/templates/test.html` |
| A question, what was found, how sure each finding is | `assets/templates/note.html` |

- Copy the template; set the language, the title and every word a reader sees in the user's language (the `ui-text`
  block too); keep the parts that fit and delete the rest.
- Keep its styles and script. They share the look of the requirement pages: a contents rail, a search bar, a cover with
  one sentence, a facts table and three cards. Colours carry meaning only: blue is the one accent (links, where you
  are); green passed or confirmed; amber needs attention; red failed; purple inferred.
- One file, nothing loaded from the network: the page opens the same offline and years from now.

## Names and status

- File and folder names: lowercase English words joined by hyphens. Titles and text: in the user's language. The
  project's own documents keep their fixed names (`AGENTS.md`, `docs/ARCHITECTURE.md` …).
- Dated types (work folders, decisions, notes): `YYYY-MM-DD-<short-name>`, the date it was created, then any
  extension. **No sequence numbers**: two sessions creating one at the same time would collide.
- Undated (explainers): one per topic, edited in place. No `-v2`, `-final`, `-new`.
- No status block is required at the top of any file (an HTML page or a script has nowhere to put one). Where a
  thing is says its state:

| Where | Means |
| --- | --- |
| `work/<folder>/` | Ongoing. Still there after 30 days (by the date in its name): `check` reminds |
| `work/archive/<folder>/` | Done, or dropped (the plan says why in one sentence) |
| `decisions/<file>` | In force, unless its first line says which decision replaced it |

Markdown files may still start with front matter (`title`, `date`); nothing requires or checks it.

## How a project's switch is decided

**The user decides, per project or per group of projects; the agent follows and never picks a default.**

`docs.mjs where` looks it up in this order and says which one applied:

1. **The project's own registry entry** (`commit`, or `skip`).
2. **The first group rule that matches** (`groups`, in order): by the start of the project's remote URL, or by the
   folder it sits in.
3. **`defaults.commit`**, if the user ever wrote one.
4. **Nothing**: not decided.

What the agent does with each:

- **Decided by the entry or a rule**: a project matched by a rule but not registered yet is registered with
  `docs.mjs init` (no question) before its first document. On a computer where `docs/process/` is not ignored yet,
  `init` again (no question).
- **Not managed** (`skip`): the project has its own rules for documents (a research repository, a notes vault). The
  agent follows those and asks nothing; `check` skips it.
- **Not decided**: if the user's words already settle it, the agent records that without asking; otherwise it asks
  once. Until the user answers it writes no documents in `docs/process/`; a draft goes in `.scratch/`.

| The user says | Switch | Fits | Cost |
| --- | --- | --- | --- |
| "Keep docs with the code", "it's my private project" | `--commit` | Private projects, or teams that review documents in pull requests | Going public later means taking `docs/process/` out and cleaning history |
| "It will be open source", "it may go public", "keep these out of the repo" | `--no-commit` | Projects that are or may become public | Documents do not follow branches; only the backup keeps their history |
| "This is the company's (someone else's) repository, add no files" | `--no-commit` | Repositories that are not the user's to add files to | Same |

More rules:

- **Group rules are added only when the user says so** ("all company repositories the same way", "everything under
  this folder keeps its own rules"). The agent does not infer groups. Remote rules work on every computer; folder
  rules only where that folder exists.
- **One document with its own wish** in a project that commits `docs/process/`: "keep this one out" — add that file to
  `.git/info/exclude`. The backup takes it (it backs up whatever git ignores under `docs/process/`).
- **Sensitive content**: the project commits `docs/process/`, but this document holds accounts, internal addresses,
  customer names, costs or unfixed security weaknesses: ask the user before writing it there.
- **A project whose `docs/` is ignored as a whole** (the user's own rule, common in company repositories): `docs/process/`
  is ignored with it, and the switch is `--no-commit`.
- **Changing the switch**: see skill section 4 and `checklist.md`.

### The registry

`projects.json`: at the store's root when there is a store (it travels to other computers with it), next to the config
file otherwise. `init` and `group` change it and commit the change in the store; editing by hand also works.

```json
{
  "version": 2,
  "groups": [
    { "remote": "git.example.com/team", "commit": false, "note": "company repositories" },
    { "folder": "D:/code/oss", "commit": false },
    { "folder": "D:/code/tools", "commit": true },
    { "folder": "D:/code/research-notes", "skip": true }
  ],
  "projects": {
    "todo-cli": {
      "match": ["github.com/someone/todo-cli"],
      "commit": false,
      "allow": ["SPEC.md"],
      "tools": [],
      "added": "2026-11-22"
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| project name (`todo-cli`) | Its folder name in the store; by default the project folder's name |
| `match` | How the project is recognized: remote URLs (no protocol, no `.git`), or the folder name when there is no remote. Where the project sits on each computer is in `local.json`, not here |
| `commit` | The switch: `true` commits `docs/process/`; `false` keeps it out (ignored on each computer, backed up). **Missing means not decided** (unless a group rule or `defaults` applies) |
| `skip` | `true`: this project keeps its own rules; agents ask nothing and the check skips it |
| `allow` | Files at the project root or the top of `docs/` let through on purpose, though named like working documents or like the project's own documents (paths relative to the project root; `init --allow a,b` adds them): files the project's own rules use, such as a spec-driven workflow's `SPEC.md` and `TASKS.md` |
| `tools` | Tools with their own document home found at registration; only a record, the check looks at what exists now |
| `groups` | Optional. Rules for groups of projects, first match wins: `remote` (start of the remote URL) or `folder` (projects inside it), with `commit` (`true`/`false`) or `skip`. `note` is for people |
| `defaults.commit` | Optional, **absent in a new registry**. Only when the user said "all my projects this way": projects matched by nothing else follow it |
| `legacy_in_repo` | Left by version 0.1 when a project split its types between repository and store. It decides nothing; the project needs a new decision |

A registry from version 0.1 (`in_repo` per type) is read as version 2: all four types in the repository → `commit:
true`; all in the store → `commit: false`; a mix → not decided. It is written as version 2 the next time it changes.

## Backup and restore

Only for documents that are not committed (a whole `docs/process/` that is ignored, or single files kept out by hand).
The project's own documents are never backed up.

- **`docs.mjs backup`**: makes `<store>/projects/<project>/` the same as what git ignores under `docs/process/`: new,
  changed, removed and renamed files alike, then commits in the store. It never pushes; the user pushes the store
  when they like. Left out: `evidence/raw/`, hidden files (a `.env` stays on this computer), files over 20 MB.
  `--all` backs up every project listed for this computer in `local.json`.
- **When**: the agent runs it after writing or changing documents in such a project. The user can ask any time
  ("back up the docs"). `where` and `check` say how many changes are not backed up; `check --store` lists every
  project with changes not backed up.
- **It stops instead of overwriting** when the store's copy changed since this computer's last backup (another
  computer's backup, pulled into the store), when the store's copy has uncommitted edits, when this computer never
  backed up or restored a store copy that differs, or when `docs/process/` is empty but the store's copy is not.
  `--force` overwrites, only when the user says so; the old copy stays in the store's history.
- **`docs.mjs restore`**: brings the store's copy into `docs/process/`: on a new computer, after a wiped folder, or
  after another computer's backup was pulled into the store. A file changed only in the store is copied; one changed
  only here is kept (the next backup takes it); one changed on both sides since the last backup is left alone and
  listed for the user to decide.
- **Never edit the store's copy.** Change the project's `docs/process/` and back up.

## When a document is out of date

| Situation | What to do |
| --- | --- |
| A piece of work is done | Keep what matters first: decisions become decision records; an explainer that changed is updated; tests worth re-running become real tests; if how the project works changed, tell the user its own architecture or conventions may need an update. Then move the whole folder into `work/archive/`, delete `evidence/raw/` |
| A piece of work is abandoned | One sentence in its plan on why, then move it into `work/archive/` |
| A decision is overturned | Write a new decision record; the old one stays, with a first line saying which one replaced it |
| An explainer no longer matches | Edit it in place until it matches. No new file |
| A note is no longer useful | Delete it |
| The project's own documents no longer match | The project's business; the agent may point it out, and updates the "where documents are" section when files are added or renamed |
| A whole project is dropped | Leave its documents and its backup as they are; add `"archived": true` to its registry entry |

Agents do not read `work/archive/` unless the user mentions it.

## Projects that use a tool with its own document home

Some tools manage a piece of work's requirements, specs, tasks and acceptance themselves (rein's `.rein/`, OpenSpec's
`openspec/`, Spec Kit's `.specify/`, Kiro's `.kiro/`); some ticket tools keep a work-item folder per bug or requirement.
One rule: **what the tool has commands for belongs to the tool; everything else follows these conventions.**

| Document | Belongs to | Where |
| --- | --- | --- |
| Requirement specs, tasks, acceptance, ticket material | That tool | The tool's own place, written with its commands; never edited or moved by hand |
| Decision records, explainers, notes | These conventions | `docs/process/` |
| Process material the tool does not take (throwaway test data and scripts, raw benchmark data, research) | These conventions | `docs/process/work/YYYY-MM-DD-<short-name>/`, with no separate plan |

The check skips these tools' folders (`.rein/`, `.kiro/`, `.specify/`, `openspec/` by default; add more with `toolDirs`
in the config file), and `docs/process/requirements/`. Tool folders usually sit in the repository, so when the project
goes public, so do the specs in them. Content others should not see does not go in a spec.

## The tool

Everything is in the skill's `scripts/docs.mjs`, Node 18 or newer, no dependencies. `docs.mjs` below means
`node <skill folder>/scripts/docs.mjs`.

| Command | What it does |
| --- | --- |
| `docs.mjs setup [--store <path> \| --no-store]` | Once per computer: record where the store is (creating it at the given path, or connecting to an existing one) and install the global rule for Claude Code and Codex. Previews by default; `--apply` writes |
| `docs.mjs init [--commit \| --no-commit]` (in a project) | Register a project and set it up on this computer: record the switch (without a flag, the one a group rule gives), ignore `docs/process/` (when not committed) and `.scratch/` locally, create `docs/process/`, record where the project sits, install a pre-commit check. `--skip` marks it as not managed |
| `docs.mjs where` | This project's name, its switch and who decided it, the folder to write in, the project's own documents found, backup state |
| `docs.mjs check` | Check this project: names and places in `docs/process/`, the project's own documents, `docs/process/` committed or ignored as decided, working documents left at the root, changes not backed up |
| `docs.mjs check --store` | Check the store: uncommitted or unpushed, projects with changes not backed up |
| `docs.mjs backup [--all]` | Copy what is not committed of `docs/process/` into the store and commit there; `--dry-run` previews, `--force` overwrites when it stops |
| `docs.mjs restore` | Bring the store's copy into `docs/process/`; `--dry-run` previews |
| `docs.mjs group list \| add \| remove` | Group rules: `add --remote <prefix>` or `--folder <path>`, with `--commit`, `--no-commit` or `--skip` |

## Moving to another computer

1. Install the skill `rein-managing-project-docs`.
2. With a store: clone it anywhere and tell the agent "connect this computer to my store at <path>" (it runs
   `setup --store <path>`, which recognizes an existing store). Without one: "set up my project documents".
3. Add the store to Claude Code's and Codex's settings as the last lines of `setup` say.
4. In each project that does not commit `docs/process/`: `docs.mjs init` (no question; the registry already has the
   switch), then `docs.mjs restore`.
5. Folder group rules match only where those folders exist; add rules for this computer's layout if it differs.

## What never goes in docs/process/ or the store

- Passwords, tokens, private keys. A `.env` a script needs stays a hidden file (never backed up) or in `.scratch/`.
- Data the company does not allow out (query results, server logs, customer information): keep it where the company
  allows. Such a project's folder can go in the store's `.gitignore` so it stays on this computer and is never pushed.

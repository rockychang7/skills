---
name: rein-managing-project-docs
description: "Keeps every project's documents under docs/, named the same way everywhere: the project's own (AGENTS.md, CLAUDE.md, architecture, conventions), placed and named but not written; and what is made while working with an agent (plans, tests, scripts, mockups, explainers, decisions, notes; any format) in docs/process/. The user decides per project or group whether docs/process/ is committed; if not, a private store backs it up. Handles setup, registering projects, group rules, the switch, adding a project's own documents, HTML pages from templates, backup and restore, wrapping up, tidying. Use when the user wants project documents set up or organized, just installed this skill, moved computers, or `docs.mjs where` says not set up or not decided; also when the user says docs should or should not be committed, asks to back up or restore docs, add AGENTS.md or an architecture doc, says work is finished or docs are a mess. Not for placing one new document (the global rule does) or analyzing a requirement document."
license: MIT
compatibility: "Requires Node.js 18+ (no dependencies) to run scripts/docs.mjs. The global rule is installed for Claude Code and Codex."
metadata:
  author: rockychang7
  version: "0.2.0"
---

# Managing Project Documents

Every project keeps its documents under `docs/`, in two parts:

- **The project's own documents**: `AGENTS.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/CONVENTION.md`, optionally
  `docs/CONTEXT.md`. This skill fixes their names and places; what they say is the project's business; they are not
  backed up; whether they are committed is the project's business.
- **What is made while working with an agent**, in `docs/process/`: plans, test records, throwaway scripts and data,
  mockups, screenshots, explainer pages, decision records, research. Any format. Whether a project commits
  `docs/process/` is the user's decision, per project or per group of projects. When it does not, git ignores it on
  this computer and `docs.mjs backup` copies it into a private store outside every project.

The global rule installed by `setup` covers everyday writing ("this document goes here, named like this"). This skill
covers the multi-step work around it. It works the same whether or not a project uses rein.

Talk to the user in the language they write in, from the first question on; this file being in English is no reason
to switch.

The full conventions are in `references/conventions.md`; what to check by hand when changing a project's switch is in
`references/checklist.md`; templates are in `assets/templates/`.

Three rules hold throughout:

- **Whether a project commits `docs/process/` is the user's decision.** Ask when they have not said. Never pick a
  default, and never talk them into having a store.
- **The project's own documents keep their content.** This skill names and places them, adds empty skeletons when
  asked, and keeps the "where documents are" section of `AGENTS.md`; it never writes, rewrites or deletes their rules,
  never moves them into `docs/process/` or the store, and never adds a line pointing at the store.
- **Nothing of any one person goes into this skill's files.** The store's name and place, group rules and each
  project's switch go into that person's config file and registry.

## Done when

- `docs.mjs check` shows no ✗ (tell the user about each `!`; do not act on them unasked).
- In a project that does not commit `docs/process/`: `docs.mjs backup` ran after the last change. It commits in the
  store and never pushes; the user pushes. If it cannot commit (some tools may not change `.git/`), do not work around
  it: tell the user which step did not happen and the command it printed.
- The reply says which files were created, moved or deleted, and where they are now.

## Running the script

`docs.mjs` below stands for `node <this skill's folder>/scripts/docs.mjs`, run from inside the project unless said
otherwise. Start every task with `docs.mjs where`. Commands that change a person's machine preview first: `setup`
writes only with `--apply`; `init`, `backup` and `restore` take `--dry-run`.

## Which situation

| Situation | What to do |
| --- | --- |
| "Set up my project documents", the skill was just installed, or `where` says this computer is not set up | [1. Set up this computer](#1-set-up-this-computer) |
| A new computer: "connect to my store at …" | Section 1, step 3, then [9](#9-back-up-and-restore) for each project |
| `where` says the project is not decided; or "new project"; or the user says whether this project's documents are committed | [2. Register a project](#2-register-a-project) |
| `where` says the switch comes from a group rule and the project is not registered, or `docs/process/` is not ignored on this computer yet | `docs.mjs init` (no flag, no question), then go on with the work |
| `where` says the project is not managed | Follow the project's own rule files for documents; do nothing here |
| "All company repositories the same way", "everything under this folder keeps its own rules" | [3. Group rules](#3-group-rules) |
| "From now on commit the docs", "keep the docs out of the repo", "keep this one out" | [4. Change the switch](#4-change-the-switch) |
| "This is done, wrap it up" | [5. Wrap up finished work](#5-wrap-up-finished-work) |
| "The docs are a mess", documents from version 0.1 (`docs/work/`, the store as the main copy), an old repository of documents to bring in | [6. Tidy up scattered documents](#6-tidy-up-scattered-documents) |
| "Add AGENTS.md / an architecture doc", a new project needs its own documents, `check` reports `own-docs`, `docs-map` or `long-rules` | [7. The project's own documents](#7-the-projects-own-documents) |
| An explainer, a test record or research written as a web page | [8. Pages in HTML](#8-pages-in-html) |
| "Back up the docs", "bring the docs back", `backup` stopped, a second computer | [9. Back up and restore](#9-back-up-and-restore) |
| A product requirement document to analyze | Not this skill: the requirements skill (rein-analyzing-requirements). Its folder: when it asks, offer `docs/process/requirements/` and let the user choose; use it only when they do not say. This skill does not check inside it |

## 1. Set up this computer

1. **Listen first, then look.** Note what the user said; then see where their projects live, how their repositories
   are named, and whether there is an old repository they used for documents.
2. **Backup store or not.** It is needed only for projects that will not commit `docs/process/`, and only if the user
   wants those documents backed up:
   - The user's words call for one ("some docs must not go in the repo, but I don't want to lose them"): yes.
   - They clearly do not ("docs always stay with the code"; "losing uncommitted docs is fine"): no store;
     `docs.mjs setup --no-store`. Come back here when they want a backup.
   - Unclear: ask once, saying what the store is (one private git repository outside every project that keeps a
     copy, with history, of each project's uncommitted documents; projects keep no trace of it), and let them choose.
3. **A store already exists** (new computer, or "my store is at X"): `docs.mjs setup --store <path>` to preview. If it
   says the folder is not a store (no registry at its root; usually an old documents repository the user made), do
   not force it: ask whether to create a new store and bring the old one in (section 6), or use another place.
4. **A new store: name and place as the user says.** If they have not said, offer two or three candidates and why:
   - Place: alongside the user's projects but inside none of them and inside no git repository (the script refuses that).
   - Name: lowercase English words with hyphens that say what it is; follows the user's existing naming habits; does
     not clash with folders or repositories already on this computer, or with words their tools already use for
     something else (for an Obsidian user, "vault" means their notes).
   - Remote: must be private; which account is the user's choice.
5. **Preview, then apply.** `docs.mjs setup --store <path>` (or `--no-store`); show its steps to the user as they are;
   after a yes, run it again with `--apply`. It creates or connects the store, writes the config file and installs the
   global rule for Claude Code and Codex. Nothing else.
6. **Permissions** (with a store): add the store's path to Claude Code's `~/.claude/settings.json`
   (`permissions.additionalDirectories`) and Codex's `~/.codex/config.toml` (`writable_roots` under
   `[sandbox_workspace_write]`). These are global settings: ask first, change only after a yes, use forward slashes
   on Windows. Without them an agent in a sandbox may not be allowed to run `docs.mjs backup`.
7. **Optional, only after asking:** add `.scratch/` to the user's global git ignore file (it then applies to every
   repository without touching any project).
8. Tell the user: the rule takes effect in new sessions; they push a new store to its remote themselves.

## 2. Register a project

When: the user starts a new project; `where` says this project is not decided; or the user changes its switch.

1. In the project root, `docs.mjs init --dry-run` to see what it would do.
2. If the user's words already settle it, use them and do not ask again:

   | The user says | Switch |
   | --- | --- |
   | "It will be open source", "it may go public", "keep the docs out of the repo" | `--no-commit` |
   | "This is the company's (someone else's) repository, add no files" | `--no-commit` |
   | "Keep docs with the code", "it's my private project, no need to split" | `--commit` |
   | "This project has its own rules for docs" | `--skip` |

   When unsure whether they meant it, treat it as not said.
3. Not settled: ask one question: commit `docs/process/` with the code, or keep it out of the repository (ignored on
   this computer, backed up to the store)? You may say what you see (the remote is public; it is a company
   repository), but do not choose for them and do not call either the default. No answer: stop; do not register and
   do not write documents there.
4. `--no-commit` and this computer has no store: say that these documents will have no backup, and ask whether to
   create a store (section 1). Their choice either way.
5. `docs.mjs init --commit` or `--no-commit`; in one sentence tell the user what it now is.
   - It says the registry already has a project with that name: ask for another name and add `--id <name>`.
   - It says the pre-commit check was not installed (the project has its own hooks): pass its line on to the user as
     it is; do not change the project's hooks yourself.
   - It says the store holds a backup of this project: `docs.mjs restore` (section 9).
6. The project uses a tool with its own document home (`where` lists `.rein/`, `openspec/` and the like): tell the
   user that requirements, specs, tasks and acceptance belong to that tool and the rest to `docs/`.
7. The project already has scattered documents (plans under `docs/`, a `PLAN.md` at the root), its own documents
   under other names, or `where` reports an old layout: run `docs.mjs check`, show the user the result and ask whether
   to tidy up; tidy only after a yes (section 6).

Never decide the switch for the user.

## 3. Group rules

When the user describes a whole group ("all company repositories", "everything under this folder", "these research
repositories have their own rules"), write one rule instead of registering each project:

- `docs.mjs group add --remote <start of the remote URL> --no-commit` — by remote, works on every computer. Take the
  prefix from a real remote of that group (`git remote get-url origin`), cut at the host or organization the user means.
- `docs.mjs group add --folder <folder> --commit` — by the folder the projects sit in; only on this computer.
- `--skip` instead marks the group as not managed.
- `docs.mjs group list` shows the rules in order (the first match wins; a project's own entry beats every rule);
  `docs.mjs group remove <number>` removes one.

Add rules only from what the user said; never infer a group from what you see. After adding, run `where` in one
project of the group and tell the user what it now says. A company's remote host goes in the user's registry only,
never into this skill's files.

## 4. Change the switch

Follow `references/checklist.md`; the outline:

- **Not committed → committed**: read every file under `docs/process/` first, looking for accounts and passwords,
  internal addresses and machine names, names of customers and colleagues, prices and costs, unfixed security
  weaknesses, opinions about people. Any of them: stop, show the user those lines, and ask whether to delete, rewrite
  or keep that file out. Then `docs.mjs init --commit` and commit.
- **Committed → not committed**: `docs.mjs init --no-commit`, `git rm -r --cached docs/process/` (files stay on disk),
  commit, `docs.mjs backup`. Then **tell the user plainly**: the files are no longer in the repository, but history
  still has them (`git log --oneline -- docs/process/`). Never pushed anywhere others can see: history can be cleaned;
  ask whether to. Already pushed where others can see: treat it as leaked; passwords or tokens in it get changed
  first; cleaning history rewrites commits, needs a force push, and cannot reach clones and forks. Let them decide;
  do not clean history yourself.
- **One file out of a committed `docs/process/`** ("keep this one out"): add its path to `.git/info/exclude` (and
  `git rm --cached` it if it was committed, with the same warning about history); `docs.mjs backup` takes it from then on.

The switch is about `docs/process/` only. Whether the project's own documents are committed is the project's business
(for a company repository the user may ignore them locally); this skill does not change it.

When the user named one specific file, do it. When they named "these" or "the related ones", show the list of files
first and act only after a yes.

## 5. Wrap up finished work

The target is `docs/process/work/<date>-<short-name>/`.

0. **Check it is really done.** Look for what the plan says was built (code, tests, docs). If something marked done
   cannot be found, stop: tell the user what is missing and ask before archiving anything.
1. **Keep what matters** (ask about each item, "keep this?", and write only after a yes):
   - What the plan settled that someone will ask "why" about later: a `docs/process/decisions/YYYY-MM-DD-<short-name>.md`.
   - An explainer page that should outlive the work: move or copy it to `docs/process/explain/<topic>.<ext>`; update an
     existing one in place.
   - Test scripts worth running again: turn them into real tests in the project's own test folder.
   - How the project works changed: tell the user `docs/ARCHITECTURE.md` or the conventions may need an update. They
     are the project's; change them only if the user asks.
2. Abandoned work: one sentence at the top of its plan on why.
3. Delete `evidence/raw/` and this work's leftovers in the project's `.scratch/`; keep only the screenshots and logs
   that back the conclusion.
4. Move the whole folder into `docs/process/work/archive/`. No status to change: the place says it.
5. `docs.mjs check`; `docs.mjs backup` when the project does not commit `docs/process/`.

In a project that uses a tool with its own document home: wrap up the requirement the tool's way; here, archive only
the material the tool does not take.

## 6. Tidy up scattered documents

In one project, documents from version 0.1 of this skill, or an old repository of documents the user made before.

1. `docs.mjs check` and work through what it lists. An old documents repository: first work out which project each
   folder belongs to; register unregistered projects by section 2.
2. For every item, say where it would go and what it would be called; put it all in one table for the user and act
   only after a yes.
3. **The project's own documents under other names** (`check` says `own-docs-name`: an `ARCHITECTURE.md` at the root,
   a `docs/conventions.md`): the table proposes the fixed name and lists every line that points at the old one
   (`AGENTS.md`, `CLAUDE.md`, README); after a yes, rename and fix those lines, nothing else. Files the project's own
   rule files use under a name of their own (a spec-driven workflow's `SPEC.md` and `TASKS.md`) stay as they are:
   add their paths to `allow` (`docs.mjs init --allow <path>`) so the checks let them through.
4. Cannot tell the type (one file mixes a plan and a decision): put the whole file in `docs/process/notes/`; do not
   split it.
5. Documents leaving the repository that were committed stay in history: tell the user as in section 4.
6. The repository has the user's uncommitted or staged changes: do not move tracked files there (your renames would
   end up in their next commit). List what would move and leave it for when their work is committed.
7. Whether to delete or archive an emptied old repository is the user's call.

**From version 0.1.** The registry is converted when read (four types in the repository → `--commit`; all in the
store → `--no-commit`; a mix → not decided, ask). The documents move by hand, with the table of step 2:

- `docs/work/`, `docs/decisions/`, `docs/notes/` in the repository → `docs/process/` (same names). `docs/internals/`:
  a page explaining something to the user → `docs/process/explain/`; a code map or conventions for agents → the
  project's own (`docs/ARCHITECTURE.md`, `docs/CONVENTION.md`).
- The store's `projects/<project>/{work,decisions,notes}` → the project's `docs/process/`. `internals/` there: same
  split as above; agent-facing ones go back to the project's own places, and the rule files point there again.
- Then `docs.mjs init` and `docs.mjs backup --force` once (the store's copy becomes the copy of `docs/process/`; the
  old layout stays in its history).

## 7. The project's own documents

Names and places are fixed; content is the project's. Skeletons are in `assets/templates/project/`.

| File | What it is |
| --- | --- |
| `AGENTS.md` | Rules for agents, read in every session: keep it short. Ends with a "where documents are" section |
| `CLAUDE.md` | Only the line `@AGENTS.md` (Claude Code reads this file; the import makes it read `AGENTS.md`). Claude-only additions may follow it |
| `docs/ARCHITECTURE.md` | Code map: the parts, their boundaries, how data moves. Short; changes rarely |
| `docs/CONVENTION.md` | Coding conventions. Past about 200 lines: `docs/conventions/`, with `README.md` as the index (one line per file: what it covers, when to read it) and one file per topic |
| `docs/CONTEXT.md` | Optional: business terms and what they mean |

- **Adding them** ("add AGENTS.md and an architecture doc", or a new project): copy the skeletons the user asked for,
  translate the headings into their language, and leave the sections empty. `CLAUDE.md` is created as `@AGENTS.md`.
  An existing file is never overwritten; tell the user it is there.
- **The "where documents are" section** in `AGENTS.md`, between `<!-- rein-managing-project-docs:docs-map -->` and
  `<!-- /rein-managing-project-docs:docs-map -->`, is the one part this skill writes: one line per document that
  exists (path and what it is, in the user's language), plus `docs/process/` with a note that it may be ignored by
  git. Keep it in step when documents are added, renamed or split (`check` says `docs-map`). No rules in it.
- **`CLAUDE.md` with rules of its own** (`check` says `own-docs`): ask, then move them into `AGENTS.md` as they are and
  leave `CLAUDE.md` as `@AGENTS.md`.
- **Splitting the conventions** (`check` says `long-rules`): ask first; then move sections into topic files under
  `docs/conventions/` without rewording them, write the index, and point `AGENTS.md` at the index.
- **Committed or not** is the project's business. In a repository that is not the user's to add files to, they may keep
  these files ignored locally; do not change that. They are not backed up.

## 8. Pages in HTML

Markdown is the default. An explainer, a test record or research may be a web page when it needs a picture, a filter,
or reads better laid out. Plans and decision records stay Markdown. Page drafts of a product (mockups) follow the
product, not these templates.

| Page | Template | Goes to |
| --- | --- | --- |
| How something works | `assets/templates/explain.html` | `docs/process/explain/<topic>.html` |
| What was tested, the verdict, the evidence | `assets/templates/test.html` | `docs/process/work/<date>-<short-name>/test.html` |
| A question, what was found, how sure each finding is | `assets/templates/note.html` | `docs/process/notes/<date>-<short-name>.html` |

1. Copy the template. Set `<html lang>`, the title and every word a reader sees in the user's language, the `ui-text`
   block included.
2. Keep the parts that fit, delete the rest; each part has a comment saying what it is for. Write real content; the
   facts table on the cover says what the page is based on (files, version, date), so a reader can tell whether it is
   still true.
3. Keep both style blocks and the script as they are. Styles for this page only go at the end of the second style
   block. Colours carry meaning only: blue is the one accent (links, where you are); green passed or confirmed; amber
   needs attention; red failed; purple inferred. The look matches the requirement pages on purpose.
4. One file, nothing loaded from the network. Pictures are inline SVG with the template's classes, so both themes
   stay readable.

## 9. Back up and restore

The project's `docs/process/` is the original; the store holds a copy. Copying goes one way, from the project to the
store.

- **Back up**: `docs.mjs backup` (one project) or `docs.mjs backup --all` (every project listed for this computer). It
  commits in the store and never pushes; say so, and leave pushing to the user.
- **New computer or wiped folder**: `docs.mjs init` (no question), then `docs.mjs restore`.
- **`backup` stopped**: it says why; do what it says, and never use `--force` unless the user said to overwrite.
  - The store's copy changed since this computer's last backup (another computer's backup was pulled in): run
    `docs.mjs restore`, then `backup`.
  - `restore` lists files changed on both sides: show the user both versions (the store's is under
    `<store>/projects/<project>/`); put the content they choose in `docs/process/`; then `docs.mjs backup --force`.
  - The store's copy has uncommitted changes (someone edited it by hand): show the user; they decide which side wins.
- **Pulling and pushing the store** between computers is the user's: `git pull` / `git push` in the store. Suggest it
  when they switch computers; do not run it unasked.

## When to stop and ask

- Before creating a store (whether, its name, its place); before changing global settings.
- Before anything that makes content public (committing documents that were not committed).
- Before renaming, moving or splitting the project's own documents, or moving rules out of `CLAUDE.md`.
- History rewriting, force pushes, changing a repository's visibility, pushing the store: give the steps; do not do them.
- `docs.mjs` fails, cannot find the store, or `backup` stops: do not make do another way; tell the user which command
  said what.

## Pitfalls

| Situation | What to do |
| --- | --- |
| Tempted to put the plan in `PLAN.md` at the root or `docs/design.md` "for now" | Run `where`; until the switch is decided, drafts go in `.scratch/` |
| Moving `docs/ARCHITECTURE.md` or the coding conventions into `docs/process/` or the store because they look like documents | Never; they are the project's own |
| Writing or improving the rules in `AGENTS.md` or the conventions while placing them | Not this skill's job: headings and the "where documents are" section only |
| A requirement document to analyze | The requirements skill; ask where its folder goes, `docs/process/requirements/` only when the user does not say |
| Thinking only of Markdown | Any format goes in `docs/process/`: an HTML page, a SQL file, a Python script, screenshots |
| Writing an HTML page from scratch, or restyling a template | Start from the template and keep its styles |
| Adding a status block to a page or a script | No status anywhere: `work/` is ongoing, `work/archive/` is done |
| Searching the whole project for a document and finding nothing | `docs/process/` may be ignored by git, and searches skip ignored folders; look there directly |
| Editing a document in the store | Never; edit the project's `docs/process/` and back up |
| `backup` stopped and `--force` would make it go | Only when the user says to overwrite the store's copy |
| The user said "remember this" or "write it down" | A file in `docs/process/`, not your own memory and not an online document |
| Seeing a public remote and choosing `--no-commit` for the user | Say what you see; the user chooses |
| Inferring a group rule from several similar projects | Ask; rules come from the user's words only |
| Writing into `.rein/`, `openspec/` or another tool's folder by hand | Use the tool's commands; if the tool cannot be used, tell the user |
| Talking to the user in English because this skill is in English | Talk in the user's language; write titles and text in documents in their language too |

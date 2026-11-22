---
name: rein-managing-project-docs
description: "Keeps every project's documents (internal docs, decision records, work folders with plans and test records, notes) in one agreed shape and place: the project repository or a private store outside all projects, as the user decides per project or per group. Handles the multi-step parts: setting up a computer (whether to have a store, its name and place), registering a project's arrangement, group rules, moving documents between repository and store, wrapping up finished work, tidying scattered documents. Use when the user wants project documents set up or organized, just installed this skill, moved to a new computer, or `docs.mjs where` says the computer is not set up, a project is not decided, or there is no store; also when the user says which documents stay in or out of a repository, that work is finished, or that docs are a mess, even when making a folder or moving a file looks enough. Not for deciding where one new document goes (the global rule covers it) or for writing a README."
license: MIT
compatibility: "Requires Node.js 18+ (no dependencies) to run scripts/docs.mjs. The global rule is installed for Claude Code and Codex."
metadata:
  author: rockychang7
  version: "0.1.0"
---

# Managing Project Documents

Every project gets the same kinds of documents with the same names; where four of those kinds live (the project
repository or a private store outside every project) is the user's decision, per project or per group of projects.
The global rule installed by `setup` covers everyday writing ("this document goes here, named like this"). This skill
covers the multi-step work around it. It works the same whether or not a project uses rein.

Talk to the user in the language they write in, from the first question on; this file being in English is no reason
to switch.

The full conventions are in `references/conventions.md`; what to check by hand when moving documents is in
`references/checklist.md`. Below, "public" means in the project repository and "private" means in the store.

Two rules hold throughout:

- **Where documents go is the user's decision.** Ask when they have not said. Never pick a default, and never talk
  them into having a store.
- **Nothing of any one person goes into this skill's files.** The store's name and place, group rules and each
  project's arrangement go into that person's config file and registry.

## Done when

- `docs.mjs check` shows no ✗ (tell the user about each `!`; do not act on them unasked).
- Changes inside the store are committed there (`git -C <store> add -A && git -C <store> commit -m "…"`), not pushed;
  the user pushes. If committing is not possible (some tools may not change `.git/`), do not work around it: tell the
  user which step did not happen and the command to run.
- The reply says which files were created, moved or deleted, and where they are now.

## Running the script

`docs.mjs` below stands for `node <this skill's folder>/scripts/docs.mjs`, run from inside the project unless said
otherwise. Start every task with `docs.mjs where`. Commands that change a person's machine (`setup`, `init`) preview
first: `setup` writes only with `--apply`; `init --dry-run` previews.

## Which situation

| Situation | What to do |
| --- | --- |
| "Set up my project documents", the skill was just installed, or `where` says this computer is not set up | [1. Set up this computer](#1-set-up-this-computer) |
| A new computer: "connect to my store at …" | Section 1, step 3 |
| `where` says the project is not decided; or "new project"; or the user says how this project's documents should go | [2. Register a project](#2-register-a-project) |
| `where` says the arrangement comes from a group rule and the project is not registered | `docs.mjs init` (no `--in-repo`, no question), then go on with the work |
| `where` says the project is not managed | Follow the project's own rule files for documents; do nothing here |
| "All company repositories go to the store", "everything under this folder keeps its own rules" | [3. Group rules](#3-group-rules) |
| "This one goes in the repo", "keep these out of the repo", "from now on decisions go in the repo" | [4. Move documents](#4-move-documents) |
| "This is done, wrap it up" | [5. Wrap up finished work](#5-wrap-up-finished-work) |
| "The docs are a mess", an old repository of documents to bring in | [6. Tidy up scattered documents](#6-tidy-up-scattered-documents) |

## 1. Set up this computer

1. **Listen first, then look.** Note what the user said; then see where their projects live, how their repositories
   are named, and whether there is an old repository they used for documents.
2. **Store or not:**
   - The user's words call for one ("some docs must not go in the repo", "company repos cannot take files", "this
     will be open source"): yes.
   - They clearly do not ("docs always stay with the code"): no store; `docs.mjs setup --no-store`. Come back here when
     a project first needs the store.
   - Unclear: ask once, saying what a store is (one private repository for every document kept out of project
     repositories; projects keep no trace of it), and let them choose.
3. **A store already exists** (new computer, or "my store is at X"): `docs.mjs setup --store <path>` to preview. If it
   says the folder is not a store (no registry at its root; usually an old documents repository the user made), do
   not force it: ask whether to create a new store and bring the old one in (section 6), or use another place.
4. **A new store: name and place as the user says.** If they have not said, offer two or three candidates and why:
   - Place: alongside the user's projects but inside none of them and inside no git repository (the script refuses that).
   - Name: lowercase English words with hyphens that say what it is; follows the user's existing naming habits; does
     not clash with folders or repositories already on this computer, or with words their tools already use for
     something else (for an Obsidian user, "vault" means their notes; with an online docs tool, "docs" invites confusion).
   - Remote: must be private; which account is the user's choice.
5. **Preview, then apply.** `docs.mjs setup --store <path>` (or `--no-store`); show its steps to the user as they are;
   after a yes, run it again with `--apply`. It creates or connects the store, writes the config file and installs the
   global rule for Claude Code and Codex. Nothing else.
6. **Permissions** (with a store): add the store's path to Claude Code's `~/.claude/settings.json`
   (`permissions.additionalDirectories`) and Codex's `~/.codex/config.toml` (`writable_roots` under
   `[sandbox_workspace_write]`). These are global settings: ask first, change only after a yes, use forward slashes
   on Windows. Without them agents know a document belongs in the store but cannot read or write it.
7. **Optional, only after asking:** add `.scratch/` to the user's global git ignore file (it then applies to every
   repository without touching any project).
8. Tell the user: the rule takes effect in new sessions; they push a new store to its remote themselves.

## 2. Register a project

When: the user starts a new project; `where` says this project is not decided; or the user changes its arrangement.

1. In the project root, `docs.mjs init --dry-run` to see what it would do.
2. If the user's words already settle the arrangement, use them and do not ask again:

   | The user says | Arrangement |
   | --- | --- |
   | "It will be open source", "it may go public", "keep internal docs out of the repo" | `--in-repo none`; add any types they name as public, e.g. `--in-repo decisions` |
   | "Keep docs with the code", "it's my private project, no need to split" | `--in-repo all` |
   | "This is the company's (someone else's) repository, add no files" | `--in-repo none` |
   | They name some types for the repository | `--in-repo <those types>`, the rest in the store |
   | "This project has its own rules for docs" | `--skip` |

   When unsure whether they meant it, treat it as not said.
3. Not settled: ask one question. List the four types (internal docs, decision records, work folders, notes) and the
   common arrangements `where` prints. You may say what you see (the remote is public; there is already a
   `docs/decisions/`), but do not choose for them and do not call any choice the default. No answer: stop; do not
   register and do not write those types.
4. The arrangement needs the store and this computer has none: create it by section 1 (ask its name and place), then
   come back.
5. `docs.mjs init --in-repo <their choice>`; in one sentence tell the user what it now is: which types go in the
   repository, which in the store.
   - It says the registry already has a project with that name: ask for another name and add `--id <name>`.
   - It says the pre-commit check was not installed (the project has its own hooks): pass its line on to the user as
     it is; do not change the project's hooks yourself.
6. The project uses a tool with its own document home (`where` lists `.rein/`, `openspec/` and the like): tell the
   user that requirements, specs, tasks and acceptance belong to that tool and the other types to these conventions.
   Nothing else to do.
7. The project already has scattered documents (plans under `docs/`, a `PLAN.md` at the root): run `docs.mjs check`,
   show the user the result and ask whether to tidy up; tidy only after a yes (section 6).

Never: add any file to the project for this (not even a line in its `AGENTS.md` pointing at the store); decide the
arrangement for the user.

**Changing an arrangement** ("from now on this project's decisions go in the repo"): list that type's current files,
move them by section 4, then `docs.mjs init --in-repo <new arrangement>`.

## 3. Group rules

When the user describes a whole group ("all company repositories", "everything under this folder", "these research
repositories have their own rules"), write one rule instead of registering each project:

- `docs.mjs group add --remote <start of the remote URL> --in-repo none` — by remote, works on every computer. Take the
  prefix from a real remote of that group (`git remote get-url origin`), cut at the host or organization the user means.
- `docs.mjs group add --folder <folder> --in-repo all` — by the folder the projects sit in; only on this computer.
- `--skip` instead of `--in-repo` marks the group as not managed.
- `docs.mjs group list` shows the rules in order (the first match wins; a project's own entry beats every rule);
  `docs.mjs group remove <number>` removes one.

Add rules only from what the user said; never infer a group from what you see. After adding, run `where` in one
project of the group and tell the user what it now says. A company's remote host goes in the user's registry only,
never into this skill's files.

## 4. Move documents

Know what is moving before acting. When the user named one specific file, do it. When they named a type, "these",
or "the related ones", **show the list of files first and act only after a yes.** Go through `references/checklist.md`.

### Private → public (from the store into the repository)

1. Read every file that becomes public. Look for: accounts and passwords, internal addresses and machine names, names
   of customers and colleagues, prices and costs, unfixed security weaknesses, opinions about people. Any of them:
   stop, show the user those lines, and ask whether to delete, rewrite or keep the file private.
2. Move the file from `<store>/projects/<project>/<path>` to the project's `docs/<path>`, same path and name.
3. Links: any link in it to other store files is removed or replaced by a sentence; repository documents never link
   into the store.
4. Update the project's registry entry so the check knows this is intended:
   - **Just this file**: add its repository path to `allow`, e.g. `"allow": ["docs/decisions/2026-10-03-store-todos-in-json.md"]`.
   - **The whole type**: add the type to `in_repo` (`docs.mjs init --in-repo …`) and move every file of that type
     (step 1 for each).
5. `docs.mjs check`. Commit on both sides: an addition in the repository, a deletion and the registry change in the store.

### Public → private (from the repository into the store)

1. No store yet: create one by section 1. Move the file to `<store>/projects/<project>/<same path>`; for a whole type,
   also take it out of `in_repo`.
2. Commit the deletion in the project repository.
3. **Tell the user plainly:** the file is no longer in the repository, but history still shows it. Run
   `git log --oneline -- <path>` to see which commits it was in.
   - Never pushed anywhere others can see: history can be cleaned; ask whether to.
   - Already pushed to a public repository: treat it as leaked. If it holds passwords or tokens, the user changes them
     first. Cleaning history rewrites commits and needs a force push, and clones and forks cannot be cleaned. Tell the
     user exactly this and let them decide; do not clean history yourself.

## 5. Wrap up finished work

The target is `work/<date>-<short-name>/`.

0. **Check it is really done.** Look for what the plan says was built (code, tests, docs). If something marked done
   cannot be found, stop: tell the user what is missing and ask before archiving anything.
1. **Keep what matters** (ask about each item, "keep this?", and write only after a yes):
   - What the plan settled that someone will ask "why" about later: a `decisions/YYYY-MM-DD-<short-name>.md`.
   - What changed how the project works: update the matching file in `internals/` in place.
   - Test scripts worth running again: turn them into real tests in the project's own test folder.
2. Set `status: done` at the top of `plan.md` (or `test.md` when there is no plan); abandoned work gets `dropped` and
   one sentence on why.
3. Delete `evidence/raw/` and this work's leftovers in the project's `.scratch/`; keep only the screenshots and logs
   that back the conclusion.
4. Move the whole folder into `work/archive/`.
5. `docs.mjs check`; in the store, commit there.

In a project that uses a tool with its own document home: wrap up the requirement the tool's way; here, archive only
the material the tool does not take.

## 6. Tidy up scattered documents

In one project, or an old repository of documents the user made before.

1. One project: `docs.mjs check` and work through what it lists. An old documents repository: first work out which
   project each folder belongs to; register unregistered projects by section 2.
2. For every item, say where it would go and what it would be called; put it all in one table for the user and act
   only after a yes.
3. Files the project's own rule files tell agents to read or update (a spec-driven workflow's `SPEC.md`, `TASKS.md`,
   a code map like `docs/ARCHITECTURE.md`) are not scattered documents even when `check` flags them: leave them where
   they are and add their paths to `allow` in the project's registry entry, so the check and the pre-commit check let
   them through.
4. Cannot tell the type (one file mixes a plan and a decision): put the whole file in `notes/`; do not split it.
5. Private-type documents that were committed and are now moved out stay in history: tell the user as in section 4,
   "Public → private", step 3.
6. The repository has the user's uncommitted or staged changes: do not move tracked files there (your renames would
   end up in their next commit). List what would move and leave it for when their work is committed.
7. Whether to delete or archive an emptied old repository is the user's call.

## When to stop and ask

- Before creating a store (whether, its name, its place); before changing global settings.
- Before anything that makes content public.
- History rewriting, force pushes, changing a repository's visibility: give the steps; do not do them.
- `docs.mjs` fails or cannot find the store: do not make do with another place; tell the user which command said what.

## Pitfalls

| Situation | What to do |
| --- | --- |
| Tempted to put the plan in `PLAN.md` at the root or `docs/design.md` "for now" | Run `where`; until the arrangement is decided, drafts go in `.scratch/` |
| The user said "remember this" or "write it down" | A file by the conventions, not your own memory and not an online document |
| Seeing a public remote and choosing "store" for the user | Say what you see; the user chooses |
| Inferring a group rule from several similar projects | Ask; rules come from the user's words only |
| Adding a pointer to the store in the project's `AGENTS.md` | Never; the global rule already tells agents where the store is, and projects keep no trace of it |
| Writing into `.rein/`, `openspec/` or another tool's folder by hand | Use the tool's commands; if the tool cannot be used, tell the user |
| `check` flags `SPEC.md` or `TASKS.md` that the project's own rules use | Not stray: add them to `allow`; moving them breaks the project's workflow |
| Talking to the user in English because this skill is in English | Talk in the user's language; write titles and text in documents in their language too |

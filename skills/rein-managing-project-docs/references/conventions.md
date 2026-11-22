# Project document conventions: what to write, what to call it, where it goes, what to do when it is out of date

This is the full text of the conventions in the skill `rein-managing-project-docs`, and the only place that says
where project documents go: other tools and repositories that need it link here instead of keeping a copy.
It is the same for every person and every project. Only two things differ per person, and neither is written here:
the store's name and place (in the config file), and which types each project keeps in its repository (in the registry).

## In one minute

- **User-facing docs always live in the project repository**: `README.md`, usage and development docs under `docs/`,
  `CHANGELOG.md`, plus the code and its real tests.
- **The other four types (internal docs, decision records, work folders, notes) go in the project repository or in
  the store, as the user decides per project**, recorded in the registry. There is no default. The first time a
  project needs one of these, the agent follows what the user has said; if the user has said nothing, it asks once.
  A user can also decide for a whole group of projects at once (group rules), or mark projects that keep their own
  rules (not managed).
- **The store is optional.** Someone who keeps every document in project repositories never needs one. When some
  project first needs documents kept out of its repository, the skill creates one, named and placed as that person says.
- **Both sides have the same shape**: `docs/<type>/…` in the project repository, `projects/<project>/<type>/…` in the
  store. Moving a document means moving it to the same path on the other side.
- **Keep one thing in mind when deciding**: what is in the store can always move into the repository; what has been
  in the repository and pushed where others can see it cannot be taken back (git history keeps it).

## Where everything is

```text
skill rein-managing-project-docs/     the same for everyone; installed and upgraded with the skill, holds no one's data
├── SKILL.md                          multi-step work: set up and create the store, register, move, wrap up, tidy
├── references/
│   ├── conventions.md                these conventions
│   ├── checklist.md                  what to check by hand when moving documents
│   └── rule-template.md              the global rule template (setup fills in this computer's paths)
├── assets/templates/                 the top of each document type
├── assets/store/                     the first files of a new store
└── scripts/docs.mjs                  setup / where / init / check / group

~/.config/rein-managing-project-docs/config.json    this computer: where the store is (null without one)

<store>/                              the person's own; name and place are theirs to choose; absent without a store
├── README.md                         what this store is (written when it is created)
├── projects.json                     the registry: group rules and one entry per project (next to the config file when there is no store)
└── projects/<project>/
    ├── internals/                    internal docs: how the project works now
    ├── decisions/                    decision records: why it was decided this way
    ├── work/                         one folder per piece of work: plan, test record, test data, screenshots
    │   └── archive/                  finished work
    └── notes/                        notes and research
```

Upgrading the skill replaces only the upper block; a person's store, config and registry are in the lower one and stay
untouched.

## Document types

| Type | When to create | Name | Where | What it says | When to clean up |
| --- | --- | --- | --- | --- | --- |
| User-facing docs | Usage, install or public interfaces change | `README.md`, `docs/<topic>.md`, `CHANGELOG.md` | Project repository | How to install, use, contribute | Never; it changes with the code |
| Internal docs | Someone needs to know how the project works now: architecture, runtime, deployment, data | `internals/<topic>.md`, e.g. `architecture.md`, `operations.md`; no date, no version | Per project | How it is now (not how it was or will be) | Never; edit in place when the code changes, the old text stays in git history |
| Decision records | A choice someone will later ask "why" about, with options that were turned down | `decisions/YYYY-MM-DD-<short-name>.md` | Per project | Context, decision, options turned down and why, consequences | Never deleted; when overturned, `status: superseded` plus `superseded_by` |
| Work folders | A plan comes before the work, the work spans sessions, or a test record should be kept | `work/YYYY-MM-DD-<short-name>/`: `plan.md`, `test.md`, `test/`, `evidence/` | Per project | See "Inside a work folder" | When done: keep what matters, then move the whole folder to `work/archive/` |
| Notes | Research or ideas not yet decided, worth keeping | `notes/YYYY-MM-DD-<short-name>.md` | Per project | What was found, sources, open questions | Delete when no longer useful; notes are not a basis for anything |
| Scratch | Drafts, trial output, screenshots tools save on their own | `.scratch/` in the project | Never committed | Anything | Delete when done |

"Per project": when the project keeps that type in its repository, the path is `docs/` plus the name column; when it
keeps it in the store, `<store>/projects/<project>/` plus the same path.

Only two types are maintained over time (internal docs and decision records), a few files each per project. Work
folders are process: when the work is done they retire to `archive/`.

**Not covered by this table:**

- Re-runnable tests (unit tests, fixtures): they belong to the code, in the project's own test folder.
- Rule files (`AGENTS.md`, `CLAUDE.md`): they are rules for agents, not documents.
- What a tool with its own document home manages: see "Projects that use a tool with its own document home".

**Do not write what is not needed:** a change that one sentence explains belongs in the commit message. Without an
option that was turned down, it is not a decision.

### Inside a work folder

```text
work/2026-11-22-export-csv/
├── plan.md        the plan: what it achieves, how, what the user must decide. Its status is the status of the work
├── test.md        the test record: what was tested, how (commands as run), results, conclusion
├── test/          test data and throwaway scripts (run from the project root; paths relative to it)
└── evidence/      screenshots, logs. Large raw logs go in evidence/raw/, which is never committed
```

Not every part is needed: checking one question needs only `test.md`; a plan alone needs only `plan.md`.
Work that touches several projects (say, a shared library) lives in the repository where it started, with one line per
project in `plan.md`.

A throwaway script that must sit inside the project to run (because it imports project code) lives in the project's
`.scratch/` while working; afterwards copy what is worth keeping into `test/` and say in `test.md` how to run it.
Anything worth running again becomes a real test in the project's test folder.

## How a project's arrangement is decided

**The user decides, per project or per group of projects; the agent follows and never picks a default.**

`docs.mjs where` looks it up in this order and says which one applied:

1. **The project's own registry entry** (`in_repo`, or `skip`).
2. **The first group rule that matches** (`groups`, in order): by the start of the project's remote URL, or by the
   folder it sits in.
3. **`defaults.in_repo`**, if the user ever wrote one.
4. **Nothing**: not decided.

What the agent does with each:

- **Decided by the entry or a rule**: put documents where it says. A project matched by a rule but not registered yet
  is registered with `docs.mjs init` (no question) before its first document.
- **Not managed** (`skip`): the project has its own rules for documents (a research repository, a notes vault, a
  repository of skills). The agent follows those and asks nothing; `check` skips it.
- **Not decided**: if the user's words already settle it, the agent records that (table below) without asking;
  otherwise it asks once and lists the common choices. Until the user answers it writes none of the four types;
  a draft goes in `.scratch/`.
- **The store is needed but there is none**: create one first (skill section 1), named and placed as the user says;
  ask if they have not.

Common arrangements (what the agent offers when it asks; any set of types also works):

| The user says | Arrangement | Fits | Cost |
| --- | --- | --- | --- |
| "It will be open source", "it may go public", "keep internal docs out of the repo" | `--in-repo none`: all four in the store | Projects that are or may become public | Documents do not follow code branches |
| "This is the company's (someone else's) repository, add no files" | `--in-repo none` | Repositories that are not the user's to add files to | Same |
| "Keep docs with the code", "it's my private project, no need to split" | `--in-repo all`: all four in the repository; no store needed | Private projects, or teams that review docs in pull requests | Going public later means moving internal docs out and cleaning history |
| "Contributors may see decisions, keep the rest out" | `--in-repo decisions` | Open-source projects that want to show why | Each decision needs a moment's thought before it is written |

No arrangement suits every project, which is why the user chooses and the agent does not.

More rules:

- **Group rules are added only when the user says so** ("all company repositories the same way", "everything under
  this folder keeps its own rules"). The agent does not infer groups. Remote rules work on every computer; folder rules
  only where that folder exists.
- **One document with its own wish**: "keep this one out" or "put this one in" — follow the user. When a type goes in
  the store but the user wants one document in the repository, its repository path goes into the entry's `allow`
  (that is how the check knows it is intended).
- **Changing an arrangement**: "from now on this project's decisions go in the repo" — move that type's existing files
  (skill section 4), then update the registry.
- **Sensitive content**: a type goes in the repository, but this document holds accounts, internal addresses, customer
  names, costs or unfixed security weaknesses: ask the user where it goes first.

### The registry

`projects.json`: at the store's root when there is a store (it travels to other computers with it), next to the config
file otherwise. `init` and `group` change it; editing by hand also works.

```json
{
  "version": 1,
  "groups": [
    { "remote": "git.example.com/team", "in_repo": "none", "note": "company repositories" },
    { "folder": "D:/code/oss", "in_repo": "none" },
    { "folder": "D:/code/tools", "in_repo": "all" },
    { "folder": "D:/code/research-notes", "skip": true }
  ],
  "projects": {
    "todo-cli": {
      "match": ["github.com/someone/todo-cli"],
      "in_repo": ["decisions"],
      "allow": ["docs/internals/architecture.md"],
      "tools": [],
      "added": "2026-11-22"
    }
  }
}
```

| Field | Meaning |
| --- | --- |
| project name (`todo-cli`) | The folder name in the store; by default the project folder's name |
| `match` | How the project is recognized: remote URLs (no protocol, no `.git`), or the folder name when there is no remote. Where the project sits on each computer is not recorded |
| `in_repo` | The user's arrangement: the listed types (`internals`, `decisions`, `work`, `notes`) go under the project's `docs/`, the rest in the store. `[]` means all four in the store. **Missing means not decided** (unless a group rule or `defaults` applies) |
| `skip` | `true`: this project keeps its own rules; agents ask nothing and the check skips it |
| `allow` | Files let through on purpose (paths relative to the project root; `init --allow a,b` adds them): a type kept in the store, but the user wants this one in the repository; a user-facing doc named like a working document; or files the project's own rules use, such as a spec-driven workflow's `SPEC.md` and `TASKS.md` |
| `tools` | Tools with their own document home found at registration; only a record, the check looks at what exists now |
| `groups` | Optional. Rules for groups of projects, first match wins: `remote` (start of the remote URL) or `folder` (projects inside it), with `in_repo` (`"all"`, `"none"` or a list) or `skip`. `note` is for people |
| `defaults.in_repo` | Optional, **absent in a new registry**. Only when the user said "all my projects this way": projects matched by nothing else follow it |

## Names and status

- File and folder names: lowercase English words joined by hyphens. Titles and text: in the user's language, inside the file.
- Dated types (decisions, work folders, notes): `YYYY-MM-DD-<short-name>`, the date it was created. **No sequence
  numbers**: documents can be split across two repositories and numbers would not line up; two sessions creating one
  at the same time would also collide.
- Undated (internal docs): one per topic, edited in place. No `-v2`, `-final`, `-new`.
- Each document starts with front matter (templates in `assets/templates/`; their English is only the structure, write
  headings and text in the user's language):

| Type | Front matter | `status` values |
| --- | --- | --- |
| Internal docs | `title`, `updated` | none |
| Decision records | `title`, `date`, `status` | `accepted` (in force), `superseded` (replaced; add `superseded_by`) |
| A work folder's `plan.md` (`test.md` when there is no plan) | `title`, `date`, `status` | `active`, `done`, `dropped` |
| Notes | `title`, `date` | none |

## When a document is out of date

| Situation | What to do |
| --- | --- |
| A piece of work is done | Keep what matters first: decisions become decision records; changes to how things work update internal docs; tests worth re-running become real tests. Then `status: done`, move the whole folder into `work/archive/`, delete `evidence/raw/` |
| A piece of work is abandoned | `status: dropped`, one sentence in `plan.md` on why, move it into `work/archive/` |
| A decision is overturned | Write a new decision record; keep the old one with `status: superseded`, `superseded_by: <new file>` |
| Internal docs no longer match the code | Edit them in place until they match; update `updated`. No new file |
| A note is no longer useful | Delete it |
| A whole project is dropped | Leave `projects/<project>/` in the store as it is; add `"archived": true` to its registry entry |

Agents do not read `work/archive/` unless the user mentions it.

## Projects that use a tool with its own document home

Some tools manage a piece of work's requirements, specs, tasks and acceptance themselves (rein's `.rein/`, OpenSpec's
`openspec/`, Spec Kit's `.specify/`, Kiro's `.kiro/`); some ticket tools keep a work-item folder per bug or requirement.
One rule: **what the tool has commands for belongs to the tool; everything else follows these conventions.**

| Document | Belongs to | Where |
| --- | --- | --- |
| Requirement specs, tasks, acceptance, ticket material | That tool | The tool's own place, written with its commands; never edited or moved by hand |
| User-facing docs, internal docs, decision records, notes | These conventions | As in the table above |
| Process material the tool does not take (throwaway test data and scripts, raw benchmark data, research) | These conventions | `work/YYYY-MM-DD-<short-name>/` per the project's arrangement, with only `test.md`, `test/`, `evidence/`; no separate `plan.md` |

The check skips these tools' folders (`.rein/`, `.kiro/`, `.specify/`, `openspec/` by default; add more with `toolDirs`
in the config file).

These folders usually sit in the project repository, so when the project goes public, so do the specs in them. Content
others should not see does not go in a spec; it goes in a decision record or internal doc kept in the store.

## The tool

Everything is in the skill's `scripts/docs.mjs`, Node 18 or newer, no dependencies. `docs.mjs` below means
`node <skill folder>/scripts/docs.mjs`.

| Command | What it does |
| --- | --- |
| `docs.mjs setup [--store <path> \| --no-store]` | Once per computer: record where the store is (creating it at the given path, or connecting to an existing one) and install the global rule for Claude Code and Codex. Previews by default; `--apply` writes |
| `docs.mjs init [--in-repo <arrangement>]` (in a project) | Register a project: record the arrangement (`all`, `none` or types separated by commas; without `--in-repo` it takes the one a group rule gives), create its store folder, ignore `.scratch/` locally, install a pre-commit check. `--skip` marks it as not managed |
| `docs.mjs where` | This project's name, whether there is a store, whether the arrangement is decided and by what, where each type goes |
| `docs.mjs check` | Check this project: wrong place, wrong name, store documents copied into the repository, work to archive |
| `docs.mjs check --store` | Check the whole store, including uncommitted and unpushed changes |
| `docs.mjs group list \| add \| remove` | Group rules: `add --remote <prefix>` or `--folder <path>`, with `--in-repo …` or `--skip` |

Projects that are not registered work too: the project name is the folder name and user-facing docs are written as
usual; the other four types wait until the arrangement is decided.

## Moving to another computer

1. Install the skill `rein-managing-project-docs`.
2. With a store: clone it anywhere and tell the agent "connect this computer to my store at <path>" (it runs
   `setup --store <path>`, which recognizes an existing store). Without one: "set up my project documents".
3. Add the store to Claude Code's and Codex's settings as the last lines of `setup` say.
4. Folder group rules match only where those folders exist; add rules for this computer's layout if it differs.

## What never goes in the store

- Passwords, tokens, private keys: in no repository, the store included.
- Data the company does not allow out (query results, server logs, customer information): keep it where the company
  allows. Such a project's folder can go in the store's `.gitignore` so it stays on this computer and is never pushed.

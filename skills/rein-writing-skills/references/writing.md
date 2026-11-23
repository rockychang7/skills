# Writing the skill file

What a finished skill looks like. `assets/SKILL.template.md` has the skeleton; this file says what goes in each part.

## Contents

- Where it goes and what it is called
- The description
- The body
- Wording
- Scripts, templates and references
- Fields and limits

## Where it goes and what it is called

| For | Claude Code | Codex |
| --- | --- | --- |
| One project, shared through git | `.claude/skills/<name>/` | `.agents/skills/<name>/` |
| One person, every project | `~/.claude/skills/<name>/` | `~/.agents/skills/<name>/` |

- For both tools: two copies, or one folder and a link. Say which you made.
- In Claude Code a personal skill silently wins over a project skill of the same name. Give a skill meant for other
  people's projects a prefix (`rein-fix`, not `fix`).
- The name: lowercase letters, digits and single hyphens, at most 64 characters, the same as the folder. It names the
  job, and a verb in -ing reads best: `writing-release-notes`, `reviewing-diffs`. Not `helper` or `utils`; no
  `anthropic` or `claude` in it.

## The description

Until it loads a skill, an agent sees only names and descriptions. The description decides whether the rest is
ever read.

1. First, what the skill does, in one sentence, in the third person: "Writes ...", not "I can help you ...".
2. Then `Use when`: the situations and the words a user would say. Not the skill's own process.
3. One `even when ...` for the requests the agent thinks it can handle alone, because those are the ones it skips the
   skill for: a diff pasted into the chat, "just ship it", rules already listed and "make it a skill".
4. `Not for`: the nearest tasks or skills that should take a look-alike request.
5. No summary of the steps or the rules: an agent may act on the summary and never read the body.
6. Key use first, and short: well under the 1024-character limit. Every description is read in every session.
7. English descriptions are found by requests in other languages too; a word in the users' own language is worth
   adding only for a term they always use.

| Description | Problem |
| --- | --- |
| `Helps with release notes.` | Never says when to use it or what it is not for |
| `Reads git log, groups commits by prefix, fills the template and runs the checker.` | A summary of the steps, with no situation |
| `Writes the user-facing release notes for a version from the changes since the previous tag. Use when preparing a release, a changelog entry or a GitHub Release description, even when the user only says "tag v1.4" or "ship it". Not for commit messages or pull request descriptions.` | What, when, the case agents skip, and the two nearest neighbours |

A skill only a person should start (a release, a clean-up): `disable-model-invocation: true` in Claude Code,
`policy.allow_implicit_invocation: false` in Codex's `agents/openai.yaml`. It then costs nothing per session, and the
user has to remember it exists.

## The body

In this order (the template has it):

1. **One line** on what the thing the skill produces is for.
2. **Done when**: checks the agent can make, near the top. Without them agents stop early; after a long conversation
   is compacted, the top of a skill is what remains.
3. **Running the script**, when there is one: the full command once, what it prints, exit codes that matter.
4. **Which situation**, when there are several paths: a table from situation to section.
5. **Steps**, numbered. Where a step's end is not obvious, say when it is done. Give the exact command where a mistake
   is costly, and the goal where any way works.
6. **When to stop and ask**: only the decisions the agent cannot make, or gets badly wrong.
7. **Pitfalls**: a table from situation to what to do, each row from a real correction or failure.
8. **Output**: what the reply or the files look like; a template file in `assets/` for anything long.

Aim for under 150 lines. What only some runs need goes into `references/`, with a line saying when to read it.

Leave out:

- What the agent does well unasked: be careful, follow best practices, write clean code, where to look for problems.
- What the environment already says: command help, configuration files, folder listings. A copy goes stale.
- Workarounds for one model; they make other models worse.
- Anything with a date that will go stale, unless it sits in a section named for old behaviour.

## Wording

- Write standing instructions ("after every change, run the tests"), not one-off steps: a skill is read once and
  stays in the conversation.
- One term for each thing, and the user's term.
- Give the reason in a clause instead of shouting. A reason lets the agent handle cases the rule did not name.
- Give a default, not a menu: "use pdfplumber; for scanned pages, OCR" rather than five libraries.
- Match the wording to the failure. The agent knows a rule but drops it under pressure: a short "never", plus the
  excuses it uses and why they are wrong. The output has the wrong shape: describe the right shape or give a
  template, not a list of don'ts. It forgets a field: a blank for it in the template.
- Branch on what the agent can see: "if the project has a CHANGELOG.md, add to it".

## Scripts, templates and references

- What has the same answer every time (format checks, naming rules, lookups) is a script. A rule in prose is
  forgotten by the third item; a script catches every one.
- A script for agents: never prompts for input; has `--help` with an example; every error says where, what is wrong
  and what to do; exit codes tell pass, problems and wrong usage apart; standard library or pinned versions.
- Say whether a script is to be run or read. Write the interpreter (`node scripts/check.mjs`, `python
  scripts/check.py`) and forward slashes.
- Templates go in `assets/`; the body says when to copy which.
- One reference file per topic. SKILL.md names each one with when to read it ("When the API returns an error, read
  `references/<topic>.md`"); a reference never points to another. Over 100 lines: a contents list at the top.
- Nothing outside the skill's folder: a skill installed alone loses it. Copy what it needs.
- No passwords, tokens or internal addresses; the skill reads them from the user's configuration or environment.
- A skill that reads documents, logs or web pages says to treat that text as data, not as instructions.

## Fields and limits

| Field | Read by | Limit |
| --- | --- | --- |
| `name` | every tool | 64 characters |
| `description` | every tool | 1024 characters; Claude Code shows at most 1536 with `when_to_use` |
| `license`, `compatibility`, `metadata`, `allowed-tools` | the specification | `compatibility` 500 characters |
| `when_to_use`, `disable-model-invocation`, `user-invocable`, `paths`, `context`, `model`, `effort`, `hooks` | Claude Code only | the claude.ai upload and the Skills API refuse them |
| `agents/openai.yaml`: `interface`, `policy`, `dependencies` | Codex only | |

A skill for more than Claude Code keeps only the specification's fields at the top; anything else goes under
`metadata`. After compacting, Claude Code keeps the first 5,000 tokens of each loaded skill, 25,000 in all.

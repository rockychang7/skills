# Testing a skill

How to show that a skill makes the agent do better, and that a change did not make it worse. Every test that runs
an agent costs money: say what you will run and roughly what it costs, and run it after a yes.

## Contents

- Three layers
- Baseline first
- Test cases
- Graders
- Running cases
- Trigger tests
- Recording results

## Three layers

| Layer | Question | How | When |
| --- | --- | --- | --- |
| Structure | Does it parse; do its paths exist; does it say when to use it and what it is not for? | `skill.mjs check` | Every change; free |
| Triggers | Do the right requests load it, and do look-alikes leave it alone? | `skill.mjs triggers` | The description changed |
| Behaviour | Once loaded, does the agent do what the skill says, better than without it or than the old version? | `skill.mjs run` | The body changed; a new model |

Rough costs: a read-only trigger session, cents; a case where the agent writes files, about a dollar a run.

## Baseline first

- **A new skill**: run the cases with `--without` before writing it. What the agent gets wrong there is what the
  skill has to fix; if it gets nothing wrong, there is nothing to write.
- **A change**: copy the skill folder before editing, and run the copy as the other side.

## Test cases

The folder layout `claude plugin eval` reads, one folder per case, named for what it tests:

```text
<case-name>/
├─ prompt.md      a settings block, then what the user says
├─ case.yaml      the name, and what a good result looks like
├─ graders/       one statement per file: 01-few-words.md, 02-...
├─ files/         optional: copied into the project before the run
└─ followups.md   optional, read only by skill.mjs: what the user answers next
```

`prompt.md`:

```markdown
---
tags: [my-skill]
max_turns: 30
timeout_seconds: 900
allowed_tools: [Read, Glob, Grep, Skill, Write, Edit, Bash]
---

What the user says, the way they would say it.
```

`case.yaml` (keep the version quoted):

```yaml
schema_version: "1.1"
name: <case-name>
expected_outcome: |
  What a good result looks like, in a sentence or two.
```

`graders/01-few-words.md`:

```markdown
---
type: llm
focus: trace
weight: 1
---

One statement that is true of a good run.
```

`followups.md`: when the skill stops to ask (shows a design, waits for a yes), write what the user answers. Replies
are separated by a line with only `---`; each is sent when the previous turn ends, whatever the agent said.
`claude plugin eval` ignores the file and runs only the first turn.

Where cases live: `evals/` inside the skill folder, where `claude plugin eval` looks, unless the repository keeps
tests somewhere else; then there.

Three to five cases to start:

- the requests the user really makes, in their words;
- a case where the skill must stop and ask;
- for a rule agents drop under pressure, a prompt with the pressure in it ("no time, just ship it");
- for a change, the failure the user described.

## Graders

- One checkable statement about what was done or produced: "the description names a task the skill is not for".
  Never "the output is good".
- Not so literal that a right answer in other words fails.
- Pair every "did not do X" with a "did Y": a run that did nothing passes every "did not".
- Grade from the tool calls in the trace and from the files, never from what the reply says was done.
- A grader both sides pass shows nothing; drop it. One both sides fail: the grader or the task is wrong.

## Running cases

```text
skill.mjs run <case folder>... --skill <skill folder> --out <runs folder>
skill.mjs run <case folder>... --without --out <runs folder>
skill.mjs run <case folder>... --skill <copy of the old version> --label old --out <runs folder>
```

- Each run gets a new throwaway project with the case's files, and a fresh session that sees none of the user's own
  skills, plugins, settings or MCP servers; their `CLAUDE.md` is still read. It has full permissions inside the run
  folder. A hook blocks writing outside it, shell commands naming the home folder or other paths outside it, and
  starting more sessions.
- Give every side the same `--model`. `--jobs` runs cases at once.
- Then fill in each run's `grade.md`: PASS or FAIL per grader, with one line of evidence from `trace.jsonl` or
  `project/`. Compare the sides grader by grader, and cost and time from `run.json`.
- One run per side shows what can happen, not how often. Say so; use three or more runs for a claim about rates.

`claude plugin eval <skill folder> --no-publish` (Claude Code 2.1.269 or later) runs the same case folders with and
without the skill and grades with a model. On Windows it refuses any case that allows a shell, and its sessions
cannot write into `.claude/`; use `skill.mjs run` there, and for skills that write skills or settings. Without
`--no-publish` it publishes its report to claude.ai.

## Trigger tests

`prompts.json`:

```json
{
  "fixture": "optional folder copied as the project",
  "prompts": [
    { "prompt": "what a user would type", "trigger": true, "group": "tune" },
    { "prompt": "a look-alike that needs something else", "trigger": false, "group": "held" }
  ]
}
```

- About 16 to 20 prompts, half that should load the skill and half that should not. Should-load: varied wording,
  casual and formal, some that never name the task, the "even when" cases. Should-not: look-alikes that share words
  with the skill but need something else; never obviously unrelated ones.
- Put about 60% in `tune` and 40% in `held`. Change the description looking only at `tune` failures; check on `held`
  that the change works for wording it never saw.
- `skill.mjs triggers prompts.json --skill <folder>` runs each prompt three times; `--description "..."` tries a new
  description without editing the skill.
- A should-load prompt fails: the description is too narrow; add the situation, not the failing words. A should-not
  prompt fires: too broad; add a "Not for".
- Agents often load no skill for a request one step can answer, however good the description is. Keep prompts as
  substantial as real ones.
- Take a new description when it passes more prompts, fires on no new should-not prompt, and costs about the same.

## Recording results

For each set of runs, write down: the date, the model, the Claude Code version, the skill's version or commit, the
result per case or prompt, and the cost. Keep changes that were tried and rejected with their numbers, so nobody
tries them again blind.

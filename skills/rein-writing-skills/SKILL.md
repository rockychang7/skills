---
name: rein-writing-skills
description: "Writes a new agent skill, or improves an existing one, from the user's own material: corrections they keep making, steps they repeat, a failure they saw. Keeps the skill to what the agent would otherwise get wrong, checks it with a script, and offers to test it against the old version or no skill. Use when the user wants a way of working saved as a skill, says a skill does not trigger or does the wrong thing, or asks to review or improve a skill, even when they have already listed the rules and only say \"make it a skill\", or only say \"make it more complete\". Not for rules that must hold every time (use a hook), project-wide instructions (AGENTS.md, CLAUDE.md), or running a skill."
license: MIT
compatibility: "Requires Node.js 18+ (no dependencies) to run scripts/skill.mjs; its run and triggers commands also need Claude Code."
metadata:
  author: rockychang7
  version: "0.1.0"
---

# Writing skills

A skill tells an agent, for one kind of task, what to hand over, in what steps, where to stop and ask, and what
not to do. It is not a lesson in what the agent already does well: every line has to change what the agent does,
and every rule has to come from the user.

Talk to the user in the language they write in; this file being in English is no reason to switch. Write the skill
in the language the user asks for; if they do not say, in the language of the skills next to it, or else theirs.

## Done when

- `skill.mjs check <skill folder>` reports no error, and every warning is fixed or the user knows why it stays.
- Every rule in the skill traces to the user's material or answers. Anything you proposed was shown to them as
  yours, and they said yes.
- The user saw the design (a new skill) or the before and after (a change) before any file was written.
- A change answers one failure the user described, and the skill grew only by what that failure needs.
- The reply says what [Output](#output) lists.

## Running the script

`skill.mjs` below stands for `node <this skill's folder>/scripts/skill.mjs`; `<command> --help` lists the options.

- `check <skill folder>...`: structure and wording, free. Each problem names the line and the fix.
- `run` and `triggers`: real Claude Code sessions in throwaway folders; they cost money. Read
  `references/testing.md` before using either.

## Which situation

| Situation | What to do |
| --- | --- |
| A way of working to save, with material: rules, corrections, a result they liked, the steps | [New skill](#new-skill) |
| "Write me a skill for X" with no material ("按我的习惯来") | Ask for it first: the corrections they keep making, a past result they liked, the steps they follow. Do not fill the gaps with common practice. Then [New skill](#new-skill) |
| A skill does not trigger, does the wrong thing, or the user keeps correcting it | [Change a skill](#change-a-skill) |
| "Make it better / more complete / more professional", with no failure named | Ask for one time it went wrong. Offer a review instead: `check` plus a read against `references/writing.md`, reported, nothing changed |
| "Check / review this skill" | The review above |
| A rule that must hold every time ("每次提交前都要…") | Not this skill. Say a skill cannot promise it (the agent may not load it) and a hook can |

## New skill

1. **Collect the material**: from the conversation first, then from the user. Done when every rule you will write
   traces to something they said or showed.
2. **Sort it.** What a script can check (formats, names, banned words) becomes a script the skill runs. What every
   task in the project needs belongs in the project's `AGENTS.md`: tell the user, do not move it yourself. What needs
   judgement in this kind of task goes in the skill.
3. **Show the design and wait for a yes**: the name, the description, each section of the body in one line, the
   scripts and templates, and where it goes. If the user has not said where: in the project (`.claude/skills/<name>/`
   for Claude Code, `.agents/skills/<name>/` for Codex) or theirs alone (`~/.claude/skills/`, `~/.agents/skills/`).
   A repository of skills has its own place for them; follow it.
4. **Write it** from `assets/SKILL.template.md`, by `references/writing.md`.
5. **Check.** Run `check` and fix what it reports. Then read each line and ask: without it, would the agent do
   anything differently? If not, delete it.
6. **Offer a test** by `references/testing.md`: which cases, roughly what it costs. Run only after a yes.
7. **Hand over**: [Output](#output).

## Change a skill

1. **Get one real failure**: what the user said, what the agent did with the skill, what they wanted. "It could be
   better" is not one.
2. **Copy the skill folder aside** before editing. The copy is what the change is tested against.
3. **Find where it went wrong:**

   | The agent | Change |
   | --- | --- |
   | did not load the skill | The description: the situation in the user's words, and "even when ..." for the case the agent thinks it can handle alone. Another skill took it: a "Not for" in both |
   | loaded it and did something else | The step, the done-when line or the output that allowed it |
   | keeps forgetting a rule a machine can check | A script the skill runs, or a hook |

4. **Make the smallest change.** Merge into a line that is there before adding one. Keep the user's words, terms and
   section names. Edit the part, not the whole file.
5. **Show the before and after**, write after a yes, run `check`, and offer to test against the copy.

## When to stop and ask

- Before writing or changing any file: show the design, or the before and after.
- Before adding a rule, section or example the user did not give.
- Before writing outside the project, or changing another skill.
- Before anything that costs money: `run`, `triggers`, `claude plugin eval`.

## Pitfalls

Seen in test runs of agents writing and changing skills without this one:

| Situation | What to do |
| --- | --- |
| Asked to make a skill "more complete" or "more professional" | Ask what went wrong. Agents grew a 40-line skill to 73 and to 106 lines with sections nobody asked for, and renamed the user's own term; skills that try to cover everything do worse on average |
| The description restates the rules or the steps | Say only what it does and when to use it: an agent may act on the summary and never read the body |
| No "Not for" in the description | Name the nearest tasks or skills that should take a look-alike request |
| Adding a list of trigger phrases to the description | One situation per kind of request, and one "even when". The description is read in every session, and every extra word pulls in look-alike requests |
| `必须`, `禁止`, `硬性要求`, `MUST`, `NEVER` | Say why in a clause. Keep a hard word only for a rule agents break under pressure |
| Rules the user never gave ("no emoji", "150–400 字") slip in while writing | Take them out, or list them as yours and ask |
| Checking a fix by asking again in the same session | Use a new session: skills are listed when it starts. Also try a look-alike request that must not load it |

## Output

Tell the user, in plain words:

1. What the skill does, in one sentence, and where it is.
2. What to say to bring it in, and what it is not for.
3. What was checked and tested, with the results; what was not tested.
4. What you decided for them (the name, the place), and any rule you added with their yes.

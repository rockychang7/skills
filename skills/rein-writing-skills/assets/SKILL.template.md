---
name: <lowercase-with-hyphens, the same as the folder>
description: "<What it does, in one sentence.> Use when <the situations, in the words a user would say>, even when <the request the agent thinks it can handle alone>. Not for <the nearest tasks or skills>."
---

<!-- Delete every section that does not apply, and this comment. Every line is read each time the skill loads. -->

# <Title>

<One line: what the thing this skill produces is for.>

## Done when

- <A check the agent can make: a script exits 0, a file exists, every X has a Y.>

## Running the script

`<tool>` below stands for `node <this skill's folder>/scripts/<tool>.mjs`. <What it prints; the exit codes that matter.>

## Which situation

| Situation | What to do |
| --- | --- |
| <What the user says or what the agent sees> | <The section to follow> |

## Steps

1. **<Step.>** <The exact command where a mistake is costly; the goal where any way works.> Done when <only if it is not obvious>.

## When to stop and ask

- <A decision only the user can make, or one the agent gets badly wrong.>

## Pitfalls

| Situation | What to do |
| --- | --- |
| <What an agent got wrong in a real run> | <What to do instead, and why> |

## Output

<What the reply or the files look like.>

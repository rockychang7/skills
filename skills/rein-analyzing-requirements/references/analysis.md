# The analysis file (analysis.json)

The analysis is the one source every page and SQL file is generated from.
Write facts in plain business language; the script does all layout.
For a complete sample run `req.py example`.

## Contents

- [Conventions](#conventions): IDs, `src`, `removed`, language
- [Top level](#top-level)
- [Overview](#overview): `meta`, `brief`, `roles`, `clients`
- [flows](#flows): the business processes, drawn as swimlane diagrams
- [Shared understanding](#shared-understanding): `terms`, `confusions`, `states`, `inputs`, `out_of_scope`, `skipped_sections`, `prototypes`
- [features](#features)
- [backend.apis](#backendapis)
- [backend.tables](#backendtables)
- [backend.data, configs, risks](#backenddata-configs-risks)
- [release](#release)
- [questions](#questions)
- [changes](#changes)
- [confirmations](#confirmations)

## Conventions

### IDs

| Item | Pattern | Example |
| --- | --- | --- |
| Client | lowercase letters; not `n`, `q`, `r` or `s` | `b`, `c`, `app` |
| Feature | client ID in upper case + 2 digits; `S` + 2 digits if no client is involved | `C03`, `S01` |
| API | client ID in upper case + a number; `N` + a number for internal tasks the frontend never calls | `C3`, `N1` |
| Question | `Q` + 2 digits | `Q01` |
| Release item | `R` + a number | `R1` |
| Table, config | its table name or config key | `activity_signup` |

IDs link the generated files together, and versions are compared item by
item using them. So:

1. An ID, once sent to anyone, is never changed or reused.
2. To delete, keep the item and add `"removed": "<why>"`. Never renumber.
3. To split, the main part keeps the ID and the new part takes a new one.
4. To merge, keep one; the other gets `"removed": "merged into C02"`.
5. Point live items (flow steps, features, APIs, open questions) at what
   replaced a removed item; `check` warns about any still pointing at it.

### src: where in the document

`"src": "§3.4"` points to a section of the requirement document; several are
written `"§3.4, §3.6"`. Section IDs come from the document's headings and are
listed by `new` and `refresh`: numbered headings keep their numbers, the rest
are numbered in order.

Never copy document text into the analysis. Pages show the cited section from
the stored document. The only exception is a question's `quotes`.

Items with `removed` may cite sections that no longer exist.

Every section is cited by a live item, itself or through a subsection, or
listed in `skipped_sections`; `check` reports the rest (`coverage.section`).
`changes` entries and removed items do not count.

### Language

Everything a person reads (names, summaries, rules, questions, notes) is
written in the requirement's language, the `lang` printed by `new` (default
`zh-CN`). Code names, table names, paths and config keys stay as they are.
`check` warns (`lang.mismatch`) when such text is in the other language.

### Optional fields

Leave out an optional field rather than writing `""` or `[]`.

## Top level

| Field | Required | What |
| --- | --- | --- |
| `format` | yes | Always `1` for this format |
| `meta` | yes | See below |
| `brief` | yes | See below |
| `roles`, `clients` | `roles` yes | See below |
| `flows` | yes | The business processes, see [flows](#flows) |
| `terms` … `prototypes` | no | See below |
| `features` | yes | What gets built, one item per feature |
| `backend` | no | `apis`, `tables`, `data`, `configs`, `risks` |
| `release` | no | Release steps the script cannot work out itself |
| `questions` | no | What is unclear, contradictory or undecided |
| `changes` | no | Change notes; empty until the first change after creation |
| `confirmations` | no | Answers to `confirm`-level issues from `check` |

## Overview

| Field | Required | What |
| --- | --- | --- |
| `meta.title` | yes | Requirement name |
| `meta.doc_version` | no | The version the document gives itself |
| `meta.code_commit` | yes | Code the analysis was checked against: `branch@commit`, e.g. `dev@1a2b3c4` |
| `meta.source_v` | yes | The stored document version the analysis follows: `1` after `new`. After `refresh` stores a newer one, raise it once the analysis takes in that version's changes. Every `src` names sections of this version |
| `brief.what` | yes | One or two sentences: what this is and how it is used, readable without technical knowledge |
| `brief.value` | no | What it brings |
| `roles[]` | yes | People and parts of the system in the flow: `id`, `name`, `does` (one sentence) |
| `clients[]` | no | Frontends this requirement changes: `id`, `name`, `where` (who uses it, where). Use the project's real clients from the project settings or the code; leave out when no frontend changes |

## flows

How the business actually runs: who does what, in what order, where it
branches and where it ends. Each flow becomes a swimlane diagram (one lane per
role) at the top of the brief, and every step links to the features that
carry it.

Split by process, not by screen: one flow per thing a person sets out to do
("sign up", "cancel and refill"), 3–10 steps each. A requirement usually has
one to three flows.

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | `P1`, `P2`, … |
| `name` | yes | The process in a few words |
| `summary` | no | One sentence |
| `steps[]` | yes | See below |

Each step:

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | Unique within the flow, e.g. `s1`; never reuse one for a different step |
| `role` | yes | A `roles` ID: who does it (the system counts as a role) |
| `kind` | no | `decision` for a question that splits the flow; `end` for an outcome where it stops. Leave out for a normal step |
| `text` | yes | One short sentence. A decision is a question ("还有名额吗？"); an end is the result the person sees |
| `next` | no | Where it goes after this step (see below) |
| `features[]` | no | Feature IDs that carry this step |
| `q` | no | A question this step waits for |
| `src` | no | Document section |

Where a step goes:

- Without `next`, a step goes on to the next step in the list. A straight
  flow is just its steps in order.
- `"next": ["s5"]` jumps to another step; `"next": []` stops here.
- A decision lists every branch with its condition:
  `"next": [{"to": "s4", "when": "有名额"}, {"to": "s7", "when": "名额满了"}]`.
  Other steps may label branches the same way.
- An `end` step never has `next`. Flows run top to bottom: do not loop back.

```json
{ "id": "P2", "name": "取消和补位", "steps": [
  { "id": "c1", "role": "visitor", "text": "在「我的报名」里点「取消」", "features": ["C04"] },
  { "id": "c2", "role": "visitor", "kind": "decision", "text": "离活动开始超过 24 小时吗？",
    "next": [{ "to": "c3", "when": "超过" }, { "to": "c6", "when": "不到 24 小时" }] },
  { "id": "c3", "role": "system", "text": "报名改为已取消，名额立刻放回", "features": ["C04"], "next": [] },
  { "id": "c6", "role": "visitor", "kind": "end", "text": "按钮置灰，提示不能取消" }
] }
```

## Shared understanding

| Field | What |
| --- | --- |
| `terms[]` | Document wording in plain words: `term`, `means` |
| `confusions[]` | Pairs that are easy to mix up: `a`, `b`, `diff` |
| `states[]` | How a status changes: `of` (what thing), `from`, `to`, `when` (trigger), `then` (what follows), optional `src` |
| `inputs[]` | Input rules: `where` (which form), `name`, `rule`, optional `src` |
| `out_of_scope[]` | Not done this time: `text`, optional `src`; give a date when it is done later |
| `skipped_sections[]` | Document sections with nothing to build (background, goals): `src`, `why`. Coverage checks skip them |
| `prototypes.links[]` | Design and prototype links: `title`, `url` |
| `prototypes.images[]` | Images that explain a feature: `file` (path inside the requirement folder), `caption` (which page, which state). Skip decorative ones |

## features

One item per feature a user can see, grouped by client.

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | See [IDs](#ids) |
| `side` | yes | A `clients` ID, or `s` when no client is involved |
| `name` | yes | Short name |
| `summary` | yes | One sentence |
| `rules[]` | yes | See below |
| `acceptance[]` | yes | 1–3 examples: the main case and one edge case. Write each as `situation：expected result` (e.g. `离开始 23 小时取消：按钮置灰，提示「…」`); pages split it at the first colon into two columns |
| `impact[]` | no | What changes for people using **existing** things: a page gains a button, a flow gains a step. One line each, no APIs or tables. Leave out for brand-new things |
| `apis[]` | no | API IDs that implement it, internal ones included. Pages derive "which clients change" from this |
| `removed` | no | Why it was dropped |

### rules

| `kind` | Label | When | Extra fields |
| --- | --- | --- | --- |
| `prd` | from the document | The document says it, or the product owner answered a question | `src` or `q` (an answered question), or both |
| `code` | current behaviour | How the system works today, in plain words | optional `path` (`file:line`, for developers; not shown in the brief) |
| `ai` | suggestion | Your proposal | — |
| `ask` | undecided | The document is unclear | `q`: the question ID |

Only write a `prd` rule when it changes how code is written or accepted.
"Cancelling is not allowed within 24 hours of the start" is a rule; "signup
improves engagement" is not. A suggestion that touches money, status or
permissions belongs in a question, not an `ai` rule.

One rule says one thing. `check` warns over 80 units (a Chinese character or
a word is one unit) and over 20 rules in one feature: split the rule or the
feature, or drop rules that only restate the document.

## backend.apis

One item per API or internal task (callbacks, scheduled jobs, message
consumers). Keep related items next to each other.

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | See [IDs](#ids) |
| `side` | yes | The client it serves (internal tasks too); `s` when there is no client |
| `internal` | no | `true` when no frontend calls it; the ID then starts with `N` |
| `kind` | yes | `new` or `modify` |
| `name` | yes | Short name |
| `path` | for `modify` | The real route found in the code, e.g. `GET /activity/detail`. Find it; never guess |
| `does` | yes | One sentence: what a new API does, or what an existing one changes into |
| `now` | for `modify` | One sentence: what it does today |
| `where` | yes | When it is called: the page and action ("tapping Sign up on the detail page"), or the trigger for internal tasks ("daily at 10:00") |
| `todo[]` | yes | Business steps, one per line. No field or class names |
| `online[]` | for `modify` and `internal` | Production concerns: who calls it today (other pages, old app versions, other services), what happens when old clients send no new parameters, which existing data it touches, call volume. If you checked and nothing is affected, say why |
| `owner` | no | Only when the user named one |
| `status` | no | `todo` (default), `doing`, `testing`, `done`. Set by people; write back what they chose |
| `depends[]` | no | API IDs that must exist first |
| `removed` | no | Why it was dropped |

Which question blocks an API is worked out from `questions[].affects`.

## backend.tables

| Field | Required | What |
| --- | --- | --- |
| `name` | yes | Table name |
| `kind` | yes | `new` (create) or `alter` (change an existing table) |
| `title` | yes | What the table is called in plain words |
| `does` | yes | What it holds or what changes |
| `sql` | yes | The full, latest statement: `CREATE TABLE …` for `new`, `ALTER TABLE …` for `alter` |
| `patches[]` | no | Statements for environments that already ran an earlier version (see below) |
| `init[]` | no | Initial rows for a new table; `INSERT` only |
| `rollback` | for `alter` | How to undo it |
| `db` | no | Database name, when it is not the default one |
| `removed` | no | Why it was dropped |

Changing a table after an environment ran its SQL:

- Before any environment ran it, just edit `sql`.
- Afterwards, do both: update `sql` to the full latest statement (for
  environments that never ran it), **and** append the matching `ALTER` to
  `patches` (for environments that did). Never edit or remove an existing patch.
- Which environment ran which version is recorded with `applied`. From that,
  the SQL file gives each environment only what it has not run yet, and
  `check` reports `sql.patch-missing` when a table changed with no new patch.
- The same holds for `data`: once an environment ran a change, leave that
  entry as it is and add a new entry for any further change.

## backend.data, configs, risks

`backend.data[]`: changes to existing rows, whether or not the table changes.

| Field | Required | What |
| --- | --- | --- |
| `table` | yes | Table name |
| `kind` | yes | `insert`, `update` or `delete` |
| `does` | yes | Why, and how many rows in each environment |
| `sql` | yes | `update` and `delete` must have a `WHERE` |
| `rollback` | for `update` and `delete` | SQL that puts the data back |
| `check` | yes | `SELECT COUNT(*) …` that finds at least one row once done |
| `db` | no | Database name, when it is not the default one |

`backend.configs[]`: settings to add or change.

| Field | Required | What |
| --- | --- | --- |
| `key` | yes | Config key, as used in the code |
| `kind` | yes | `new` or `modify` |
| `values` | yes | A value for every environment in the project settings (default `dev`, `test`, `prod`) |
| `old` | for `modify` | Current value, for rollback |
| `does` | yes | What it controls |
| `src` | no | Document section |
| `removed` | no | Why it was dropped |

A new feature should usually get a switch that starts off in production.

`backend.risks[]`: one-line warnings for developers: concurrency, duplicate
submits, things that can only happen once, old data. `text`, plus `apis[]`
when it belongs to specific APIs; risks without `apis` are listed on their own.

## release

Release steps the script cannot work out. The script adds the SQL steps,
config steps, and their rollbacks by itself; never write those.

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | `R1`, `R2`, … |
| `stage` | yes | `before`, `deploy`, `after` (what to watch once live), `rollback` (fastest first) |
| `type` | yes | `deploy` (a service), `config`, `other` |
| `text` | yes | One sentence; put names in backticks |
| `detail` | no | More explanation |
| `verify` | no | How to tell it is done |
| `src` | no | Document section |
| `removed` | no | Why it was dropped |

Do not list tests, frontend releases, or business chores such as menu
permissions.

## questions

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | `Q01`, `Q02`, … |
| `priority` | yes | `P0`: cannot start, or would build it wrong (data, money, status). `P1`: affects details. `P2`: can be settled during development |
| `status` | yes | See below |
| `title` | yes | The question in one plain sentence |
| `quotes[]` | yes | At least one: `src` and the exact `text` from the document; mark a gap with `…`. While the question is open or decided, `check` warns when the text is no longer in that section, or over 150 units |
| `why` | yes | Why this is a question |
| `affects[]` | for `P0` | Feature or API IDs it blocks; list the narrowest |
| `options[]` | yes | 2–3 answers someone can pick as they are: `key`, `text`, `reason` (the cost), `recommended` (at most one) |
| `owner` | no | Who decides |
| `answer` | when answered | `choice`, `note` (the person's own words), `at` (date), `by` (who) |
| `superseded_by` | when superseded | The question that replaces it |

| `status` | Meaning | Next |
| --- | --- | --- |
| `open` | Asked | Wait for an answer |
| `decided` | Answer written back | Fix every rule, API, table and release item it affects |
| `applied` | Everything affected is fixed; no `ask` rule points to it | Done |
| `superseded` | The answer was overturned | Open a new question and point to it; never edit the old answer |

## changes

Change notes for people, kept as an append-only log: add new entries at the
top, never edit or delete old ones. The script knows which version added each
entry, so a send shows every note since that reader's last copy.

| Field | Required | What |
| --- | --- | --- |
| `type` | yes | `add`, `modify` or `remove` |
| `text` | yes | One change per line, in words the readers of the changed pages use; start with the feature or API ID it is about. Table and column names go in `refs`, not here: the team notice copies this text as it is. Field names the frontend reads may stay |
| `refs[]` | yes | Every ID, table name or config key the change touches. `send` checks that each difference it finds is covered by some entry's `refs` |
| `src` | no | Document section, when the document caused it |

## confirmations

When `check` reports a `confirm`-level issue, ask the user, then record the
answer here so it is not asked again.

| Field | Required | What |
| --- | --- | --- |
| `code` | yes | The issue's `code` |
| `where` | yes | The issue's `where` |
| `note` | yes | What the user said |
| `at` | yes | Date |

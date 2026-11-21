# Questions: writing them, applying answers

A question is anything the document leaves unclear, contradicts, or that
clashes with the code. Finding them is your own judgement; this file only
says how to write them down and what to do with the answers. You never
decide them: the product owner picks an answer on the brief.

Leave out what is yours to decide (names, where code goes, which library)
and what the code can tell you: look that up.

## Writing one

- `title`: one plain sentence a product owner can answer without reading
  code. One decision per question; split bundles.
- `quotes`: the exact sentences that raise it. This is the only place that
  copies document text.
- `why`: what is missing or what contradicts what.
- `options`: 2–3 answers that can be picked as they are, each with `reason`,
  its cost (effort, user experience, risk). Mark at most one `recommended`.
  Never "to be discussed" or "other".
- `priority`: `P0` if development cannot start or would build the wrong
  thing (data, money, status); `P0` needs `affects`, the narrowest feature or
  API IDs it blocks, which the brief turns into "can start, except …".
  `P1` affects details; `P2` can be settled during development.
- In the analysis, every rule the question leaves open is an `ask` rule with
  `q`, and every flow step that waits for it has `q`.

## When answers arrive

The user pastes the text from the brief's "copy answers" button (one line per
question, such as `Q01 选 A：…`, with an optional note under it) or tells you.

1. **Record.** On each question write `answer`: `choice` (the option key),
   `note` (the person's own words, unchanged), `at` (today), `by` (who
   decided; if the user does not say, the user). Set `status` to `decided`.
   An answer that matches no option: `choice` is `other`, the words go in
   `note`.
2. **Apply.** Every `ask` rule pointing to it becomes a `prd` rule with `q`
   (and `src` once the document says it too), or goes away if the answer makes
   it moot. Update the flows, APIs, tables, configs and release items the
   answer touches. When nothing points to it any more, set `status` to
   `applied`.
3. **Note it.** Add a `changes` entry at the top: what was decided, with
   `refs` listing the question and every ID you changed.
4. **New questions** the answer raises: add them.
5. `check`, `render`, and tell the user which items changed.

An answer that overturns an earlier one: leave the old question and its
answer as they are, set its `status` to `superseded` with `superseded_by`
pointing to a new question that carries the new answer.

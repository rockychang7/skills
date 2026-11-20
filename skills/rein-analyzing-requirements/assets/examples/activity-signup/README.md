# Example: activity signup (made up)

A complete, made-up requirement used by `req.py example` and by the tests.
Copy the shape, never the content.

A scenic area lets visitors sign up for its events in a mini program; staff
manage signups in a web admin. Generated files are in Chinese (`zh-CN`).

## Files

| File | What it is |
| --- | --- |
| `doc-v1.md` | Requirement document, version V1.0-1112 |
| `doc-v2.md` | Requirement document, version V1.2-1117 |
| `analysis-v3.json` | Analysis version 3, built on doc v1 |
| `analysis-v10.json` | Analysis version 10, built on doc v2 |
| `frontend.json` | Frontend guide source, matching analysis v10 |
| `openapi.json` | API description the frontend guide's fields come from, matching analysis v10 |

## Timeline

| Date | Event |
| --- | --- |
| 11-12 | Doc v1 read. Analysis v1 to v3 written; Q02 answered on 11-14. |
| 11-15 | **Send 1**: analysis v3 and the frontend guide go to the frontend team. |
| 11-15 | The test environment runs the table SQL of analysis v3. |
| 11-16 | Q03 answered. |
| 11-17 | Doc v2 arrives: §2.3 (export) moves to §5, §3.4 now answers Q01, §3.6 (waitlist) is new. Q05 overturns Q02. |
| 11-18 | **Send 2**: analysis v10 and the updated frontend guide. |

## What this example shows

- Two flows (`P1` sign up, `P2` cancel and refill) with decisions, labelled
  branches and end steps; v3 → v10 adds the waitlist branch and the refill steps.
- Append-only change notes: the two entries from v3 are still at the bottom of
  v10's `changes`; everything above them was added after send 1.
- A removed feature and API (`B03`, `B3`) keep their IDs with `removed`.
- Question states: `open` (Q04, Q06), `applied` (Q01, Q03, Q05),
  `superseded` (Q02 → Q05). `ask` rules turn into `prd` rules once answered.
- Table patches: the test environment ran v3, so v10's later table changes are
  appended to `patches`, while `sql` stays the full latest statement.
- An expand-then-contract rename (`quota` → `max_quota`): both names live side
  by side; dropping the old one is listed in `out_of_scope` with a date.

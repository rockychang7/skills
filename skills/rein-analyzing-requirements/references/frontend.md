# The frontend guide file (frontend.json)

`frontend.json` feeds the frontend API guide. Write only how each API is
used. Paths, parameters, response fields and types come from the API
description (OpenAPI), filled in by the script through each API's `contract`.
API names and kinds come from the analysis by ID.

Write it once the API's inputs and outputs exist in code; the logic can still
be unfinished. For a complete sample run `req.py example frontend`.

Store the API description with `req.py contract --req <name> --openapi <file
or URL>` (Spring Boot with springdoc: `/v3/api-docs`; FastAPI:
`/openapi.json`). Run it again
whenever the APIs change: each new copy is a version, and the guide marks
field changes against the copy an earlier version used, and lists what
breaks old frontend code (a field going away or removed, a new type, a new
required parameter, new values). `contract` and `check --frontend` report a
`contract` the description does not have (`frontend.op-missing`).

## Contents

- [Top level](#top-level)
- [clients](#clients)
- [apis](#apis)
- [guides](#guides)
- [error_codes](#error_codes)
- [changes](#changes)

## Top level

| Field | Required | What |
| --- | --- | --- |
| `format` | yes | Always `1` |
| `conventions[]` | no | Rules shared by every client: the response wrapper, field naming, time format |
| `clients[]` | yes | One item per client, IDs matching the analysis `clients` |
| `error_codes[]` | no | Every error code the frontend should handle, all clients in one table |
| `changes[]` | no | Change notes, same rules as in the analysis |

## clients

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | A `clients` ID from the analysis |
| `name` | yes | The client's real name in this project |
| `status` | yes | Integration status: `todo` (not started), `doing` (in progress), `done` |
| `conventions[]` | no | Rules for this client only: headers, login token, app ID |
| `flow.nodes[]` | yes | One per page or dialog: `id`, `name`, `calls[]` (API IDs called there) |
| `flow.edges[]` | no | "Tap this, go there": `from`, `to`, `label`; add `back: true` for returning to an earlier page |
| `apis[]` | yes | See below |
| `guides[]` | no | Display rules as tables, see below |

## apis

Each API appears once, under the client it belongs to in the analysis. A page
of another client that calls it lists the ID in its `calls`.

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | The API ID from the analysis |
| `contract` | yes | `METHOD /path` of the operation in the API description, e.g. `POST /activity/signup` |
| `change` | for `modify` | What changed in this API this time |
| `facts[]` | yes | Key facts as `k`/`v` pairs: when it is called, login, paging, limits |
| `frontend[]` | yes | What the frontend must do: empty states, when a button is disabled, when to refresh, how to react to errors |
| `example` | yes | A realistic response. Make one up from the response schema first; replace it with a real (masked) response once it runs in a test environment |
| `fields` | only without an API description | Hand-written `params[]` and `response[]` (`name`, `type`, `required`, `desc`, nested `children[]`), copied from the code, never guessed |
| `removed` | no | Why it was dropped; the other fields can go |

If the API description and the requirement disagree (the requirement says a
field is returned, the code does not return it), do not edit around it: add a
question to the analysis.

## guides

| Field | Required | What |
| --- | --- | --- |
| `id` | yes | `G1`, `G2`, …, unique in the file |
| `title` | yes | What it explains |
| `head[]` | yes | Column titles |
| `rows[][]` | yes | Table rows |
| `notes[]` | no | Remarks under the table |

## error_codes

| Field | Required | What |
| --- | --- | --- |
| `code` | yes | The code as the API returns it |
| `msg` | yes | The message the API returns |
| `handle` | yes | What the frontend does when it gets it |

## changes

Same as the analysis `changes`: append-only, newest first, one change per
line, `refs[]` listing the API and guide IDs it touches. Breaking changes
(renamed, removed or retyped fields; optional becoming required) are detected
from the API descriptions and flagged by the script; still describe them here.

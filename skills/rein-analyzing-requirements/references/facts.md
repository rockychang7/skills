# Reading the code and the document

If `.req-profile.json` names a `facts` file, read it first: it says where
this project keeps what you need. Otherwise find things your own way.

- Only read: run no write queries, migrations or deploys.
- What you cannot find or see becomes a question; never guess. In `online`,
  say what you could not check.
- A link you cannot open (login, permissions): ask the user to export the
  document as Markdown or text.
- Images that explain what gets built (screens, flow charts, tables drawn as
  images): save them in `<requirement folder>/source/img/`, look at each,
  and list them in `prototypes.images`.
- `meta.code_commit`: `branch@short-sha`, e.g. `dev@1a2b3c4`; add `+changes`
  when the working tree has uncommitted changes; `none` outside git.
- The frontend guide later needs the API description (OpenAPI), from the
  running service or the code.

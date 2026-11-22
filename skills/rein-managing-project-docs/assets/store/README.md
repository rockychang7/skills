# __NAME__: documents kept out of project repositories

This is a private store. It holds the documents each project decided to keep out of its own repository (the internal
docs, decision records, work folders and notes set to "store" for that project). The skill `rein-managing-project-docs`
created it; it holds only its owner's documents. The conventions and the tool live in the skill, and upgrading the
skill never touches this repository.

- `projects.json`: the registry. Group rules, and one entry per project: how it is recognized, which types stay in its
  repository (`in_repo`), files let through on purpose (`allow`), or `skip` for projects with their own rules.
- `projects/<project>/`: the types this project keeps here, shaped like the repository's `docs/`: `internals/`,
  `decisions/`, `work/`, `notes/`.
- The full conventions (types, names, status, what to do when out of date): `references/conventions.md` in the skill.
- Checking: `docs.mjs check --store` here; `docs.mjs check` inside a project.

Never put here: passwords, tokens, private keys; data the company does not allow out (query results, server logs,
customer information). A project folder that must stay on this computer and never be pushed goes in `.gitignore`.

On another computer: clone this repository, install the skill `rein-managing-project-docs`, and tell the agent
"connect this computer to my store at <path>".

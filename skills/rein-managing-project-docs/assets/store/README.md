# __NAME__: backups of project documents

This is a private store. It holds a copy, with history, of each project's documents that are not committed to the
project's own repository (its `docs/process/` folder, or single files kept out of it). The skill
`rein-managing-project-docs` created it; it holds only its owner's documents. The conventions and the tool live in the
skill, and upgrading the skill never touches this repository.

**Do not edit the documents here.** Each project's `docs/process/` is the original; `docs.mjs backup` copies it here, one
way, and commits. An edit made here gets overwritten by the next backup (it stays in this repository's history).

- `projects.json`: the registry. Group rules, and one entry per project: how it is recognized, whether it commits
  `docs/process/` (`commit`), files let through on purpose (`allow`), or `skip` for projects with their own rules.
- `projects/<project>/`: the copy of that project's uncommitted documents, shaped like its `docs/process/`.
- The full conventions: `references/conventions.md` in the skill.
- Checking: `docs.mjs check --store` here; `docs.mjs check` inside a project.

Never put here: passwords, tokens, private keys; data the company does not allow out (query results, server logs,
customer information). A project folder that must stay on this computer and never be pushed goes in `.gitignore`.

On another computer: clone this repository, install the skill `rein-managing-project-docs`, tell the agent "connect
this computer to my store at <path>", then in each project run `docs.mjs init` and `docs.mjs restore`.

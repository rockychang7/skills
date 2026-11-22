# Skills

English | [简体中文](./README.zh-CN.md)

A personal collection of reusable agent skills — mostly workflow and tooling skills that I use across projects. Skills follow the [Agent Skills](https://agentskills.io/specification) format and can be installed with the [skills](https://github.com/vercel-labs/skills) CLI, listed on [skills.sh](https://www.skills.sh/).

## Install

```bash
# Install all skills
npx skills add rockychang7/skills

# List available skills without installing
npx skills add rockychang7/skills --list

# Install a specific skill
npx skills add rockychang7/skills --skill <skill-name>

# Update installed skills
npx skills update
```

## Available Skills

| Skill | Description |
| --- | --- |
| [rein-analyzing-requirements](./skills/rein-analyzing-requirements/SKILL.md) | Turns a product requirement document into an analysis checked against the code, then generates the requirement brief, backend plan, table SQL, release checklist and frontend API guide. When the requirement changes, marks what changed since each reader's last copy and drafts the team notice. Output in Chinese or English. Needs Python 3.9+ (standard library only) |
| [rein-managing-project-docs](./skills/rein-managing-project-docs/SKILL.md) | Gives every project the same kinds of documents with the same names (internal docs, decision records, one folder per piece of work with its plan and test record, notes), and keeps each kind in the project repository or in a private store outside all projects, as you decide per project or per group of projects. Sets up the store, registers projects, moves documents between the two sides, wraps up finished work, and checks for misplaced or misnamed files. Installs a short global rule for Claude Code and Codex. Needs Node.js 18+ (no dependencies) |

## Repository Structure

```text
.
├─ skills/                    # All published skills live here
│  └─ <skill-name>/
│     ├─ SKILL.md             # Required: metadata + instructions
│     ├─ references/          # Optional: docs and output templates
│     ├─ scripts/             # Optional: executable helpers
│     └─ assets/              # Optional: static resources
├─ template/
│  └─ SKILL.template.md       # Starting point for a new skill
├─ README.md
├─ README.zh-CN.md
└─ LICENSE
```

## Adding a Skill

1. Create `skills/<skill-name>/` and copy `template/SKILL.template.md` into it as `SKILL.md`.
2. Fill in the frontmatter:
   - `name` — lowercase letters, numbers and single hyphens only, max 64 chars, **must match the folder name**.
   - `description` — what the skill does and when to use it, max 1024 chars. Include trigger keywords.
3. Keep `SKILL.md` under ~500 lines; move long material into `references/`.
4. Check that the CLI can discover it locally:

   ```bash
   npx skills add . --list
   ```

5. Add a row to the **Available Skills** table in both READMEs, then commit and push.

Once the repository is public on GitHub, skills appear on [skills.sh](https://www.skills.sh/) automatically after they are installed via `npx skills add rockychang7/skills`.

## License

[MIT](./LICENSE)

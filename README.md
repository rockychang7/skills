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
| [rein-managing-project-docs](./skills/rein-managing-project-docs/SKILL.md) | Keeps every project's documents under `docs/`, named the same way everywhere. The project's own documents (`AGENTS.md`, `CLAUDE.md`, `docs/ARCHITECTURE.md`, `docs/CONVENTION.md`) get fixed names, empty skeletons on request and a "where documents are" section, but their content stays yours. Everything made while working with an agent (plans, test records, throwaway scripts and data, mockups, explainer pages, decisions, notes; any format) goes in `docs/process/`; you decide per project or group whether it is committed, and when it is not, git ignores it on your computer and the skill backs it up, one way, to a private store. Ships HTML page templates for explainers, test records and research. Installs a short global rule for Claude Code and Codex. Needs Node.js 18+ (no dependencies) |

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

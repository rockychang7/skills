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
| _None yet_ | |

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

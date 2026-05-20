# Personal Skills Collection

English | [简体中文](./README.zh-CN.md)

This repository is a personal collection of reusable AI / agent skills. It is meant to archive, organize, and maintain the skills I repeatedly use across different task scenarios, so they can be reused, refined, and expanded over time.

## What Is a Skill

A `skill` is a reusable set of instructions and constraints for a specific type of task. It usually defines:

- when it should be used
- trigger conditions
- workflow
- output requirements
- reference templates or supporting materials

In this repository, a skill usually contains:

- `SKILL.md`: the main specification file that defines the skill's responsibility, rules, workflow, and output format
- `references/`: optional supporting materials such as templates, examples, and supplemental notes

## Project Positioning

This project is a personal skill collection. The goal is to capture stable, reusable capabilities by scenario instead of rebuilding prompts or workflows from scratch every time.

It is mainly used to:

- preserve reusable AI / agent workflows
- standardize how common tasks are handled and structured
- keep reusable constraints, templates, and checklists together
- make skills easier to search, reuse, and expand over time

## Current Skills

- `api-html-generate`: generates or updates standalone HTML pages for API documentation and API change notes
- `code-review`: performs structured code reviews with a focus on findings, risks, compliance, and review conclusions
- `test-workflow`: supports testing work such as test-level decisions, scenario design, test additions, execution, and result summaries

## Directory Structure

```text
skills/
├─ api-html-generate/
│  ├─ SKILL.md
│  └─ references/
├─ code-review/
│  ├─ SKILL.md
│  └─ references/
├─ test-workflow/
│  ├─ SKILL.md
│  └─ references/
├─ .gitignore
├─ LICENSE
├─ README.md
└─ README.zh-CN.md
```

## Usage

1. Find the skill directory that matches your task.
2. Read its `SKILL.md` first to understand the scope, workflow, and output requirements.
3. If the directory includes `references/`, use those templates or supporting materials as needed.
4. Treat the files inside each skill directory as the source of truth for that skill.

## Maintenance Principles

- prefer reusable content over one-off notes
- keep the structure stable so new skills can be added easily
- keep documentation direct, clear, and searchable
- when adding a new skill, include the main specification and any necessary references

## License

This repository is licensed under the `MIT` License.

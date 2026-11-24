---
name: rein-writing-changelogs
description: "Writes the release notes for a new version of a project into CHANGELOG.md, in one fixed format, for the people who use it, and prepares the same text for the GitHub Release. Use when releasing a version, tagging, or asked to write or update a changelog or release notes, even when the user only says \"tag v1.4\" or \"发版\". Not for commit messages, pull request descriptions or project documentation."
license: MIT
compatibility: "Requires Node.js 18+ (no dependencies) to run scripts/changelog.mjs."
metadata:
  author: rockychang7
  version: "0.1.0"
---

# Writing changelogs

A changelog entry tells the people who use a project what changed for them in one version, and what they have to
do to upgrade.

Write the entry in English unless the user asks for Chinese. When a file's older entries are in Chinese or in
another format, leave them as they are and write the new entry in English.

## Done when

- `changelog.mjs check` reports no problems for the new version.
- The user saw the entry and the Release text.
- No tag, push or GitHub Release was made before the user said yes to it.

## Running the script

`changelog.mjs` below stands for `node <this skill's folder>/scripts/changelog.mjs`, run from the project root.

- `check [file]`: checks the newest version's entry (`--all`: every version). Each problem names the line and the
  fix. Exit 0 no problems, 1 problems, 2 wrong usage or no file.
- `print <version> [file]`: prints that version's notes without the heading. Use it for the Release text, so the
  Release and the file never differ.

## The entry

```markdown
# Changelog

## 1.4.0 - 2026-11-24

### Breaking Changes

- <what changed>. To upgrade: <what the user does>.

### Added

- ...

### Fixed

- ...

### Changed

- ...

### Verification

- ...
```

- Newest version first; the date is the release date.
- Sections in this order, only those with items. Verification only when tests were run for this release: say what
  ran and on what.
- In Chinese, the sections are 不兼容改动, 新增, 修复, 调整, 验证.
- Each item says what a user notices, in a sentence or two. Restructuring users cannot see gets one line under
  Changed, or none.
- Every breaking change says how to upgrade: the commands, the files to edit, what is lost.
- No commit hashes, commit lists or install instructions; the commits are the material, not the text.

## Steps

1. **Find what changed**: the commits and the diff since the last tag (`git describe --tags --abbrev=0`). The
   version is what the user said, or else the one in the project's version file. With no tag to start from, or no
   version, ask.
2. **Write the entry** at the top of `CHANGELOG.md`, below `# Changelog`. Create the file with that heading when
   there is none.
3. **Run `check`** and fix what it reports.
4. **Show the user** the entry and the `print` output, and say which tag, push and Release you would make. After
   their yes: tag with the project's existing tag style (`v1.4.0` when earlier tags have the `v`), push, and create
   the Release where the project's earlier Releases are, which for a private source is often a separate public
   repository: `gh release create <tag> -R <owner/repo> --title <tag> --notes-file <file with the print output>`.

When the user asks to bring the older entries into this format, rewrite them all and run `check --all`.

## When to stop and ask

- Before a tag, a push or a GitHub Release: other people see them.
- When there is no tag to start from, or the version is neither given nor in the project.

## Pitfalls

Seen in earlier releases of the user's projects:

| Situation | What to do |
| --- | --- |
| The Release text was a list of commits | Write the entry; a commit list tells users nothing they can act on |
| The Release said only how to install | Every Release carries the entry: what changed is the reason to read it |
| One project's releases switched between English and Chinese | English unless the user asks for Chinese, every release |

## Output

Tell the user the version, the file path, the check result, and the entry itself; then the tag, push and Release
you are waiting to make, or the links to the ones made.

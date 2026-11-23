# Checklist: changing whether a project commits docs/process/

What a script can check is left to `docs.mjs check`. This list covers what a person (or the agent) has to look at.
Whether the repository itself is visible to others is a repository setting; "public" below means anyone besides the
user can see it.

## Not committed → committed (documents go into the repository from now on)

- [ ] Read every file under `docs/process/` that will be committed. None of these is in it: accounts and passwords,
      internal addresses and machine names, names of customers and colleagues, prices and costs, unfixed security
      weaknesses, opinions about people. Any of them: show the user those lines and ask whether to delete, rewrite, or
      keep that one file out (add it to `.git/info/exclude`; the backup keeps taking it).
- [ ] No hidden files the user did not mean to share (`git status --ignored docs/process/` after the switch shows them).
- [ ] `docs.mjs init --commit` (it removes `docs/process/` from `.git/info/exclude`).
- [ ] `docs.mjs check` shows no ✗; commit in the project repository.
- [ ] The store's copy is no longer updated (only files kept out by hand are). Leave it; it is history.

## Committed → not committed (documents leave the repository from now on)

- [ ] No store yet and the user wants a backup: create one first (skill section 1).
- [ ] `docs.mjs init --no-commit`, then `git rm -r --cached docs/process/` (the files stay on disk) and commit that.
- [ ] `docs.mjs backup`.
- [ ] See which commits held them: `git log --oneline -- docs/process/`.
- [ ] Those commits were **never pushed**: history can be cleaned (`git filter-repo --invert-paths --path docs/process/`)
      before pushing. The user decides.
- [ ] Those commits **were pushed where others can see them**: treat the content as leaked.
  - [ ] Passwords or tokens in it: change them first.
  - [ ] Cleaning history is the user's call: it rewrites every commit id and needs a force push; clones, forks and
        cached pages elsewhere cannot be cleaned.

## One document in a project that commits docs/process/: keep it out

- [ ] Add its path to `.git/info/exclude`. Already committed: `git rm --cached <path>` and the history steps above.
- [ ] `docs.mjs backup` (it backs up whatever git ignores under `docs/process/`).

## A whole project goes private (the repository becomes private)

- [ ] Change the repository setting; documents do not need to move.
- [ ] Clones and forks made while it was public cannot be taken back: treat what was public as public for good.
- [ ] To have documents follow the code from now on: the first list above.

## A whole project goes public

Not covered by this version of the skill. At the very least, before changing the setting: search the whole history for
words that must not be public (`git log --all -S "<word>" --oneline`), run a secret scanner such as gitleaks over all
history, and read rule files, commit messages and branch names. When history has problems, publishing a fresh
repository with only the current files is the safest way.

## Now and then (say, monthly)

- [ ] `docs.mjs check --store`: projects with changes not backed up; store commits not pushed. A store that lives on
      one disk is lost with it.
- [ ] `docs.mjs check` in active projects: work folders open for over a month.

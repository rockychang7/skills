# Checklist: moving documents between the project repository and the store

What a script can check is left to `docs.mjs check`. This list covers what a person (or the agent) has to look at.
Below, "public" means in the project repository and "private" means in the store; whether the repository itself is
visible to others is a repository setting.

## One document: private → public

- [ ] Read it all. None of these is in it: accounts and passwords, internal addresses and machine names, names of
      customers and colleagues, prices and costs, unfixed security weaknesses, opinions about people.
- [ ] Move it to the project's `docs/<same path>`, same name.
- [ ] The type is kept in the store for this project: add the file's repository path to `allow` in the project's
      registry entry.
- [ ] No link in it points into the store (documents in the repository never link to the store).
- [ ] `docs.mjs check` shows no ✗.
- [ ] Commit on both sides: an addition in the project repository, a deletion in the store.

## Changing an arrangement: a type moves into the repository from now on (say, decision records)

- [ ] Add the type to `in_repo` in the project's registry entry (`docs.mjs init --in-repo <new arrangement>`).
- [ ] Run every existing file of that type through the list above (skip the `allow` step). Any the user does not want
      public stays in the store; the rest are unaffected.

## One document: public → private

- [ ] Move it to the store's `projects/<project>/<same path>`; commit the deletion in the project repository.
- [ ] See which commits it was in: `git log --oneline -- <path>`.
- [ ] Those commits were **never pushed**: history can be cleaned (`git filter-repo --invert-paths --path <path>`)
      before pushing. The user decides.
- [ ] Those commits **were pushed where others can see them**: treat the content as leaked.
  - [ ] Passwords or tokens in it: change them first.
  - [ ] Cleaning history is the user's call: it rewrites every commit id and needs a force push; clones, forks and
        cached pages elsewhere cannot be cleaned.

## A whole project: public → private

- [ ] Change the repository setting; documents do not need to move.
- [ ] Clones and forks made while it was public cannot be taken back: treat what was public as public for good.
- [ ] To have documents follow the code from now on: `docs.mjs init --in-repo all`, then move the store's documents
      into the project's `docs/`. Otherwise leave everything as it is.

## A whole project: private → public

Not covered by this version of the skill. At the very least, before changing the setting: search the whole history for
words that must not be public (`git log --all -S "<word>" --oneline`), run a secret scanner such as gitleaks over all
history, and read rule files, commit messages and branch names. When history has problems, publishing a fresh
repository with only the current files is the safest way.

## Now and then (say, monthly)

- [ ] `docs.mjs check --store`: misnamed files, wrong status, finished work not archived, work active for over a month.
- [ ] It says "uncommitted" or "not pushed": commit and push in the store. A store that lives on one disk is lost with it.

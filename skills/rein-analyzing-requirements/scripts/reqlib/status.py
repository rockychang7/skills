"""What is out of date in one requirement, and what to do about it (the status command).

Every finding is a `warn` issue whose hint says the next step; the result
fields describe the requirement as it is. Nothing is changed.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

import json

from . import diff as diffs
from . import render, sends, sql
from .check import check_analysis
from .output import issue, summarize

RUN = "req.py"


def _pages(folder: Path, state: dict[str, Any], analysis: dict[str, Any], latest: int | None,
           frontend: bool) -> list[dict[str, Any]]:
    """Every generated file the analysis needs, with its state: current, outdated, edited or missing."""
    texts = render.load_texts(state["lang"])
    names: list[tuple[str, str]] = []
    for page in render.pages_needed(analysis, frontend):
        if page not in render.READY:
            continue
        if page == "sql":
            names += [("sql", name) for name in sql.file_names(analysis, texts["files"]["sql"]).values()]
        else:
            names.append((page, texts["files"][page]))
    outputs = state.get("outputs") or {}
    rows = []
    for page, name in names:
        path = folder / "out" / name
        record = outputs.get(name) or {}
        if not path.is_file():
            how = "missing"
        elif render.file_hash(path.read_bytes()) != record.get("sha256"):
            how = "edited"
        elif latest is not None and record.get("v") != latest:
            how = "outdated"
        else:
            how = "current"
        rows.append({"page": page, "file": str(path), "state": how, "v": record.get("v")})
    return rows


def _frontend_at(folder: Path, version: dict[str, Any]) -> Any:
    path = folder / version["frontend"] if version.get("frontend") else None
    return json.loads(path.read_text(encoding="utf-8-sig")) if path and path.is_file() else None


def _sends(folder: Path, state: dict[str, Any], analysis: dict[str, Any], has_frontend: bool,
           last: dict[str, Any] | None, load_version: Callable[[int], dict[str, Any]]) -> tuple[list, list]:
    """The sends so far, and per reader group the changes since the copies it last received."""
    all_sends = state.get("sends") or []
    listed = [{"no": s["no"], "to": s["to"], "v": s["v"], "date": sends.short_date(s["at"]), "files": s["files"]}
              for s in all_sends]
    if not last or not all_sends:
        return listed, []
    by_v = {x["v"]: x for x in state.get("versions") or []}
    latest = load_version(last["v"])
    found = []
    for group in sends.GROUPS:
        behind = []
        for page in render.pages_needed(analysis, has_frontend):
            got = sends.last_copy(all_sends, group, page)
            if got is None or got["v"] == last["v"]:
                continue
            old = load_version(got["v"])
            if page == "frontend":
                moved = _frontend_at(folder, by_v.get(got["v"], {})) != _frontend_at(folder, last) or \
                    by_v.get(got["v"], {}).get("contract_v") != last.get("contract_v")
            else:
                moved = bool(sends.page_changes(page, old, latest)) or bool(diffs.new_notes(old, latest))
            if moved:
                behind.append((page, got))
        if behind:
            oldest = min((got for _, got in behind), key=lambda s: (s["v"], s["no"]))
            found.append(issue(
                "status.unsent", "warn",
                "The %s team has changes it has not received: %s. Its copies are from send %d (%s, version %d); "
                "the latest version is %d." % (group, ", ".join(p for p, _ in behind), oldest["no"],
                                               sends.short_date(oldest["at"]), oldest["v"], last["v"]),
                hint="When the user wants to send them: `send --req %s --to %s --preview`, then send."
                % (state.get("name", ""), group), where="sends"))
    return listed, found


def report(
    folder: Path,
    state: dict[str, Any],
    analysis: dict[str, Any] | None,
    envs: list[str],
    doc_text: str,
    load_version: Callable[[int], dict[str, Any]],
    frontend: Any = None,
    contract_v: int | None = None,
    follows: int | None = None,
    source_issues: list[dict[str, str]] | None = None,
) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """(fields, issues) for the status result. `frontend` is frontend.json (None: not written);
    `follows` is the document version the analysis follows, `source_issues` what is wrong with it."""
    issues: list[dict[str, str]] = []
    docs = state.get("docs") or []
    versions = state.get("versions") or []
    last = versions[-1] if versions else None
    fields: dict[str, Any] = {"document": {"v": len(docs), "file": docs[-1]["file"] if docs else None}}

    if analysis is None:
        fields["analysis"] = {"exists": False}
        issues.append(issue("status.no-analysis", "warn", "analysis.json has not been written yet.",
                            hint="Write it by references/analysis.md; see the format with: %s example" % RUN,
                            where="analysis.json"))
        return fields, issues

    saved = last is not None and last.get("sha256") == render.draft_fingerprint(analysis, frontend, contract_v)
    fields["analysis"] = {"exists": True, "version": last["v"] if last else None, "rendered": saved,
                          "doc_v": follows}
    if not saved:
        issues.append(issue(
            "status.not-rendered", "warn",
            "The analysis, frontend.json or the API description changed since the last render." if last
            else "analysis.json has never been rendered.",
            hint="Run check, then render. Until then the pages show %s." % (
                "version %d" % last["v"] if last else "nothing"),
            where="analysis.json"))
    if follows is not None and follows < len(docs):
        issues.append(issue(
            "status.doc-newer", "warn",
            "Document version %d is newer than the one the analysis follows (%d)." % (len(docs), follows),
            hint="`refresh --req %s` lists what changed and what it affects. Tell the user and wait for a "
            "go-ahead, then update the analysis (references/changes.md) and render." % state.get("name", ""),
            where="meta.source_v"))

    questions = [q for q in analysis.get("questions") or [] if isinstance(q, dict)]
    open_qs = [q for q in questions if q.get("status") == "open"]
    decided = [q.get("id") for q in questions if q.get("status") == "decided"]
    fields["questions"] = {"open": len(open_qs), "open_p0": [q.get("id") for q in open_qs if q.get("priority") == "P0"],
                           "decided": decided}
    if decided:
        issues.append(issue(
            "status.decided", "warn", "Answered but not applied yet: %s." % ", ".join(decided),
            hint="Fix every rule, API, table and release item each one affects, then set its status to `applied` "
            "(references/questions.md, \"When answers arrive\").", where="questions"))

    pages = _pages(folder, state, analysis, last["v"] if last else None, frontend is not None)
    fields["pages"] = pages
    for p in pages:
        name = Path(p["file"]).name
        if p["state"] == "missing":
            issues.append(issue("status.page-missing", "warn", "%s has not been generated." % name,
                                hint="Run render.", where="out/" + name))
        elif p["state"] == "edited":
            issues.append(issue("status.page-edited", "warn", "%s was changed by hand after it was generated." % name,
                                hint="Ask the user whether the hand edits matter: copy what matters into "
                                "analysis.json, then render --force replaces the file.", where="out/" + name))
        elif p["state"] == "outdated" and saved:
            issues.append(issue("status.page-outdated", "warn",
                                "%s shows version %s; the latest is %d." % (name, p["v"], last["v"]),
                                hint="Run render.", where="out/" + name))

    environments = []
    if last:
        latest = load_version(last["v"])
        for env, ran in sql.env_rows(state, envs):
            to_run = None
            if ran is not None and ran < last["v"]:
                older = load_version(ran)
                to_run = 0
                for db in sql.databases(latest):
                    c = sql.catch_up(older, latest, db)
                    to_run += sum(len(stmts) for _, _, stmts in c["tables"]) + len(c["data"])
                if to_run:
                    issues.append(issue(
                        "status.env-behind", "warn",
                        "%s ran the SQL of version %d; %d statement(s) added since have not run there." % (env, ran, to_run),
                        hint="`steps --env %s` lists what %s still needs (version %d → %d); bring it there with "
                        "the tools at hand or tell the user. Once it is in place, record it with applied."
                        % (env, env, ran, last["v"]), where="applied.%s" % env))
            environments.append({"env": env, "ran": ran, "to_run": to_run})
    fields["environments"] = environments
    fields["sends"], unsent = _sends(folder, state, analysis, frontend is not None, last, load_version)
    issues += unsent

    found = [i for i in source_issues or [] if i["level"] != "warn"]  # being behind is reported above
    found += check_analysis(analysis, doc_text, envs, state["lang"]) + sql.problems(analysis, state, load_version)
    counts = summarize(found)
    fields["check"] = counts
    if counts.get("error") or counts.get("confirm"):
        issues.append(issue(
            "status.check-fails", "warn",
            "check reports %d error(s) and %d item(s) to confirm." % (counts.get("error", 0), counts.get("confirm", 0)),
            hint="Run check and fix them; render refuses until then.", where="analysis.json"))
    return fields, issues

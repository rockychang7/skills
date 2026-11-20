"""What each implemented command does. Parsing lives in cli.py."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

from . import example as ex
from . import openapi
from . import render
from . import sql
from .check import check_analysis, check_frontend
from .doc import duplicate_ids, parse_sections, read_doc
from .files import JsonProblem, read_json, write_text
from .output import Stop, finish, issue, note, summarize
from .settings import LANGS, Settings, guard_not_in_skill_folder, workspace_suggestions
from .status import report
from .steps import for_env
from .store import by_name, check_name, find, latest_doc, load_state, save_state

# How hints name the script; SKILL.md defines `req.py` as the full command.
RUN = "req.py"
ISSUE_LIMIT = 50


def _now() -> datetime.datetime:
    return datetime.datetime.now().replace(microsecond=0)


def _cwd() -> Path:
    return Path.cwd().resolve()


def cmd_new(args: argparse.Namespace) -> int:
    cwd = _cwd()
    guard_not_in_skill_folder(cwd)
    check_name(args.name)
    doc_path = (cwd / Path(args.doc).expanduser()).resolve()
    text, warnings = read_doc(doc_path)
    settings = Settings(cwd)

    workspace, workspace_from = settings.workspace(args.dir)
    if workspace is None:
        return finish(
            "new",
            [
                issue(
                    "workspace.not-set",
                    "confirm",
                    "No requirements folder is set yet, so nothing was created.",
                    hint="Ask the user once where requirement folders should go (suggestions below), then run "
                    "`config set workspace <path>` and run new again. A folder inside the project is saved "
                    "for this project only; one outside it is saved for all projects.",
                    where="workspace",
                )
            ],
            suggestions=workspace_suggestions(settings),
        )

    existing = by_name(workspace, args.name)
    if existing:
        return finish(
            "new",
            [
                issue(
                    "req.exists",
                    "warn",
                    "Requirement %r already exists; nothing was changed." % args.name,
                    hint="Ask the user: continue it (pass --req %s to later commands), or start a separate "
                    "requirement under another short name." % args.name,
                    where="--name",
                )
            ],
            id=existing[0].name,
            dir=str(existing[0]),
            exists=True,
        )

    lang, lang_from = settings.lang(args.lang)
    now = _now()
    req_id = "REQ-%s-%s" % (now.strftime("%Y%m%d"), args.name)
    folder = workspace / req_id
    doc_file = "source/doc-v1.md"
    write_text(folder / doc_file, text)
    save_state(
        folder,
        {
            "format": 1,
            "id": req_id,
            "name": args.name,
            "lang": lang,
            "created": now.isoformat(),
            "docs": [{"v": 1, "file": doc_file, "from": str(doc_path), "at": now.isoformat()}],
        },
    )

    sections = parse_sections(text)
    for dupe in duplicate_ids(sections):
        warnings.append(
            issue(
                "doc.duplicate-section",
                "warn",
                "Section §%s appears more than once in the document." % dupe,
                hint="src can only point to the first one; mention this to the user if it matters.",
                where=doc_file,
            )
        )
    return finish(
        "new",
        warnings,
        id=req_id,
        dir=str(folder),
        workspace=str(workspace),
        workspace_from=workspace_from,
        lang=lang,
        lang_from=lang_from,
        doc=doc_file,
        sections=["§%s %s" % (s.id, s.title) for s in sections],
        next=[
            "Read the whole document (%s) and every related image." % (folder / doc_file),
            "See the format: %s example" % RUN,
            "Write %s, in %s, citing sections as listed above." % (folder / "analysis.json", lang),
            "Then: %s check --req %s" % (RUN, args.name),
        ],
    )


def cmd_config_set(args: argparse.Namespace) -> int:
    cwd = _cwd()
    if not args.value.strip():
        raise Stop(issue("config.bad-value", "error", "The value is empty.", where="value"))
    if args.key == "workspace" or args.scope == "project":
        guard_not_in_skill_folder(cwd)
    settings = Settings(cwd)

    if args.key == "workspace":
        # The path decides where it is saved: a folder inside the project goes in
        # the project settings (relative, so it works for everyone); one outside
        # goes in the user settings, never in a file that may be committed.
        full = settings.resolve(args.value)
        scope = "project" if settings.inside_project(full) else "user"
        if args.scope and args.scope != scope:
            raise Stop(
                issue(
                    "config.scope-mismatch",
                    "error",
                    "%s is %s the project, so it is saved in the %s settings, not the %s settings."
                    % (full, "inside" if scope == "project" else "outside", scope, args.scope),
                    hint="Leave out --scope for workspace; the folder's location decides it.",
                    where="--scope",
                )
            )
        value = str(full)
    else:
        if args.value not in LANGS:
            raise Stop(issue("config.bad-value", "error", "Language %r is not supported." % args.value,
                             hint="Use one of: %s." % ", ".join(LANGS), where="value"))
        if not args.scope:
            raise Stop(issue("config.no-scope", "error", "Say where to save the language.",
                             hint="Add --scope project (this project) or --scope user (all projects).",
                             where="--scope"))
        scope, value = args.scope, args.value

    path, stored = settings.set_value(args.key, args.value, scope)

    after = Settings(cwd)
    effective, effective_from = after.workspace(None) if args.key == "workspace" else after.lang(None)
    issues = []
    if str(effective) != value:
        issues.append(
            issue(
                "config.shadowed",
                "warn",
                "Saved, but this project still uses %s from its %s settings, which come first."
                % (effective, effective_from),
                hint="To use the new value here too, remove %r from %s. Ask the user first: "
                "teammates may rely on it." % (args.key, after.profile_path),
                where=args.key,
            )
        )
    return finish("config set", issues, key=args.key, value=value, stored=stored, scope=scope, file=str(path),
                  effective=str(effective), effective_from=effective_from)


def _requirement(args: argparse.Namespace) -> tuple[Settings, Path, dict]:
    cwd = _cwd()
    guard_not_in_skill_folder(cwd)
    settings = Settings(cwd)
    workspace, _ = settings.workspace(args.dir)
    folder = find(workspace, args.req)
    return settings, folder, load_state(folder)


def _read_source(path: Path, missing_hint: str) -> object:
    """Read analysis.json or frontend.json; problems become analysis.missing, frontend.invalid, …"""
    try:
        return read_json(path, path.stem)
    except JsonProblem as e:
        if e.issue["code"].endswith(".missing"):
            e.issue["msg"] = "%s has not been written yet." % path.name
            e.issue["hint"] = missing_hint
        raise Stop(e.issue, exit_code=1, file=str(path))


def cmd_check(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    analysis_path = folder / "analysis.json"
    analysis = _read_source(analysis_path, "Write it first; see the format with: %s example" % RUN)
    if args.frontend:
        path = folder / "frontend.json"
        data = _read_source(path, "Write it first; see the format with: %s example frontend" % RUN)
        issues = check_frontend(data, analysis) + render.contract_issues(data, _contract(folder, state)[0])
    else:
        path = analysis_path
        doc = latest_doc(folder, state)
        sections = {s.id for s in parse_sections(doc.read_text(encoding="utf-8"))}
        issues = check_analysis(analysis, sections, settings.envs())
        issues += sql.problems(analysis, state, _version_loader(folder, state))
    return finish(
        "check",
        issues,
        limit=None if args.all else ISSUE_LIMIT,
        id=state.get("id", folder.name),
        file=str(path),
        summary=summarize(issues),
    )


def _version_loader(folder: Path, state: dict):
    """A function returning the saved analysis of a version; unknown versions stop the command."""
    files = {v["v"]: v["file"] for v in state.get("versions", [])}
    cache: dict = {}

    def load(v: int) -> dict:
        if v not in cache:
            if v not in files or not (folder / files[v]).is_file():
                have = ", ".join(str(n) for n in files) or "none yet"
                raise Stop(issue("version.missing", "error", "Analysis version %d is not saved." % v,
                                 hint="Saved versions: %s." % have, where="state.json"))
            cache[v] = json.loads((folder / files[v]).read_text(encoding="utf-8-sig"))
        return cache[v]

    return load


def _frontend(folder: Path, required: bool) -> object:
    """frontend.json, or None when it is not written and not required."""
    path = folder / "frontend.json"
    if not path.is_file() and not required:
        return None
    return _read_source(path, "Write it by references/frontend.md; see the format with: %s example frontend" % RUN)


def _contract(folder: Path, state: dict, v: object = None) -> tuple[object, object]:
    """(stored API description, its version): the latest, or version `v`; (None, None) when there is none."""
    contracts = state.get("contracts") or []
    found = [c for c in contracts if c["v"] == v] if v is not None else contracts[-1:]
    if not found:
        return None, None
    return json.loads((folder / found[0]["file"]).read_text(encoding="utf-8-sig")), found[0]["v"]


def _save_version(folder: Path, state: dict, analysis: object, raw: str, frontend: object = None,
                  frontend_raw: str = "", contract_v: object = None) -> tuple[dict, bool]:
    """Store the drafts as a new version unless they equal the latest one.

    A version is the analysis, plus frontend.json and the API description version when there are.
    """
    versions = state.setdefault("versions", [])
    digest = render.draft_fingerprint(analysis, frontend, contract_v)
    if versions and versions[-1].get("sha256") == digest:
        return versions[-1], False
    v = len(versions) + 1
    entry = {"v": v, "file": "versions/analysis-v%d.json" % v, "at": _now().isoformat(), "doc_v": len(state["docs"]),
             "sha256": digest}
    write_text(folder / entry["file"], raw)
    if frontend is not None:
        entry["frontend"] = "versions/frontend-v%d.json" % v
        write_text(folder / entry["frontend"], frontend_raw)
    if contract_v is not None:
        entry["contract_v"] = contract_v
    versions.append(entry)
    return entry, True


def cmd_render(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    analysis_path = folder / "analysis.json"
    analysis = _read_source(analysis_path, "Write it first; see the format with: %s example" % RUN)
    doc_text = latest_doc(folder, state).read_text(encoding="utf-8")
    load_version = _version_loader(folder, state)
    frontend = _frontend(folder, args.frontend)
    spec, contract_v = _contract(folder, state)
    issues = check_analysis(analysis, {s.id for s in parse_sections(doc_text)}, settings.envs())
    issues += sql.problems(analysis, state, load_version)
    if frontend is not None:
        issues += check_frontend(frontend, analysis) + render.contract_issues(frontend, spec)
    if any(i["level"] in ("error", "confirm") for i in issues):
        return finish("render", issues, limit=ISSUE_LIMIT, id=state["id"], rendered=False,
                      summary=summarize(issues))

    base, base_analysis = None, None
    if args.since is not None:
        if not any(v["v"] == args.since for v in state.get("versions", [])):
            have = ", ".join(str(v["v"]) for v in state.get("versions", [])) or "none yet"
            raise Stop(issue("render.bad-since", "error", "There is no analysis version %d." % args.since,
                             hint="Saved versions: %s." % have, where="--since"))
        base_analysis = load_version(args.since)
        base = {"kind": "version", "v": args.since}

    entry, created = _save_version(folder, state, analysis, analysis_path.read_text(encoding="utf-8-sig"), frontend,
                                   (folder / "frontend.json").read_text(encoding="utf-8-sig") if frontend is not None else "",
                                   contract_v)
    generated = entry["at"].replace("T", " ")[:16]
    wanted = list(args.only) if args.only else render.pages_needed(analysis, frontend is not None)
    if "frontend" in wanted and frontend is None:
        raise Stop(issue("frontend.missing", "error", "frontend.json has not been written yet.",
                         hint="Write it by references/frontend.md once the APIs exist in code.", where="--only"))
    texts = render.load_texts(state["lang"])
    making = [p for p in wanted if p in render.READY]
    not_yet = [p for p in wanted if p not in render.READY]
    # One SQL file per database; pages link to the first.
    sql_files = sql.file_names(analysis, texts["files"]["sql"])
    names = {p: texts["files"][p] for p in render.PAGES}
    if sql_files:
        names["sql"] = next(iter(sql_files.values()))
    # Each page lists the requirement's pages: the ones it needs, plus any generated earlier.
    exists = {p for p in render.PAGES if (folder / "out" / names[p]).is_file()}
    needed = render.pages_needed(analysis, frontend is not None)
    shown = [p for p in render.PAGES if p in needed or p in wanted or p in exists]
    linked = exists | set(making)
    files: list = []

    def write(page: str, name: str, content: str, **extra: str) -> None:
        result, page_issues = render.write_page(folder, name, content, state, entry["v"], args.force)
        files.append(dict(result, page=page, **extra))
        issues.extend(page_issues)

    for page in making:
        pages = render.page_list(texts, shown, linked, page, names)
        if page == "brief":
            write(page, names[page], render.brief_html(analysis, state, entry["v"], generated, doc_text, texts, base,
                                                       base_analysis, pages))
        elif page == "plan":
            write(page, names[page], render.plan_html(analysis, state, entry["v"], generated, texts, base,
                                                      base_analysis, pages))
        elif page == "frontend":
            base_frontend = base_spec = None
            if base is not None:
                at = [v for v in state["versions"] if v["v"] == args.since][0]
                if at.get("frontend") and (folder / at["frontend"]).is_file():
                    base_frontend = json.loads((folder / at["frontend"]).read_text(encoding="utf-8-sig"))
                base_spec = _contract(folder, state, at["contract_v"])[0] if at.get("contract_v") else None
            write(page, names[page], render.frontend_html(
                analysis, frontend, state, entry["v"], generated, texts, spec, contract_v, base, base_analysis,
                base_frontend, base_spec, pages))
        elif page == "release":
            rows = sql.release_rows(analysis, state, settings.envs(), entry["v"], load_version, texts, sql_files)
            write(page, names[page], render.release_html(
                analysis, state, entry["v"], generated, texts, sql.env_rows(state, settings.envs()), rows,
                base, base_analysis, pages))
        else:
            for db, name in sql_files.items():
                content = sql.build(analysis, db, entry["v"], generated, state["id"], state, settings.envs(),
                                    load_version, texts)
                write(page, name, content, db=db)
    save_state(folder, state)
    if not_yet:
        note("Not generated yet (coming in later versions of this skill): %s." % ", ".join(not_yet))
    return finish("render", issues, limit=ISSUE_LIMIT, id=state["id"], rendered=True, version=entry["v"],
                  new_version=created, compared_with=base, files=files, not_yet=not_yet)


def cmd_contract(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    source = args.openapi or settings.openapi()
    if not source:
        raise Stop(issue("contract.no-source", "error", "Where is the API description?",
                         hint="Pass --openapi <file or URL>, or ask the user and save it as `openapi` in "
                         ".req-profile.json (Spring Boot with springdoc: http://localhost:8080/v3/api-docs).",
                         where="--openapi"))
    if not source.startswith(("http://", "https://")):
        source = str(settings.resolve(source))
    spec = openapi.load(source)
    digest = render.fingerprint(spec)
    contracts = state.setdefault("contracts", [])
    if contracts and contracts[-1].get("sha256") == digest:
        entry, created = contracts[-1], False
    else:
        v = len(contracts) + 1
        entry = {"v": v, "file": "source/openapi-v%d.json" % v, "at": _now().isoformat(), "from": source,
                 "sha256": digest}
        write_text(folder / entry["file"], json.dumps(spec, ensure_ascii=False, indent=2) + "\n")
        contracts.append(entry)
        created = True
        save_state(folder, state)
    frontend = _frontend(folder, False)
    issues = render.contract_issues(frontend, spec) if frontend is not None else []
    note("Render again so the frontend guide takes its fields from this description.")
    return finish("contract", issues, id=state["id"], v=entry["v"], new_version=created, file=str(folder / entry["file"]),
                  operations=len(openapi.operations(spec)))


def cmd_status(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    workspace, chosen_by = settings.workspace(args.dir)
    try:
        analysis = read_json(folder / "analysis.json", "analysis")
    except JsonProblem as e:
        if not e.issue["code"].endswith(".missing"):
            raise Stop(e.issue, exit_code=1, file=str(folder / "analysis.json"))
        analysis = None
    doc = latest_doc(folder, state)
    sections = {s.id for s in parse_sections(doc.read_text(encoding="utf-8"))}
    try:
        frontend = read_json(folder / "frontend.json", "frontend")
    except JsonProblem as e:
        if not e.issue["code"].endswith(".missing"):
            raise Stop(e.issue, exit_code=1, file=str(folder / "frontend.json"))
        frontend = None
    fields, issues = report(folder, state, analysis, settings.envs(), sections, _version_loader(folder, state),
                            frontend, _contract(folder, state)[1])
    return finish("status", issues, id=state["id"], dir=str(folder), lang=state["lang"],
                  workspace={"dir": str(workspace), "from": chosen_by}, up_to_date=not issues, **fields)


def cmd_steps(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    envs = settings.envs()
    if args.env not in envs:
        raise Stop(issue("steps.unknown-env", "error", "Environment %r is not in the project settings." % args.env,
                         hint="Known environments: %s." % ", ".join(envs), where="--env"))
    versions = state.get("versions") or []
    if not versions:
        raise Stop(issue("steps.not-rendered", "error", "Nothing has been rendered yet.",
                         hint="Run check and render first; the steps come from the rendered version.", where="--req"))
    last = versions[-1]
    load_version = _version_loader(folder, state)
    issues = []
    try:
        current = read_json(folder / "analysis.json", "analysis")
        frontend = _frontend(folder, False)
        if render.draft_fingerprint(current, frontend, _contract(folder, state)[1]) != last.get("sha256"):
            issues.append(issue("steps.not-rendered", "warn",
                                "The drafts changed after version %d; these steps are version %d's." % (last["v"], last["v"]),
                                hint="If the change matters for this release, run check and render first.",
                                where="analysis.json"))
    except JsonProblem:
        pass
    plan = for_env(load_version(last["v"]), state, args.env, last["v"], load_version,
                   render.load_texts(state["lang"]), folder / "out")
    return finish("steps", issues, id=state["id"], env=args.env, **plan)


def cmd_applied(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    versions = [v["v"] for v in state.get("versions", [])]
    if args.v not in versions:
        raise Stop(issue("applied.bad-version", "error", "There is no analysis version %d." % args.v,
                         hint="Saved versions: %s. The version is on the first line of the SQL file that was run; "
                         "if the user does not know which file, ask." % (", ".join(map(str, versions)) or "none yet"),
                         where="--v"))
    envs = settings.envs()
    if args.env not in envs:
        raise Stop(issue("applied.unknown-env", "error", "Environment %r is not in the project settings." % args.env,
                         hint="Known environments: %s. Use one of them, or ask the user before adding it to `envs` "
                         "in .req-profile.json." % ", ".join(envs), where="--env"))
    applied = state.setdefault("applied", {})
    before = (applied.get(args.env) or {}).get("v")
    issues = []
    if before is not None and before > args.v:
        issues.append(issue("applied.backwards", "warn",
                            "%s was recorded at version %d and is now set back to %d." % (args.env, before, args.v),
                            hint="Right only if the database was restored to an older state; otherwise record the "
                            "version again.", where="--env"))
    applied[args.env] = {"v": args.v, "at": _now().isoformat()}
    save_state(folder, state)
    note("Render again so the SQL file shows what each environment still needs.")
    return finish("applied", issues, id=state["id"], env=args.env, v=args.v, previous=before,
                  applied={e: r["v"] for e, r in applied.items()})


def cmd_example(args: argparse.Namespace) -> int:
    if args.kind == "frontend":
        return finish("example", kind="frontend", note=ex.NOTE, sample=ex.frontend_sample())
    return finish("example", kind="analysis", note=ex.NOTE, sample=ex.analysis_sample())


HANDLERS = {
    "new": cmd_new,
    "config set": cmd_config_set,
    "check": cmd_check,
    "render": cmd_render,
    "applied": cmd_applied,
    "steps": cmd_steps,
    "contract": cmd_contract,
    "status": cmd_status,
    "example": cmd_example,
}

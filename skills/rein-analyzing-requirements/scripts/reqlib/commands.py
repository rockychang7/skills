"""What each implemented command does. Parsing lives in cli.py."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

from . import example as ex
from . import render
from .check import check_analysis, check_frontend
from .doc import duplicate_ids, parse_sections, read_doc
from .files import JsonProblem, read_json, write_text
from .output import Stop, finish, issue, note, summarize
from .settings import LANGS, Settings, guard_not_in_skill_folder, workspace_suggestions
from .store import by_name, check_name, find, latest_doc, load_state, save_state

RUN = "python3 scripts/req.py"
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
                    hint="To store a new version of its document, use refresh. To start a separate "
                    "requirement, pick another short name.",
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
        issues = check_frontend(data, analysis)
    else:
        path = analysis_path
        doc = latest_doc(folder, state)
        sections = {s.id for s in parse_sections(doc.read_text(encoding="utf-8"))}
        issues = check_analysis(analysis, sections, settings.envs())
    return finish(
        "check",
        issues,
        limit=None if args.all else ISSUE_LIMIT,
        id=state.get("id", folder.name),
        file=str(path),
        summary=summarize(issues),
    )


def _save_version(folder: Path, state: dict, analysis: object, raw: str) -> tuple[dict, bool]:
    """Store the analysis as a new version unless it equals the latest one."""
    versions = state.setdefault("versions", [])
    digest = render.fingerprint(analysis)
    if versions and versions[-1].get("sha256") == digest:
        return versions[-1], False
    v = len(versions) + 1
    entry = {"v": v, "file": "versions/analysis-v%d.json" % v, "at": _now().isoformat(), "doc_v": len(state["docs"]),
             "sha256": digest}
    write_text(folder / entry["file"], raw)
    versions.append(entry)
    return entry, True


def cmd_render(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    analysis_path = folder / "analysis.json"
    analysis = _read_source(analysis_path, "Write it first; see the format with: %s example" % RUN)
    doc_text = latest_doc(folder, state).read_text(encoding="utf-8")
    issues = check_analysis(analysis, {s.id for s in parse_sections(doc_text)}, settings.envs())
    if any(i["level"] in ("error", "confirm") for i in issues):
        return finish("render", issues, limit=ISSUE_LIMIT, id=state["id"], rendered=False,
                      summary=summarize(issues))

    base, base_analysis = None, None
    if args.since is not None:
        found = [v for v in state.get("versions", []) if v["v"] == args.since]
        if not found:
            have = ", ".join(str(v["v"]) for v in state.get("versions", [])) or "none yet"
            raise Stop(issue("render.bad-since", "error", "There is no analysis version %d." % args.since,
                             hint="Saved versions: %s." % have, where="--since"))
        base_analysis = json.loads((folder / found[0]["file"]).read_text(encoding="utf-8"))
        base = {"kind": "version", "v": args.since}

    entry, created = _save_version(folder, state, analysis, analysis_path.read_text(encoding="utf-8-sig"))
    generated = entry["at"].replace("T", " ")[:16]
    wanted = list(args.only) if args.only else render.pages_needed(analysis, args.frontend)
    if args.frontend and "frontend" not in wanted:
        wanted.append("frontend")
    texts = render.load_texts(state["lang"])
    files, not_yet = [], []
    for page in wanted:
        if page not in render.READY:
            not_yet.append(page)
            continue
        content = render.brief_html(analysis, state, entry["v"], generated, doc_text, texts, base, base_analysis)
        result, page_issues = render.write_page(folder, texts["files"][page], content, state, entry["v"], args.force)
        files.append(dict(result, page=page))
        issues += page_issues
    save_state(folder, state)
    if not_yet:
        note("Not generated yet (coming in later versions of this skill): %s." % ", ".join(not_yet))
    return finish("render", issues, limit=ISSUE_LIMIT, id=state["id"], rendered=True, version=entry["v"],
                  new_version=created, compared_with=base, files=files, not_yet=not_yet)


def cmd_example(args: argparse.Namespace) -> int:
    if args.kind == "frontend":
        return finish("example", kind="frontend", note=ex.NOTE, sample=ex.frontend_sample())
    return finish("example", kind="analysis", note=ex.NOTE, sample=ex.analysis_sample())


HANDLERS = {
    "new": cmd_new,
    "config set": cmd_config_set,
    "check": cmd_check,
    "render": cmd_render,
    "example": cmd_example,
}

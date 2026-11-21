"""What each implemented command does. Parsing lives in cli.py."""

from __future__ import annotations

import argparse
import datetime
import json
from pathlib import Path

from . import diff as diffs
from . import example as ex
from . import xmind
from . import __version__, SKILL_NAME
from . import notice
from . import openapi
from . import render
from . import sends
from . import sql
from .check import check_analysis, check_frontend
from .doc import duplicate_ids, parse_sections, read_doc
from .files import JsonProblem, read_json, write_text
from .output import BLOCKING, Stop, finish, issue, note, summarize
from .settings import LANGS, Settings, guard_not_in_skill_folder, workspace_suggestions
from .status import report
from .steps import for_env
from .refresh import compare_docs, with_impact
from .store import by_name, check_name, doc_file, find, followed_doc, latest_doc, load_state, save_state, source_v

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
            "Write %s, in %s, citing sections as listed above; meta.source_v is 1." % (folder / "analysis.json", lang),
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
        _, doc, issues = followed_doc(folder, state, analysis)
        sections = {s.id for s in parse_sections(doc.read_text(encoding="utf-8"))}
        issues += check_analysis(analysis, sections, settings.envs())
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


def _save_version(folder: Path, state: dict, analysis: object, raw: str, doc_v: int, frontend: object = None,
                  frontend_raw: str = "", contract_v: object = None) -> tuple[dict, bool]:
    """Store the drafts as a new version unless they equal the latest one.

    A version is the analysis, plus frontend.json and the API description version when there are.
    """
    versions = state.setdefault("versions", [])
    digest = render.draft_fingerprint(analysis, frontend, contract_v)
    if versions and versions[-1].get("sha256") == digest:
        return versions[-1], False
    v = len(versions) + 1
    entry = {"v": v, "file": "versions/analysis-v%d.json" % v, "at": _now().isoformat(), "doc_v": doc_v,
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
    doc_v, doc, issues = followed_doc(folder, state, analysis)
    doc_text = doc.read_text(encoding="utf-8")
    load_version = _version_loader(folder, state)
    frontend = _frontend(folder, args.frontend)
    spec, contract_v = _contract(folder, state)
    issues += check_analysis(analysis, {s.id for s in parse_sections(doc_text)}, settings.envs())
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

    entry, created = _save_version(folder, state, analysis, analysis_path.read_text(encoding="utf-8-sig"), doc_v, frontend,
                                   (folder / "frontend.json").read_text(encoding="utf-8-sig") if frontend is not None else "",
                                   contract_v)
    wanted = list(args.only) if args.only else render.pages_needed(analysis, frontend is not None)
    if "frontend" in wanted and frontend is None:
        raise Stop(issue("frontend.missing", "error", "frontend.json has not been written yet.",
                         hint="Write it by references/frontend.md once the APIs exist in code.", where="--only"))
    job = _job(folder, state, settings, analysis, frontend, spec, contract_v, entry, doc_text)
    making = [p for p in wanted if p in render.READY]
    not_yet = [p for p in wanted if p not in render.READY]
    files, page_issues = _write_working(job, making, wanted, base, args.force)
    issues += page_issues
    save_state(folder, state)
    if not_yet:
        note("Not generated yet (coming in later versions of this skill): %s." % ", ".join(not_yet))
    return finish("render", issues, limit=ISSUE_LIMIT, id=state["id"], rendered=True, version=entry["v"],
                  new_version=created, compared_with=base, files=files, not_yet=not_yet)


def _job(folder: Path, state: dict, settings: Settings, analysis: dict, frontend: object, spec: object,
         contract_v: object, entry: dict, doc_text: str) -> render.Job:
    return render.Job(folder, state, settings.envs(), analysis, frontend, spec, contract_v, entry, doc_text,
                      _version_loader(folder, state), lambda v: _contract(folder, state, v)[0])


def _write_working(job: render.Job, making: list, wanted: list, base: object, force: bool) -> tuple[list, list]:
    """Write the working copies of `making` into out/.

    Change marks compare with `base` when given (render --since); otherwise with the copy of the
    page last sent, or, when this version is the one last sent, the page looks like that copy.
    """
    folder, state, v = job.folder, job.state, job.entry["v"]
    # Each page lists the requirement's pages: the ones it needs, plus any generated earlier.
    exists = {p for p in render.PAGES if (folder / "out" / job.names[p]).is_file()}
    needed = render.pages_needed(job.analysis, job.frontend is not None)
    shown = [p for p in render.PAGES if p in needed or p in wanted or p in exists]
    linked = exists | set(making)
    files: list = []
    issues: list = []
    for page in making:
        pages = render.page_list(job.texts, shown, linked, page, job.names)
        views = None
        if base:
            page_base, send = base, None
        else:
            page_base, send = sends.working_view(state.get("sends") or [], page, v)
            if page in render.SWITCH:
                views = sends.views(state.get("sends") or [], page, v, page_base) or None
                page_base = views[0]["base"] if views else page_base
        for name, content, extra in job.contents(page, page_base, send, pages, views):
            result, found = render.write_page(folder, name, content, state, v, force)
            files.append(dict(result, page=page, compared_with=page_base, **extra))
            issues += found
    return files, issues


UNEXPLAINED_LIMIT = 20


def cmd_send(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    analysis = _read_source(folder / "analysis.json", "Write it first; see the format with: %s example" % RUN)
    frontend = _frontend(folder, False)
    spec, contract_v = _contract(folder, state)
    versions = state.get("versions") or []
    if not versions or versions[-1].get("sha256") != render.draft_fingerprint(analysis, frontend, contract_v):
        return finish("send", [issue(
            "send.not-rendered", "error",
            "The drafts changed after the last render." if versions else "Nothing has been rendered yet.",
            hint="Run check and render, and look at the pages: what is sent is the last rendered version.",
            where="analysis.json")], id=state["id"], sent=False)
    entry = versions[-1]
    _, doc, issues = followed_doc(folder, state, analysis)
    doc_text = doc.read_text(encoding="utf-8")
    load_version = _version_loader(folder, state)

    # 1. What check and render would refuse. Their warnings were seen at render.
    found = check_analysis(analysis, {s.id for s in parse_sections(doc_text)}, settings.envs())
    found += sql.problems(analysis, state, load_version)
    if frontend is not None:
        found += check_frontend(frontend, analysis) + render.contract_issues(frontend, spec)
    issues += [i for i in found if i["level"] in BLOCKING]
    # 2. Answers not applied: readers would get rules that ignore them.
    decided = [q.get("id") for q in analysis.get("questions") or [] if isinstance(q, dict) and q.get("status") == "decided"]
    if decided:
        issues.append(issue("send.decided", "error", "Answered but not applied yet: %s." % ", ".join(decided),
                            hint="Readers would get rules that ignore these answers. Apply each one (references/"
                            "questions.md, \"When answers arrive\"), render, and send again.", where="questions"))

    # 3. Which pages go.
    needed = render.pages_needed(analysis, frontend is not None)
    if args.files:
        bad = [p for p in args.files if p not in needed]
        if bad:
            issues.append(issue("send.bad-files", "error", "This requirement has no %s to send." % ", ".join(bad),
                                hint="It has: %s." % ", ".join(needed), where="--files"))
        files = [p for p in render.PAGES if p in args.files and p in needed]
    else:
        files = [p for p in render.PAGES if p in sends.DEFAULT_FILES[args.to] and p in needed]
        if args.to in ("frontend", "all") and frontend is None:
            issues.append(issue("send.no-frontend-guide", "warn",
                                "The frontend API guide is not part of this send: frontend.json has not been written.",
                                hint="Once the APIs exist in code, write it (references/frontend.md), render, and send "
                                "it to the frontend.", where="--to"))
    job = _job(folder, state, settings, analysis, frontend, spec, contract_v, entry, doc_text)

    # 4. Hand edits would not reach the copy that is sent.
    outputs = state.get("outputs") or {}
    for page in files:
        for name in job.file_names(page):
            path, record = folder / "out" / name, outputs.get(name)
            if path.is_file() and record and render.file_hash(path.read_bytes()) != record.get("sha256"):
                issues.append(issue("send.page-edited", "error", "%s was changed by hand after it was generated." % name,
                                    hint="Ask the user whether the edits matter: copy what matters into analysis.json "
                                    "and render, or render --force to drop them.", where="out/" + name))

    # 5. Every change since the copy these readers last got is named by a change note.
    all_sends = state.get("sends") or []
    bases = {p: sends.base_send(all_sends, args.to, p) for p in files}
    missing: list = []
    for page, prev in bases.items():
        if prev is None or prev["v"] == entry["v"]:
            continue
        base_analysis, base_frontend, _ = job.base_drafts(prev["v"])
        notes = diffs.new_notes(base_analysis, analysis)
        if page == "frontend":
            notes += diffs.new_notes(base_frontend or {}, frontend or {})
        changes = sends.page_changes(page, base_analysis, analysis, lambda v=prev["v"]: job.frontend_marks(v))
        missing += [label for label in sends.unexplained(changes, notes) if label not in missing]
    if missing:
        listed = ", ".join(missing[:UNEXPLAINED_LIMIT]) + (
            " and %d more" % (len(missing) - UNEXPLAINED_LIMIT) if len(missing) > UNEXPLAINED_LIMIT else "")
        issues.append(issue(
            "send.unexplained", "error",
            "Changed since the copy these readers last received, but named by no change note: %s." % listed,
            hint="Readers learn what changed from the notes. Add `changes` entries at the top (frontend guide: "
            "frontend.json) in plain words, with refs naming each one; then check, render and send again.",
            where="changes"))
    if files and all(prev is not None and prev["v"] == entry["v"] for prev in bases.values()):
        issues.append(issue("send.nothing-new", "warn",
                            "These readers already received version %d of every page in this send." % entry["v"],
                            hint="Sending again is fine if they lost the files; otherwise there is nothing new.",
                            where="--to"))

    no, at = len(all_sends) + 1, _now().isoformat()
    pattern = job.texts["send"]["file"]
    names = {p: [sends.copy_name(n, no, at, pattern) for n in job.file_names(p)] for p in files}
    view = [{"page": p, "files": names[p], "compared_with": sends.base_meta(bases[p]) if bases[p] else None}
            for p in files]
    common = dict(id=state["id"], to=args.to, no=no, version=entry["v"])
    if any(i["level"] in BLOCKING for i in issues):
        return finish("send", issues, limit=None if args.all else ISSUE_LIMIT, sent=False, files=view, **common)
    text = _notice(job, args.to, no, at, files, names, bases)
    if args.preview:
        note("Preview only: nothing was recorded or written.")
        return finish("send", issues, sent=False, preview=True, files=view, notice=text, **common)

    # Write the copies that are sent, record the send, then bring the working copies in line.
    record = {"no": no, "to": args.to, "files": files, "v": entry["v"], "at": at, "copies": [], "notice": text}
    belongs = {"no": no, "date": sends.short_date(at)}
    rail = {p: names[p][0] for p in files}
    for item in view:
        page, prev = item["page"], bases[item["page"]]
        pages = render.page_list(job.texts, files, set(files), page, rail)
        for (_, content, extra), name in zip(job.contents(page, item["compared_with"], belongs, pages), names[page]):
            write_text(folder / "sent" / name, content)
            record["copies"].append(dict({"page": page, "file": "sent/" + name, "base": prev["no"] if prev else None,
                                          "sha256": render.file_hash(content.encode("utf-8"))}, **extra))
    state.setdefault("sends", []).append(record)
    working, page_issues = _write_working(job, files, needed, None, False)
    issues += page_issues
    save_state(folder, state)
    for item in view:
        item["files"] = [str(folder / "sent" / n) for n in item["files"]]
    return finish("send", issues, sent=True, files=view, working=working, notice=text, **common, next=[
        "Give the user the notice as it is, ready to paste. Hand the files and the notice over with the tools this "
        "session has (a chat or file-sharing skill) only after the user says where and to whom; with no such tool, "
        "give the user the file paths.",
    ])


def _notice(job: render.Job, to: str, no: int, at: str, files: list, names: dict, bases: dict) -> str:
    """The notice for the team chat, from the change notes since these readers' copies."""
    analysis, frontend = job.analysis, job.frontend
    got = [b for b in bases.values() if b is not None]
    oldest = min(got, key=lambda s: (s["v"], s["no"])) if got else None
    notes: list = []
    breaking: dict = {}
    keys = set().union(*(notice.page_keys(p, analysis, frontend) for p in files))
    if oldest is not None:
        base_analysis = job.base_drafts(oldest["v"])[0]
        frontend_notes: list = []
        if bases.get("frontend") is not None:
            v = bases["frontend"]["v"]
            frontend_notes = diffs.new_notes(job.base_drafts(v)[1] or {}, frontend or {})
            breaking = {api: lines["breaking"] for api, lines in job.frontend_diff(v)["apis"].items() if lines["breaking"]}
        notes = notice.pick(diffs.new_notes(base_analysis, analysis), frontend_notes, keys,
                            notice.page_keys("frontend", analysis, frontend))
    return notice.build(
        job.texts["send"], title=(analysis.get("meta") or {}).get("title", ""), to=to, no=no, at=at,
        files=[n for p in files for n in names[p]], first_files=[n for p in files if bases[p] is None for n in names[p]],
        base=oldest, notes=notes, breaking=breaking, analysis=analysis, open_questions=render.open_questions(analysis),
        keys=keys)


CITED_LIMIT = 15  # citations listed per changed section
LINES_LIMIT = 20  # was / now lines listed per changed section


def _capped(entry: dict) -> dict:
    """Keep one change entry short; the stored document versions have the rest."""
    for key, limit in (("was", LINES_LIMIT), ("now", LINES_LIMIT), ("cited_by", CITED_LIMIT)):
        if len(entry.get(key) or []) > limit:
            entry["more_" + key] = len(entry[key]) - limit
            entry[key] = entry[key][:limit]
    return entry


def cmd_refresh(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    analysis_path = folder / "analysis.json"
    analysis = _read_source(analysis_path, "") if analysis_path.is_file() else None
    docs = state["docs"]
    issues: list = []
    stored = False
    if args.doc:
        doc_path = (_cwd() / Path(args.doc).expanduser()).resolve()
        text, issues = read_doc(doc_path)
        if text == latest_doc(folder, state).read_text(encoding="utf-8"):
            note("The document is the same as stored version %d; nothing was stored." % len(docs))
        else:
            v = len(docs) + 1
            entry = {"v": v, "file": "source/doc-v%d.md" % v, "from": str(doc_path), "at": _now().isoformat()}
            write_text(folder / entry["file"], text)
            docs.append(entry)
            save_state(folder, state)
            stored = True
    latest = len(docs)
    latest_text = latest_doc(folder, state).read_text(encoding="utf-8")
    sections = parse_sections(latest_text)
    for dupe in duplicate_ids(sections):
        issues.append(issue("doc.duplicate-section", "warn", "Section §%s appears more than once in the document." % dupe,
                            hint="src can only point to the first one; mention this to the user if it matters.",
                            where=docs[-1]["file"]))

    # Compare with the version the analysis follows; without an analysis, with the one before.
    base = source_v(analysis) if analysis is not None else None
    if base is not None and not 1 <= base <= latest:
        issues += followed_doc(folder, state, analysis)[2]
        base = None
    if base is None:
        base = max(latest - 1, 1)
    found = {"head": None, "sections": []}
    if base < latest:
        found = with_impact(compare_docs(doc_file(folder, state, base).read_text(encoding="utf-8"), latest_text),
                            analysis)
    changes = [_capped(e) for e in found["sections"]]
    summary = {k: sum(1 for e in changes if e["change"] == k) for k in ("added", "removed", "modified", "moved")}
    name = state.get("name", args.req)
    fixes = ("rewrite what cites changed or removed sections (drop items no longer wanted with `removed`), write in "
             "added sections or list them in skipped_sections, renumber src of moved sections, add `changes` "
             "entries with src, and set meta.source_v to %d" % latest)
    if analysis is None:
        steps = ["Write %s from document version %d (meta.source_v %d)." % (analysis_path, latest, latest)]
    elif base >= latest:
        steps = []
        note("The analysis already follows the latest document (version %d)." % latest)
    elif changes:
        issues.append(issue(
            "refresh.impact", "confirm",
            "Document version %d changes %d section(s) since version %d, the one the analysis follows."
            % (latest, len(changes), base),
            hint="Before changing the analysis, tell the user in plain words what changed and what it affects "
            "(references/changes.md), and wait for a go-ahead. Nothing needs recording.",
            where="source/doc-v%d.md" % latest))
        steps = [
            "Tell the user what changed and what it affects: per entry, was/now, and cited_by, items and apis; "
            "add code already written for those items on the working branch. Wait for a go-ahead.",
            "Then update analysis.json: %s." % fixes,
            "Then: %s check --req %s, and render." % (RUN, name),
        ]
    else:
        steps = ["Only the lines before the first section changed: update meta.doc_version if the version changed, "
                 "set meta.source_v to %d, then check and render." % latest]
    return finish("refresh", issues, id=state["id"], stored=stored, doc_v=latest, file=str(latest_doc(folder, state)),
                  compared={"from": base, "to": latest} if base < latest else None, summary=summary,
                  head=found["head"], changes=changes, sections=["§%s %s" % (s.id, s.title) for s in sections],
                  next=steps)


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
    follows, doc, source_issues = followed_doc(folder, state, analysis)
    sections = {s.id for s in parse_sections(doc.read_text(encoding="utf-8"))}
    try:
        frontend = read_json(folder / "frontend.json", "frontend")
    except JsonProblem as e:
        if not e.issue["code"].endswith(".missing"):
            raise Stop(e.issue, exit_code=1, file=str(folder / "frontend.json"))
        frontend = None
    fields, issues = report(folder, state, analysis, settings.envs(), sections, _version_loader(folder, state),
                            frontend, _contract(folder, state)[1], follows, source_issues)
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


def cmd_export(args: argparse.Namespace) -> int:
    settings, folder, state = _requirement(args)
    versions = state.get("versions") or []
    if not versions:
        raise Stop(issue("export.not-rendered", "error", "Nothing has been rendered yet.",
                         hint="Run check and render first; the map is drawn from the rendered version.", where="--req"))
    last = versions[-1]
    load_version = _version_loader(folder, state)
    analysis = load_version(last["v"])
    if not [a for a in (analysis.get("backend") or {}).get("apis") or [] if not a.get("removed")]:
        raise Stop(issue("export.no-apis", "error", "Version %d has no backend APIs, so there is no backend plan to "
                         "draw." % last["v"], where="--req"))
    issues = []
    try:
        current = read_json(folder / "analysis.json", "analysis")
        if render.draft_fingerprint(current, _frontend(folder, False), _contract(folder, state)[1]) != last.get("sha256"):
            issues.append(issue("export.not-rendered", "warn",
                                "The drafts changed after version %d; the map shows version %d." % (last["v"], last["v"]),
                                hint="If the change matters, run check and render first, then export again.",
                                where="analysis.json"))
    except JsonProblem:
        pass
    # Like the backend plan page: mark what changed since the copy of the plan last sent.
    texts = render.load_texts(state["lang"])
    prev = sends.last_send(state.get("sends") or [], "plan")
    marks = diffs.compare_backend(load_version(prev["v"]), analysis)["items"] if prev and prev["v"] != last["v"] else {}
    raw = xmind.pack(xmind.build(analysis, texts, marks), texts["xmind"]["sheet"], last["at"], SKILL_NAME, __version__)
    name = texts["files"]["plan"].rsplit(".", 1)[0] + ".xmind"
    result, found = render.write_page(folder, name, raw, state, last["v"], args.force, again="export xmind")
    save_state(folder, state)
    return finish("export", issues + found, id=state["id"], format="xmind", version=last["v"],
                  compared_with=sends.base_meta(prev) if marks else None, **result,
                  next=["Owners and status changed in XMind do not come back: set them on the backend plan page "
                        "(\"copy plan\") or tell the agent, then render and export again."])


HANDLERS = {
    "new": cmd_new,
    "config set": cmd_config_set,
    "check": cmd_check,
    "render": cmd_render,
    "applied": cmd_applied,
    "steps": cmd_steps,
    "contract": cmd_contract,
    "refresh": cmd_refresh,
    "export": cmd_export,
    "send": cmd_send,
    "status": cmd_status,
    "example": cmd_example,
}

"""Turning an analysis into the pages people read: brief, backend plan, release checklist,
frontend API guide.

The SQL file is built in sql.py; render lists it among the pages.

A page is one HTML template (assets/templates) plus a JSON blob of data; the
browser draws the page from the data. Text on the page comes from the language
table (assets/i18n/<lang>.json), so the same template serves every language.
"""

from __future__ import annotations

import hashlib
import html
import json
import re
from pathlib import Path
from typing import Any

from . import diff as diffs
from . import openapi
from . import sql
from .doc import section_texts
from .files import write_text
from .output import issue

ASSETS = Path(__file__).resolve().parents[2] / "assets"
PAGES = ("brief", "plan", "sql", "release", "frontend")
READY = ("brief", "plan", "sql", "release", "frontend")  # pages this version can generate
SECTION_REF = re.compile(r"§\s*(\d+(?:\.\d+)*)")


def load_texts(lang: str) -> dict[str, Any]:
    return json.loads((ASSETS / "i18n" / ("%s.json" % lang)).read_text(encoding="utf-8"))


def fingerprint(data: Any) -> str:
    """Same content, same fingerprint, whatever the formatting."""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def draft_fingerprint(analysis: Any, frontend: Any = None, contract_v: int | None = None) -> str:
    """What a saved version stands for: the analysis, plus frontend.json and the API description when there are.

    Without a frontend guide it is the analysis' own fingerprint, so versions
    saved before frontend.json existed still match.
    """
    if frontend is None and contract_v is None:
        return fingerprint(analysis)
    return fingerprint({"analysis": analysis, "frontend": frontend, "contract": contract_v})


def file_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pages_needed(analysis: dict[str, Any], frontend: bool) -> list[str]:
    backend = analysis.get("backend") or {}
    needed = ["brief"]
    if backend.get("apis"):
        needed.append("plan")
    if sql.databases(analysis):
        needed.append("sql")
    if backend.get("tables") or backend.get("data") or backend.get("configs") or analysis.get("release"):
        needed.append("release")
    if frontend:
        needed.append("frontend")
    return needed


def page_list(texts: dict[str, Any], shown: list[str], linked: set[str], current: str,
              names: dict[str, str] | None = None) -> list[dict[str, Any]]:
    """The requirement's pages as each page's rail lists them; only `linked` ones get a link.

    `names` overrides file names (the SQL file of a named database).
    """
    out = []
    for page in shown:
        entry: dict[str, Any] = {"page": page, "label": texts["pages"][page]}
        if page == current:
            entry["current"] = True
        elif page in linked:
            entry["file"] = (names or {}).get(page) or texts["files"][page]
        out.append(entry)
    return out


def _meta(state: dict[str, Any], version: int, generated: str) -> dict[str, Any]:
    """Header facts every page shows; doc_v is the document version this analysis version follows."""
    doc_v = next((v.get("doc_v") for v in state.get("versions") or [] if v["v"] == version), None)
    return {"id": state["id"], "analysis_v": version, "doc_v": doc_v or len(state["docs"]), "generated": generated,
            "send": None}


def _fill(page: str, analysis: dict[str, Any], lang: str, texts: dict[str, Any], data: dict[str, Any]) -> str:
    title = texts[page]["page_title"].replace("{title}", str(analysis.get("meta", {}).get("title", "")))
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    template = (ASSETS / "templates" / ("%s.html" % page)).read_text(encoding="utf-8")
    return (template.replace("__LANG__", lang)
            .replace("__TITLE__", html.escape(title))
            .replace("__NOSCRIPT__", html.escape(texts[page]["noscript"]))
            .replace("__REQ_DATA__", payload))


def brief_html(
    analysis: dict[str, Any],
    state: dict[str, Any],
    version: int,
    generated: str,
    doc_text: str,
    texts: dict[str, Any],
    base: dict[str, Any] | None = None,
    base_analysis: dict[str, Any] | None = None,
    pages: list[dict[str, Any]] | None = None,
) -> str:
    shown = {k: v for k, v in analysis.items() if k != "skipped_sections"}  # skipped sections are never shown
    cited = set(SECTION_REF.findall(json.dumps(shown, ensure_ascii=False)))
    data = {
        "lang": state["lang"],
        "t": texts["brief"],
        "meta": _meta(state, version, generated),
        "pages": pages or [],
        "analysis": analysis,
        "sections": section_texts(doc_text, cited),
        "diff": dict(diffs.compare(base_analysis, analysis), base=base) if base and base_analysis is not None else None,
    }
    return _fill("brief", analysis, state["lang"], texts, data)


PLAN_PARTS = ("meta", "clients", "features", "backend", "questions")


def plan_html(
    analysis: dict[str, Any],
    state: dict[str, Any],
    version: int,
    generated: str,
    texts: dict[str, Any],
    base: dict[str, Any] | None = None,
    base_analysis: dict[str, Any] | None = None,
    pages: list[dict[str, Any]] | None = None,
) -> str:
    """The backend plan: build order, who does what, each task, tables, data, config, risks.

    It links into the brief only when `pages` gives the brief a file.
    """
    brief = [p.get("file") for p in pages or [] if p["page"] == "brief"]
    data = {
        "lang": state["lang"],
        "t": texts["plan"],
        "meta": _meta(state, version, generated),
        "pages": pages or [],
        "brief_file": brief[0] if brief else None,
        "analysis": {k: analysis.get(k) for k in PLAN_PARTS},
        "changes": diffs.backend_notes(analysis),
        "diff": dict(diffs.compare_backend(base_analysis, analysis), base=base)
        if base and base_analysis is not None else None,
    }
    return _fill("plan", analysis, state["lang"], texts, data)


def contract_issues(frontend: Any, spec: dict[str, Any] | None) -> list[dict[str, str]]:
    """Each API's `contract` against the stored API description."""
    out: list[dict[str, str]] = []
    if not isinstance(frontend, dict):
        return out
    apis = [(c.get("id"), x) for c in frontend.get("clients") or [] if isinstance(c, dict)
            for x in c.get("apis") or [] if isinstance(x, dict) and not x.get("removed")]
    wanting = [(cid, x) for cid, x in apis if x.get("contract")]
    if spec is None:
        if wanting:
            out.append(issue("frontend.no-description", "warn",
                             "No API description is stored, so the frontend guide has no fields for %s."
                             % ", ".join(str(x.get("id")) for _, x in wanting),
                             hint="Store one: req.py contract --req <name> --openapi <file or URL>.",
                             where="contract"))
        return out
    known = openapi.operations(spec)
    for cid, x in wanting:
        if openapi.operation(spec, x["contract"]) is None:
            out.append(issue("frontend.op-missing", "error",
                             "%s is not in the stored API description." % x["contract"],
                             hint="Write `contract` as METHOD /path exactly as in the description (%d operations, "
                             "e.g. %s). If the API is not in the code yet, store a newer description once it is."
                             % (len(known), ", ".join(known[:3])),
                             where="clients[%s].apis[%s].contract" % (cid, x.get("id"))))
    return out


FRONTEND_COMPARED = ("contract", "change", "facts", "frontend", "fields", "removed")


def _frontend_clients(analysis: dict[str, Any], frontend: dict[str, Any], spec: dict[str, Any] | None,
                      t: dict[str, str], base_analysis: dict[str, Any] | None, base_frontend: dict[str, Any] | None,
                      base_spec: dict[str, Any] | None) -> tuple[list[dict[str, Any]], dict[str, Any]]:
    """Clients with each API's fields filled in, and the change marks against the base (if any)."""
    a_apis = {x.get("id"): x for x in (analysis.get("backend") or {}).get("apis") or []}
    compared = base_analysis is not None
    b_apis = {x.get("id"): x for x in ((base_analysis or {}).get("backend") or {}).get("apis") or []}
    b_fapis = {x.get("id"): x for c in (base_frontend or {}).get("clients") or [] for x in c.get("apis") or []}
    items: dict[str, str] = {}
    lines: dict[str, dict[str, list[str]]] = {}
    total = 0
    clients = []
    for c in frontend.get("clients") or []:
        rows = []
        for x in c.get("apis") or []:
            xid = x.get("id")
            a = a_apis.get(xid) or {}
            row = dict(x, name=a.get("name") or "", kind=a.get("kind") or "new", removed=x.get("removed") or a.get("removed"))
            before = b_fapis.get(xid) if base_frontend is not None else b_apis.get(xid)
            if row["removed"]:
                if compared and before is not None and not before.get("removed"):
                    items["api:" + xid] = "remove"
                    total += 1
                rows.append(row)
                continue
            op = openapi.operation(spec, x["contract"]) if spec is not None and x.get("contract") else None
            if op is not None:
                row.update(method=op["method"], path=op["path"], query=op["query"], body=op["body"],
                           response=op["response"])
            elif isinstance(x.get("fields"), dict):
                row.update(params=x["fields"].get("params") or [], response=x["fields"].get("response") or [], hand=True)
            elif x.get("contract") and spec is not None:
                row["missing"] = x["contract"]
            if compared:
                if before is None:
                    items["api:" + xid] = "add"
                    total += 1
                else:
                    base_op = None
                    if op is not None and base_spec is not None:
                        base_op = openapi.operation(base_spec, before.get("contract") or x["contract"])
                    found = openapi.compare(base_op, op, t) if op is not None else None
                    if found and found["marks"]:
                        row.update(marks=found["marks"], removed_fields=found["removed"])
                        items["api:" + xid] = "modify"
                        lines[xid] = {"breaking": found["breaking"], "compatible": found["compatible"]}
                        total += len(found["marks"])
                    elif base_frontend is not None and any(
                            json.dumps(before.get(k), sort_keys=True, ensure_ascii=False)
                            != json.dumps(x.get(k), sort_keys=True, ensure_ascii=False) for k in FRONTEND_COMPARED):
                        items["api:" + xid] = "modify"
                        total += 1
            rows.append(row)
        clients.append(dict(c, apis=rows))
    return clients, {"items": items, "apis": lines, "total": total}


def frontend_html(
    analysis: dict[str, Any],
    frontend: dict[str, Any],
    state: dict[str, Any],
    version: int,
    generated: str,
    texts: dict[str, Any],
    spec: dict[str, Any] | None = None,
    contract_v: int | None = None,
    base: dict[str, Any] | None = None,
    base_analysis: dict[str, Any] | None = None,
    base_frontend: dict[str, Any] | None = None,
    base_spec: dict[str, Any] | None = None,
    pages: list[dict[str, Any]] | None = None,
) -> str:
    """The frontend API guide: per client, pages, APIs with fields from the API description, display rules."""
    t = texts["frontend"]
    compared = base is not None and base_analysis is not None
    clients, marks = _frontend_clients(analysis, frontend, spec, t, base_analysis if compared else None,
                                       base_frontend if compared else None, base_spec if compared else None)
    notes = frontend.get("changes") or []
    brief = [p.get("file") for p in pages or [] if p["page"] == "brief"]
    data = {
        "lang": state["lang"],
        "t": t,
        "meta": dict(_meta(state, version, generated), contract_v=contract_v),
        "pages": pages or [],
        "brief_file": brief[0] if brief else None,
        "title": (analysis.get("meta") or {}).get("title", ""),
        "code_commit": (analysis.get("meta") or {}).get("code_commit", ""),
        "conventions": frontend.get("conventions") or [],
        "clients": clients,
        "error_codes": frontend.get("error_codes") or [],
        "changes": notes,
        "questions": open_questions(analysis),
        "features": {f.get("id"): {"name": f.get("name"), "apis": f.get("apis") or []} for f in analysis.get("features") or []},
        "diff": dict(marks, base=base, new_changes=len(diffs.new_notes(base_frontend or {}, frontend)))
        if compared else None,
    }
    return _fill("frontend", analysis, state["lang"], texts, data)


def open_questions(analysis: dict[str, Any]) -> list[dict[str, Any]]:
    """Open questions, each with `blocks`: the features and APIs it names, with their names."""
    names = {x.get("id"): x.get("name") for x in (analysis.get("backend") or {}).get("apis") or []}
    names.update({f.get("id"): f.get("name") for f in analysis.get("features") or []})
    return [dict(q, blocks=[{"id": i, "name": names.get(i) or ""} for i in q.get("affects") or []])
            for q in analysis.get("questions") or [] if q.get("status") == "open"]


def release_html(
    analysis: dict[str, Any],
    state: dict[str, Any],
    version: int,
    generated: str,
    texts: dict[str, Any],
    envs: list[tuple[str, int | None]],
    sql_rows: dict[str, list[dict[str, Any]]],
    base: dict[str, Any] | None = None,
    base_analysis: dict[str, Any] | None = None,
    pages: list[dict[str, Any]] | None = None,
) -> str:
    """The release checklist: steps by stage for the environment picked on the page.

    `envs` is [(name, version it ran or None)]; `sql_rows` is sql.release_rows.
    """
    brief = [p.get("file") for p in pages or [] if p["page"] == "brief"]
    data = {
        "lang": state["lang"],
        "t": texts["release"],
        "meta": _meta(state, version, generated),
        "pages": pages or [],
        "brief_file": brief[0] if brief else None,
        "envs": [{"name": e, "applied": v} for e, v in envs],
        "sql": sql_rows,
        "analysis": {"meta": analysis.get("meta"), "release": analysis.get("release") or [],
                     "configs": (analysis.get("backend") or {}).get("configs") or [],
                     "questions": open_questions(analysis)},
        "changes": diffs.release_notes(analysis),
        "diff": dict(diffs.compare_release(base_analysis, analysis), base=base)
        if base and base_analysis is not None else None,
    }
    return _fill("release", analysis, state["lang"], texts, data)


def write_page(folder: Path, name: str, content: str, state: dict[str, Any], version: int,
               force: bool) -> tuple[dict[str, Any], list[dict[str, str]]]:
    """Write out/<name> unless someone edited the last generated copy by hand."""
    out = folder / "out" / name
    raw = content.encode("utf-8")
    digest = file_hash(raw)
    outputs = state.setdefault("outputs", {})
    result: dict[str, Any] = {"file": str(out)}
    if out.is_file():
        current = file_hash(out.read_bytes())
        if current == digest:
            result["status"] = "unchanged"
            return result, []
        record = outputs.get(name)
        if not force and (record is None or current != record.get("sha256")):
            alt = out.with_name(out.stem + ".new" + out.suffix)
            write_text(alt, content)
            result.update(status="kept-manual", new_file=str(alt))
            return result, [
                issue(
                    "render.kept-manual",
                    "warn",
                    "%s was changed by hand since it was generated, so it was kept; the new page is %s." % (name, alt.name),
                    hint="Ask the user whether the hand edits matter. Copy what matters into analysis.json and "
                    "render again, or run render --force to replace the file.",
                    where="out/" + name,
                )
            ]
    write_text(out, content)
    outputs[name] = {"sha256": digest, "v": version}
    result["status"] = "written"
    return result, []

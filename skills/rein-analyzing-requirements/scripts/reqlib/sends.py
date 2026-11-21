"""Who received which copy of which page, and what a new send compares with (the send command).

A send is recorded in state.json:

    "sends": [{"no": 1, "to": "frontend", "files": ["brief", "frontend"], "v": 3, "at": "2026-11-15T10:00:00",
               "copies": [{"page": "brief", "file": "sent/1.需求导读-第1次-1115.html", "base": null,
                           "sha256": "…"}, …]}]

Readers are groups: `frontend` and `backend`; a send to `all` reaches both.
Each page of a new send is compared with the copy of that page the readers
last received, so the frontend team that got version 3 sees every change from
3 to 10, not only from 9 to 10. A page sent to `all` is compared with the
oldest of those copies, so neither group misses a change.
"""

from __future__ import annotations

import datetime
from typing import Any, Callable

from . import diff as diffs

GROUPS = ("frontend", "backend")
TARGETS = GROUPS + ("all",)
# Pages each reader gets by default, when the requirement has them.
DEFAULT_FILES = {
    "frontend": ("brief", "frontend"),
    "backend": ("brief", "plan", "sql", "release"),
    "all": ("brief", "plan", "sql", "release", "frontend"),
}


def readers(to: str) -> tuple[str, ...]:
    return GROUPS if to == "all" else (to,)


def last_copy(sends: list[dict[str, Any]], group: str, page: str) -> dict[str, Any] | None:
    """The latest send that gave `group` this page."""
    found = [s for s in sends if group in readers(s["to"]) and page in s["files"]]
    return found[-1] if found else None


def base_send(sends: list[dict[str, Any]], to: str, page: str) -> dict[str, Any] | None:
    """The send a new copy of `page` for `to` is compared with; None the first time they get it."""
    got = [s for s in (last_copy(sends, g, page) for g in readers(to)) if s is not None]
    return min(got, key=lambda s: (s["v"], s["no"])) if got else None


def last_send(sends: list[dict[str, Any]], page: str) -> dict[str, Any] | None:
    """The latest send of this page to anyone."""
    found = [s for s in sends if page in s["files"]]
    return found[-1] if found else None


def short_date(at: str) -> str:
    """"2026-11-18T10:00:00" -> "11-18", as pages and file names show it."""
    return datetime.datetime.fromisoformat(at).strftime("%m-%d")


def base_meta(send: dict[str, Any]) -> dict[str, Any]:
    """What a page shows as the copy it compares with."""
    return {"kind": "send", "no": send["no"], "date": short_date(send["at"]), "v": send["v"]}


def copy_name(name: str, no: int, at: str, pattern: str) -> str:
    """File name of a sent copy: `pattern` ("-第{n}次-{date}") goes before the extension."""
    stem, dot, ext = name.rpartition(".")
    suffix = pattern.replace("{n}", str(no)).replace("{date}", short_date(at).replace("-", ""))
    return "%s%s.%s" % (stem, suffix, ext) if dot else name + suffix


# ------------------------------------------------------------ change notes cover every change


def _step_ids(analysis: dict[str, Any], flow: str, step: str) -> set[str]:
    for fw in analysis.get("flows") or []:
        if fw.get("id") == flow:
            for s in fw.get("steps") or []:
                if s.get("id") == step:
                    return set(s.get("features") or [])
    return set()


def changed_ids(page: str, old: dict[str, Any], new: dict[str, Any],
                frontend_items: dict[str, str] | None = None) -> dict[str, set[str]]:
    """What changed on one page between two analysis versions: {label: IDs any of which a note may name}.

    The label is what is shown to the agent ("feature C06", "flow P1 step s9");
    a step counts as explained by a note naming its flow or one of its features.
    Lists without IDs (terms, states, risks, …) are left out: no note can name them.
    """
    found: dict[str, set[str]] = {}
    if page == "brief":
        d = diffs.compare(old, new)
        for key, s in d["items"].items():
            kind, _, rest = key.partition(":")
            if kind == "step":
                flow, _, step = rest.partition(":")
                found["flow %s step %s" % (flow, step)] = {flow} | _step_ids(new, flow, step) | _step_ids(old, flow, step)
            else:
                found["%s %s" % (kind, rest)] = {rest}
        for flow, steps in d["removed_steps"].items():
            for st in steps:
                found["flow %s step %s" % (flow, st.get("id"))] = {flow} | set(st.get("features") or [])
    elif page == "plan":
        d = diffs.compare_backend(old, new)
        data = (new.get("backend") or {}).get("data") or []
        for key in d["items"]:
            kind, _, rest = key.partition(":")
            if kind == "data":
                table = data[int(rest)].get("table") if int(rest) < len(data) else None
                found["data change on %s" % table] = {table} if table else set()
            else:
                found["%s %s" % ("API" if kind == "api" else kind, rest)] = {rest}
    elif page == "release":
        for key in diffs.compare_release(old, new)["items"]:
            kind, _, rest = key.partition(":")
            if kind != "sql":  # a database's SQL changes with its tables, which the plan covers
                found["%s %s" % ("release item" if kind == "release" else kind, rest)] = {rest}
    elif page == "frontend":
        for key in frontend_items or {}:
            api = key.partition(":")[2]
            found["API %s on the frontend guide" % api] = {api}
    return found


def unexplained(changes: dict[str, set[str]], notes: list[dict[str, Any]]) -> list[str]:
    """Labels of the changes no note names."""
    named = {ref for n in notes for ref in n.get("refs") or []}
    return [label for label, ids in changes.items() if not ids & named]


def page_changes(page: str, base_analysis: dict[str, Any], analysis: dict[str, Any],
                 frontend_marks: Callable[[], dict[str, str]] | None = None) -> dict[str, set[str]]:
    """changed_ids for a page; the SQL file shows tables, which the backend plan already checks."""
    if page == "sql":
        return {k: v for k, v in changed_ids("plan", base_analysis, analysis).items()
                if k.startswith(("table ", "data change"))}
    return changed_ids(page, base_analysis, analysis, frontend_marks() if page == "frontend" and frontend_marks else None)


def working_view(sends: list[dict[str, Any]], page: str, v: int) -> tuple[dict[str, Any] | None, dict[str, Any] | None]:
    """(base, send) for the working copy of a page in out/.

    Never sent: no marks. Changed since it was last sent: marks against that copy. This very
    version was the last one sent: the page looks like that sent copy.
    """
    last = last_send(sends, page)
    if last is None:
        return None, None
    if last["v"] != v:
        return base_meta(last), None
    copy = next((c for c in last.get("copies") or [] if c["page"] == page), {})
    before = next((s for s in sends if s["no"] == copy.get("base")), None)
    return (base_meta(before) if before else None), {"no": last["no"], "date": short_date(last["at"])}

"""The notice to paste into a team chat when files are sent.

Built from the change notes the agent wrote (`changes` in analysis.json and
frontend.json), never reworded: people read the notes, the program only picks
and orders them.

- Only notes touching something on the pages of this send.
- Grouped: breaking API changes first (from comparing the API descriptions),
  then added, changed, removed; newest first within each group.
- Open P0 questions say what to hold off on, among what these pages show.
- The first send to a team has no changes; it says what is being built.
"""

from __future__ import annotations

from typing import Any

from . import diff as diffs
from .sends import short_date

MAX_NOTES = 12
INDENT = "  · "


def _fill(text: str, **values: Any) -> str:
    for k, v in values.items():
        text = text.replace("{%s}" % k, str(v))
    return text


def page_keys(page: str, analysis: dict[str, Any], frontend: dict[str, Any] | None) -> set[str]:
    """The IDs, table names and config keys a page shows, for picking the notes its readers care about."""
    if page == "brief":
        return {x.get("id") for part in ("features", "questions", "flows") for x in analysis.get(part) or []
                if isinstance(x, dict)} - {None}
    if page == "plan":
        return diffs.backend_keys(analysis)
    if page == "release":
        return diffs.release_keys(analysis)
    if page == "sql":
        be = analysis.get("backend") or {}
        return ({x.get("name") for x in be.get("tables") or []} | {x.get("table") for x in be.get("data") or []}) - {None}
    return {x.get("id") for c in (frontend or {}).get("clients") or [] for x in c.get("apis") or []} - {None}


def pick(analysis_notes: list[dict[str, Any]], frontend_notes: list[dict[str, Any]], keys: set[str],
         frontend_apis: set[str]) -> list[dict[str, Any]]:
    """The notes for this send, newest first.

    Frontend guide notes all count. An analysis note counts when it names something on these
    pages, unless all it names there are APIs a frontend guide note already describes.
    """
    described = {r for n in frontend_notes for r in n.get("refs") or []} & frontend_apis
    out = list(frontend_notes)
    for n in analysis_notes:
        named = set(n.get("refs") or []) & keys
        if named and not named <= described:
            out.append(n)
    return out


def _size(analysis: dict[str, Any], t: dict[str, str]) -> str:
    be = analysis.get("backend") or {}
    features = [f for f in analysis.get("features") or [] if not f.get("removed")]
    apis = [x for x in be.get("apis") or [] if not x.get("removed")]
    tables = [x for x in be.get("tables") or [] if not x.get("removed")]
    parts = [_fill(t["n_size_features"], n=len(features))]
    if apis:
        parts.append(_fill(t["n_size_apis"], n=len(apis), new=sum(1 for x in apis if x.get("kind") == "new"),
                           modify=sum(1 for x in apis if x.get("kind") == "modify")))
    if tables:
        parts.append(_fill(t["n_size_tables"], n=len(tables)))
    return t["n_sep"].join(parts)


def _holds(questions: list[dict[str, Any]], keys: set[str], t: dict[str, str]) -> list[str]:
    """One line per open P0 question blocking something on these pages: what to hold off on."""
    lines = []
    for q in questions:
        blocks = [b for b in q.get("blocks") or [] if b.get("id") in keys]
        if q.get("priority") != "P0" or not blocks:
            continue
        names = t["n_list"].join("%s %s" % (b["id"], b["name"]) if b.get("name") else b["id"] for b in blocks)
        lines.append(INDENT + _fill(t["n_hold_line"], names=names, q=q.get("id"), title=q.get("title", "")))
    return lines


def build(t: dict[str, str], *, title: str, to: str, no: int, at: str, files: list[str], first_files: list[str],
          base: dict[str, Any] | None, notes: list[dict[str, Any]], breaking: dict[str, list[str]],
          analysis: dict[str, Any], open_questions: list[dict[str, Any]], keys: set[str]) -> str:
    """The notice text.

    `base` is the send these readers' copies compare with (the oldest, when pages differ), None
    the first time; `breaking` maps an API ID to what the API description comparison found;
    `keys` are what the pages of this send show (page_keys).
    """
    lines = [_fill(t["n_title"], title=title, reader=t["n_reader_" + to], n=no, date=short_date(at))]
    if base is None:
        lines.append(_fill(t["n_what"], what=(analysis.get("brief") or {}).get("what", "")))
        lines.append(_size(analysis, t))
    elif not notes and not breaking:
        lines.append(_fill(t["n_nothing"], n=base["no"], date=short_date(base["at"])))
    else:
        lines.append(_fill(t["n_since"], n=base["no"], date=short_date(base["at"])))
        groups: dict[str, list[str]] = {"breaking": [], "add": [], "modify": [], "remove": []}
        named: set[str] = set()
        shown = 0
        for n in notes:
            if shown == MAX_NOTES:
                break
            hits = [api for api in n.get("refs") or [] if api in breaking]
            text = INDENT + n.get("text", "")
            if hits:
                # Several APIs: say which one each finding is about.
                found = [line if len(hits) == 1 else _fill(t["n_api_of"], api=api, line=line)
                         for api in hits for line in breaking[api]]
                found = list(dict.fromkeys(found))[:3]
                text += _fill(t["n_check"], lines=t["n_join"].join(found))
                named.update(hits)
                groups["breaking"].append(text)
            else:
                groups.get(n.get("type"), groups["modify"]).append(text)
            shown += 1
        # An API the comparison flags that no shown note mentions still gets a line.
        for api, found in breaking.items():
            if api not in named and found:
                groups["breaking"].append(INDENT + _fill(t["n_api_line"], api=api, lines=t["n_join"].join(found[:3])))
        for key in ("breaking", "add", "modify", "remove"):
            if groups[key]:
                lines.append(t["n_group_" + key])
                lines += groups[key]
        if len(notes) > shown:
            lines.append(_fill(t["n_more"], n=len(notes) - shown))
    holds = _holds(open_questions, keys, t)
    if holds:
        lines.append(t["n_hold"])
        lines += holds
    lines.append(_fill(t["n_files"], files=t["n_list"].join(
        f + (t["n_first_file"] if base is not None and f in first_files else "") for f in files)))
    lines.append(t["n_latest"])
    return "\n".join(lines)

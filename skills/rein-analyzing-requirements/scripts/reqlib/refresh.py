"""Two versions of the requirement document, compared section by section (the refresh command).

Sections are matched by content, not only by number: in a document whose
headings carry no numbers, inserting one section renumbers every later one,
so the old "§2.4" may be "§2.5" now and the analysis must follow.

Matching, in this order:
1. same heading and text: unchanged, or moved when the number differs;
2. same number and heading: the text changed;
3. same heading under another number: moved, and maybe changed;
4. similar heading and text: changed, and moved when the number differs.
What is left was removed (old version) or added (new version).

Each change lists what in the analysis cites the old section, so the agent
can tell the user what the change affects before touching the analysis.
"""

from __future__ import annotations

import difflib
from typing import Any, Iterator

from .doc import Part, number_of, section_refs, split_sections

SIMILAR = 0.6  # text similarity above which two leftover sections count as one that changed
TEXT_LIMIT = 80
# Lists whose items carry the IDs people know them by; a citation inside one belongs to that item.
OWNED = {"features": "id", "flows": "id", "questions": "id", "release": "id",
         "backend.apis": "id", "backend.tables": "name", "backend.configs": "key"}
TEXT_KEYS = ("text", "name", "title", "rule", "when", "does", "why")


def _name(p: Part) -> str:
    """The heading without its number: what stays the same when a section moves."""
    num = number_of(p.heading)
    return " ".join((num[1] if num else p.heading).split())


def _whole(p: Part) -> str:
    return "\n".join([_name(p)] + p.body)


def _label(p: Part) -> str:
    return "§%s %s" % (p.section.id, p.section.title)


def _pairs(old: list[Part], new: list[Part]) -> dict[int, int]:
    """new index -> old index for the sections that are the same section in both versions."""
    pairs: dict[int, int] = {}
    used: set[int] = set()

    def take(j: int, i: int) -> None:
        pairs[j] = i
        used.add(i)

    def free_new() -> Iterator[int]:
        return (j for j in range(len(new)) if j not in pairs)

    # 1. Same heading and text; the same number first.
    for same_number in (True, False):
        for j in list(free_new()):
            for i, o in enumerate(old):
                if i not in used and _whole(o) == _whole(new[j]) and (
                        not same_number or o.section.id == new[j].section.id):
                    take(j, i)
                    break
    # 2 and 3. Same heading, under the same number first. Paragraphs have no heading.
    for same_number in (True, False):
        for j in list(free_new()):
            if not _name(new[j]):
                continue
            for i, o in enumerate(old):
                if i not in used and _name(o) == _name(new[j]) and (
                        not same_number or o.section.id == new[j].section.id):
                    take(j, i)
                    break
    # 4. Similar heading and text, best pairs first.
    scores = []
    for j in free_new():
        for i, o in enumerate(old):
            if i not in used:
                ratio = difflib.SequenceMatcher(None, _whole(o), _whole(new[j]), autojunk=False).ratio()
                if ratio >= SIMILAR:
                    scores.append((ratio, j, i))
    for _, j, i in sorted(scores, reverse=True):
        if j not in pairs and i not in used:
            take(j, i)
    return pairs


def _lines(old: list[str], new: list[str]) -> tuple[list[str], list[str]]:
    """The lines only the old version has, and the lines only the new one has."""
    was: list[str] = []
    now: list[str] = []
    sm = difflib.SequenceMatcher(None, old, new, autojunk=False)
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag != "equal":
            was += old[i1:i2]
            now += new[j1:j2]
    return was, now


def compare_docs(old_text: str, new_text: str) -> dict[str, Any]:
    """What changed between two versions of the document.

    {"head": {"was": [...], "now": [...]} or None,   # lines before the first section
     "sections": [{"change": "modified" | "moved" | "added" | "removed",
                   "section": "§3.6 候补报名", "old_section": "§2.4 …",  # whichever apply
                   "was": [lines], "now": [lines], "old_id": "2.4"}, …]}

    Sections are listed in the new version's order; a removed one stays where it was.
    """
    old_head, old = split_sections(old_text)
    new_head, new = split_sections(new_text)
    pairs = _pairs(old, new)
    paired_old = set(pairs.values())
    out: list[dict[str, Any]] = []
    next_old = 0

    def removed_before(limit: int) -> None:
        nonlocal next_old
        while next_old < limit:
            if next_old not in paired_old:
                o = old[next_old]
                out.append({"change": "removed", "old_section": _label(o), "old_id": o.section.id,
                            "was": o.body, "now": []})
            next_old += 1

    for j, n in enumerate(new):
        i = pairs.get(j)
        if i is None:
            out.append({"change": "added", "section": _label(n), "was": [], "now": n.body})
            continue
        removed_before(i)
        next_old = max(next_old, i + 1)
        o = old[i]
        was, now = _lines(o.body, n.body)
        moved = o.section.id != n.section.id
        renamed = _name(o) != _name(n)
        if not (was or now or moved or renamed):
            continue
        entry: dict[str, Any] = {"change": "modified" if was or now or renamed else "moved", "section": _label(n)}
        if moved or renamed:
            entry["old_section"] = _label(o)
        entry.update(was=was, now=now, old_id=o.section.id)
        out.append(entry)
    removed_before(len(old))

    was, now = _lines(old_head, new_head)
    return {"head": {"was": was, "now": now} if was or now else None, "sections": out}


def _short(text: str) -> str:
    text = " ".join(str(text).split())
    return text if len(text) <= TEXT_LIMIT else text[: TEXT_LIMIT - 1] + "…"


def _citations(node: Any, where: str = "", owner: str = "", removed: bool = False,
               parent: str = "") -> Iterator[tuple[str, str, str, Any]]:
    """(where, owner ID, src, the citing object) for every `src` outside removed items."""
    if isinstance(node, dict):
        removed = removed or "removed" in node
        if removed:
            return
        if isinstance(node.get("src"), str):
            yield where, owner, node["src"], node
        for key, value in node.items():
            if key != "src":
                path = "%s.%s" % (where, key) if where else key
                yield from _citations(value, path, owner, removed, path)
    elif isinstance(node, list):
        key = OWNED.get(parent)
        for i, item in enumerate(node):
            label = next((item[k] for k in ("id", "key", "name") if isinstance(item, dict)
                          and isinstance(item.get(k), str) and item[k]), None)
            mine = item.get(key) if key and isinstance(item, dict) and isinstance(item.get(key), str) else None
            yield from _citations(item, "%s[%s]" % (where, label or i), mine or owner, removed, "")


def _text(node: dict[str, Any]) -> str:
    for key in TEXT_KEYS:
        if isinstance(node.get(key), str) and node[key]:
            return _short(node[key])
    return ""


def impact(analysis: dict[str, Any], section_id: str) -> dict[str, Any]:
    """What in the analysis cites a section: each citation, the items they belong to, and those items' APIs."""
    cited = []
    items: list[str] = []
    for where, owner, src, node in _citations(analysis):
        if section_id in section_refs(src):
            cited.append({"where": where, "text": _text(node)})
            if owner and owner not in items:
                items.append(owner)
    features = {f.get("id"): f for f in analysis.get("features") or [] if isinstance(f, dict)}
    apis: list[str] = []
    for item in items:
        for api in (features.get(item) or {}).get("apis") or []:
            if api not in apis:
                apis.append(api)
    return {"cited_by": cited, "items": items, "apis": apis}


def with_impact(changes: dict[str, Any], analysis: dict[str, Any] | None) -> dict[str, Any]:
    """Add to each changed section what in the analysis cites it (nothing for added sections)."""
    for entry in changes["sections"]:
        old_id = entry.pop("old_id", None)
        if analysis is not None and old_id is not None:
            entry.update(impact(analysis, old_id))
    return changes

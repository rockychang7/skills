"""Compare two versions of an analysis item by item, for change marks on pages.

`compare` is for the brief; `compare_backend` and `compare_release` are the
same for the backend plan and the release checklist.

Items with IDs (features, questions, flows and their steps) are matched by ID.
Lists without IDs (rules, examples, terms, …) are matched by content: equal
items are unchanged, similar ones in the same place count as modified (old
text kept), the rest are added or removed.

The result is what the page templates read:

    {"items": {"feature:C04": "modify", "step:P1:s7": "add", …},
     "lists": {"feature:C04:rules": [{"s": "modify", "item": …, "old": …}, …], …},
     "old": {"feature:C04": {"summary": "the summary before"}, …},   # changed names and summaries
     "removed_steps": {"P1": [step, …]},
     "total": 28, "add": 13, "modify": 12, "remove": 3,
     "new_changes": 9}        # change notes added since the old version
"""

from __future__ import annotations

import difflib
import json
from typing import Any

from .sql import databases

SIMILAR = 0.4  # text similarity above which a replaced item counts as modified
FEATURE_LISTS = ("rules", "acceptance", "impact")
PLAIN_LISTS = ("terms", "confusions", "states", "inputs", "out_of_scope")


def _dump(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def _text(x: Any) -> str:
    if isinstance(x, str):
        return x
    if isinstance(x, dict):
        for key in ("text", "means", "rule", "when", "diff"):
            if isinstance(x.get(key), str):
                return x[key]
    return _dump(x)


def list_diff(old: list[Any] | None, new: list[Any] | None) -> list[dict[str, Any]]:
    """Entries in display order; removed items stay where they were."""
    old, new = old or [], new or []
    sm = difflib.SequenceMatcher(None, [_dump(x) for x in old], [_dump(x) for x in new], autojunk=False)
    out: list[dict[str, Any]] = []
    for tag, i1, i2, j1, j2 in sm.get_opcodes():
        if tag == "equal":
            out += [{"s": "same", "item": new[j]} for j in range(j1, j2)]
        elif tag == "insert":
            out += [{"s": "add", "item": new[j]} for j in range(j1, j2)]
        elif tag == "delete":
            out += [{"s": "remove", "old": old[i]} for i in range(i1, i2)]
        else:
            used: set[int] = set()
            pairs: dict[int, int] = {}
            for j in range(j1, j2):
                best, pick = 0.0, None
                for i in range(i1, i2):
                    if i not in used:
                        ratio = difflib.SequenceMatcher(None, _text(old[i]), _text(new[j])).ratio()
                        if ratio > best:
                            best, pick = ratio, i
                if pick is not None and best >= SIMILAR:
                    pairs[j] = pick
                    used.add(pick)
            out += [{"s": "remove", "old": old[i]} for i in range(i1, i2) if i not in used]
            out += [{"s": "modify", "item": new[j], "old": old[pairs[j]]} if j in pairs else {"s": "add", "item": new[j]}
                    for j in range(j1, j2)]
    return out


def _by_id(items: Any, key: str = "id") -> dict[str, dict[str, Any]]:
    return {x[key]: x for x in items or [] if isinstance(x, dict) and key in x}


def compare(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    items: dict[str, str] = {}
    lists: dict[str, list[dict[str, Any]]] = {}
    olds: dict[str, dict[str, Any]] = {}
    removed_steps: dict[str, list[dict[str, Any]]] = {}
    count = {"add": 0, "modify": 0, "remove": 0}

    def hit(key: str, s: str) -> None:
        items[key] = s
        count[s] += 1

    def note(key: str, entries: list[dict[str, Any]]) -> bool:
        changed = [e for e in entries if e["s"] != "same"]
        if changed:
            lists[key] = entries
            for e in changed:
                count[e["s"]] += 1
        return bool(changed)

    old_features = _by_id(old.get("features"))
    for f in new.get("features") or []:
        before = old_features.get(f.get("id"))
        key = "feature:%s" % f.get("id")
        if before is None:
            hit(key, "add")
        elif f.get("removed") and not before.get("removed"):
            hit(key, "remove")
        elif not f.get("removed"):
            changed = False
            if (f.get("name"), f.get("summary")) != (before.get("name"), before.get("summary")):
                count["modify"] += 1
                changed = True
                olds[key] = {k: before.get(k) for k in ("name", "summary") if before.get(k) != f.get(k)}
            for part in FEATURE_LISTS:
                changed = note("%s:%s" % (key, part), list_diff(before.get(part), f.get(part))) or changed
            if changed:
                items[key] = "modify"

    old_questions = _by_id(old.get("questions"))
    for q in new.get("questions") or []:
        before = old_questions.get(q.get("id"))
        if before is None:
            hit("question:%s" % q.get("id"), "add")
        elif _dump(before) != _dump(q):
            hit("question:%s" % q.get("id"), "modify")

    old_flows = _by_id(old.get("flows"))
    for fw in new.get("flows") or []:
        before = old_flows.get(fw.get("id"))
        if before is None:
            hit("flow:%s" % fw.get("id"), "add")
            continue
        if (fw.get("name"), fw.get("summary")) != (before.get("name"), before.get("summary")):
            hit("flow:%s" % fw.get("id"), "modify")
            olds["flow:%s" % fw.get("id")] = {k: before.get(k) for k in ("name", "summary") if before.get(k) != fw.get(k)}
        old_steps = _by_id(before.get("steps"))
        new_ids = set()
        for s in fw.get("steps") or []:
            new_ids.add(s.get("id"))
            key = "step:%s:%s" % (fw.get("id"), s.get("id"))
            prev = old_steps.get(s.get("id"))
            if prev is None:
                hit(key, "add")
            elif _dump(prev) != _dump(s):
                hit(key, "modify")
        gone = [s for s in before.get("steps") or [] if s.get("id") not in new_ids]
        if gone:
            removed_steps[fw.get("id")] = gone
            count["remove"] += len(gone)

    for part in PLAIN_LISTS:
        note(part, list_diff(old.get(part), new.get(part)))

    return {
        "items": items,
        "lists": lists,
        "old": olds,
        "removed_steps": removed_steps,
        "total": sum(count.values()),
        **count,
        "new_changes": len(new_notes(old, new)),
    }


def new_notes(old: dict[str, Any], new: dict[str, Any]) -> list[dict[str, Any]]:
    """Change notes added since `old`: the log is newest first and append-only."""
    seen = {_dump(c) for c in old.get("changes") or []}
    out = []
    for c in new.get("changes") or []:
        if _dump(c) in seen:
            break
        out.append(c)
    return out


def release_keys(analysis: dict[str, Any]) -> set[str]:
    """Release item IDs, config keys, table names and data tables: what the release checklist shows."""
    be = analysis.get("backend") or {}
    return ({x.get("id") for x in analysis.get("release") or []} | {x.get("key") for x in be.get("configs") or []}
            | {x.get("name") for x in be.get("tables") or []} | {x.get("table") for x in be.get("data") or []}) - {None}


def release_notes(analysis: dict[str, Any], notes: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """The change notes (all, or `notes`) that touch what the release checklist shows."""
    keys = release_keys(analysis)
    return [c for c in (analysis.get("changes") or [] if notes is None else notes)
            if keys & set(c.get("refs") or [])]


def compare_release(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Change marks for the release checklist: its items, configs, and the SQL step of each database."""
    items: dict[str, str] = {}
    count = {"add": 0, "modify": 0, "remove": 0}

    def hit(key: str, s: str) -> None:
        items[key] = s
        count[s] += 1

    def by_key(new_items: Any, old_items: Any, key: str, prefix: str) -> None:
        before = _by_id(old_items, key)
        for x in new_items or []:
            o = before.get(x.get(key))
            if o is None:
                hit(prefix + str(x.get(key)), "add")
            elif x.get("removed") and not o.get("removed"):
                hit(prefix + str(x.get(key)), "remove")
            elif not x.get("removed") and _dump(o) != _dump(x):
                hit(prefix + str(x.get(key)), "modify")

    ob, nb = old.get("backend") or {}, new.get("backend") or {}
    by_key(new.get("release"), old.get("release"), "id", "release:")
    by_key(nb.get("configs"), ob.get("configs"), "key", "config:")

    def db_part(analysis: dict[str, Any], db: str) -> str:
        be = analysis.get("backend") or {}
        return _dump([x for x in be.get("tables") or [] if (x.get("db") or "") == db]
                     + [x for x in be.get("data") or [] if (x.get("db") or "") == db])

    before = databases(old)
    for db in databases(new):
        if db not in before:
            hit("sql:" + db, "add")
        elif db_part(old, db) != db_part(new, db):
            hit("sql:" + db, "modify")

    return {"items": items, "total": sum(count.values()), **count,
            "new_changes": len(release_notes(new, new_notes(old, new)))}


API_FIELDS = ("name", "kind", "internal", "side", "path", "does", "now", "where", "depends")


def backend_keys(analysis: dict[str, Any]) -> set[str]:
    """Every ID, table name and config key the backend part has, for picking change notes."""
    be = analysis.get("backend") or {}
    return ({x.get("id") for x in be.get("apis") or []} | {x.get("name") for x in be.get("tables") or []}
            | {x.get("key") for x in be.get("configs") or []} | {x.get("table") for x in be.get("data") or []}) - {None}


def backend_notes(analysis: dict[str, Any], notes: list[dict[str, Any]] | None = None) -> list[dict[str, Any]]:
    """The change notes (all, or `notes`) that touch the backend part."""
    keys = backend_keys(analysis)
    return [c for c in (analysis.get("changes") or [] if notes is None else notes)
            if keys & set(c.get("refs") or [])]


def compare_backend(old: dict[str, Any], new: dict[str, Any]) -> dict[str, Any]:
    """Change marks for the backend plan, in the shape `compare` returns.

    Owner and status are progress, not requirement changes: they never count.
    `old` holds an item's previous one-line texts ("api:C2": {"does": …}), so
    the page can show what it was.
    """
    items: dict[str, str] = {}
    lists: dict[str, list[dict[str, Any]]] = {}
    olds: dict[str, dict[str, Any]] = {}
    heads: list[str] = []  # APIs whose own fields changed, not only their todo / online lines
    count = {"add": 0, "modify": 0, "remove": 0}
    ob, nb = old.get("backend") or {}, new.get("backend") or {}

    def hit(key: str, s: str) -> None:
        items[key] = s
        count[s] += 1

    def note(key: str, entries: list[dict[str, Any]], counted: bool = True) -> bool:
        changed = [e for e in entries if e["s"] != "same"]
        if changed:
            lists[key] = entries
            if counted:
                for e in changed:
                    count[e["s"]] += 1
        return bool(changed)

    def removed_now(x: dict[str, Any], before: dict[str, Any]) -> bool:
        return bool(x.get("removed")) and not before.get("removed")

    old_apis = _by_id(ob.get("apis"))
    for x in nb.get("apis") or []:
        before, key = old_apis.get(x.get("id")), "api:%s" % x.get("id")
        if before is None:
            hit(key, "add")
        elif removed_now(x, before):
            hit(key, "remove")
        elif not x.get("removed"):
            changed = False
            if any(_dump(before.get(f)) != _dump(x.get(f)) for f in API_FIELDS):
                count["modify"] += 1
                changed = True
                heads.append(key)
                was = {f: before[f] for f in ("does", "where", "now") if before.get(f) and before.get(f) != x.get(f)}
                if was:
                    olds[key] = was
            for part in ("todo", "online"):
                changed = note("%s:%s" % (key, part), list_diff(before.get(part), x.get(part))) or changed
            if changed:
                items[key] = "modify"

    old_tables = _by_id(ob.get("tables"), "name")
    for x in nb.get("tables") or []:
        before, key = old_tables.get(x.get("name")), "table:%s" % x.get("name")
        if before is None:
            hit(key, "add")
        elif removed_now(x, before):
            hit(key, "remove")
        elif not x.get("removed") and _dump(before) != _dump(x):
            hit(key, "modify")
            # New patches are shown on the table, not counted on their own.
            note(key + ":patches", list_diff(before.get("patches"), x.get("patches")), counted=False)

    old_configs = _by_id(ob.get("configs"), "key")
    for x in nb.get("configs") or []:
        before, key = old_configs.get(x.get("key")), "config:%s" % x.get("key")
        if before is None:
            hit(key, "add")
        elif removed_now(x, before):
            hit(key, "remove")
        elif not x.get("removed") and _dump(before) != _dump(x):
            hit(key, "modify")

    # Data changes have no ID: one that is not in the old version word for word is new.
    old_data = {_dump(d) for d in ob.get("data") or []}
    for i, d in enumerate(nb.get("data") or []):
        if _dump(d) not in old_data:
            hit("data:%d" % i, "add")

    note("risks", list_diff(ob.get("risks"), nb.get("risks")))

    return {
        "items": items,
        "lists": lists,
        "old": olds,
        "heads": heads,
        "total": sum(count.values()),
        **count,
        "new_changes": len(backend_notes(new, new_notes(old, new))),
    }

"""Compare two versions of an analysis item by item, for change marks on pages.

Items with IDs (features, questions, flows and their steps) are matched by ID.
Lists without IDs (rules, examples, terms, …) are matched by content: equal
items are unchanged, similar ones in the same place count as modified (old
text kept), the rest are added or removed.

The result is what the page templates read:

    {"items": {"feature:C04": "modify", "step:P1:s7": "add", …},
     "lists": {"feature:C04:rules": [{"s": "modify", "item": …, "old": …}, …], …},
     "removed_steps": {"P1": [step, …]},
     "total": 28, "add": 13, "modify": 12, "remove": 3,
     "new_changes": 9}        # change notes added since the old version
"""

from __future__ import annotations

import difflib
import json
from typing import Any

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

    old_notes = {_dump(c) for c in old.get("changes") or []}
    new_changes = 0
    for c in new.get("changes") or []:
        if _dump(c) in old_notes:
            break
        new_changes += 1

    return {
        "items": items,
        "lists": lists,
        "removed_steps": removed_steps,
        "total": sum(count.values()),
        **count,
        "new_changes": new_changes,
    }

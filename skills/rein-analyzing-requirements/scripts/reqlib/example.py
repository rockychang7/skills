"""The format sample printed by `req.py example`.

The full made-up example (assets/examples/activity-signup) is large, so the
command prints a trimmed copy of its latest version: one or two items per
block, chosen to show every kind of field once. References to items that were
left out are dropped, so the sample still passes `check`.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

EXAMPLE_DIR = Path(__file__).resolve().parents[2] / "assets" / "examples" / "activity-signup"
FULL_ANALYSIS = "analysis-v10.json"
FULL_FRONTEND = "frontend.json"
SAMPLE_DOC = "doc-v2.md"  # the document the sample's section numbers refer to

# Items kept in the analysis sample, by ID (tables by name, configs by key).
KEEP = {
    "features": ["C04"],  # prd with src and q, prd citing two sections, ai, ask
    "apis": ["B1", "C4"],  # modify, new
    "tables": ["activity"],  # alter, with patches and rollback
    "configs": ["activity.signup.enabled"],
    "release": ["R3"],
    "questions": ["Q01", "Q04"],  # applied with a note, open
    "flows": ["P2"],  # decisions with conditions, end steps, a step that goes on by default
}
FIRST = {"terms": 1, "states": 1, "inputs": 1, "out_of_scope": 1, "risks": 1, "data": 1}
LIST_CAP = 2  # string lists inside kept items (todo, acceptance, …) are cut to this
KEEP_FRONTEND = {"clients": ["c"], "apis": ["C1", "C2"], "rows": 3, "error_codes": 2, "changes": 2}
NOTE = "Format sample from a made-up requirement. Copy the shape and the level of detail, never the content."


def _load(name: str) -> Any:
    return json.loads((EXAMPLE_DIR / name).read_text(encoding="utf-8"))


def _pick(items: list[dict[str, Any]], key: str, keep: list[str]) -> list[dict[str, Any]]:
    return [i for i in items if i.get(key) in keep]


def _only(values: list[str], allowed: set[str]) -> list[str]:
    return [v for v in values if v in allowed]


def _cap_lists(item: dict[str, Any], keys: tuple[str, ...]) -> None:
    for key in keys:
        if key in item:
            item[key] = item[key][:LIST_CAP]


def analysis_sample() -> dict[str, Any]:
    a = copy.deepcopy(_load(FULL_ANALYSIS))
    b = a["backend"]
    a["features"] = _pick(a["features"], "id", KEEP["features"])
    b["apis"] = _pick(b["apis"], "id", KEEP["apis"])
    b["tables"] = _pick(b["tables"], "name", KEEP["tables"])
    b["configs"] = _pick(b["configs"], "key", KEEP["configs"])
    a["release"] = _pick(a["release"], "id", KEEP["release"])
    a["questions"] = _pick(a["questions"], "id", KEEP["questions"])
    a["flows"] = _pick(a["flows"], "id", KEEP["flows"])
    for key, n in FIRST.items():
        holder = b if key in ("risks", "data") else a
        holder[key] = holder[key][:n]

    feature_ids = {f["id"] for f in a["features"]}
    api_ids = {x["id"] for x in b["apis"]}
    question_ids = {q["id"] for q in a["questions"]}
    known = (feature_ids | api_ids | question_ids | {r["id"] for r in a["release"]}
             | {t["name"] for t in b["tables"]} | {c["key"] for c in b["configs"]} | {f["id"] for f in a["flows"]})

    for fw in a["flows"]:
        for step in fw["steps"]:
            if "features" in step:
                step["features"] = _only(step["features"], feature_ids)
                if not step["features"]:
                    del step["features"]
            if step.get("q") and step["q"] not in question_ids:
                del step["q"]

    for f in a["features"]:
        f["apis"] = _only(f.get("apis", []), api_ids)
        f["rules"] = [r for r in f["rules"] if "q" not in r or r["q"] in question_ids]
        _cap_lists(f, ("acceptance", "impact"))
    for x in b["apis"]:
        _cap_lists(x, ("todo", "online"))
        if "depends" in x:
            x["depends"] = _only(x["depends"], api_ids)
            if not x["depends"]:
                del x["depends"]
    for r in b["risks"]:
        if "apis" in r:
            r["apis"] = _only(r["apis"], api_ids)
            if not r["apis"]:
                del r["apis"]
    for q in a["questions"]:
        q["affects"] = _only(q.get("affects", []), feature_ids | api_ids)
        if not q["affects"]:
            del q["affects"]
    changes = []
    for c in a["changes"]:
        refs = _only(c["refs"], known)
        if refs:
            changes.append(dict(c, refs=refs))
    a["changes"] = changes[:2]
    return a


def frontend_sample() -> dict[str, Any]:
    f = copy.deepcopy(_load(FULL_FRONTEND))
    keep = KEEP_FRONTEND
    f["clients"] = [c for c in f["clients"] if c["id"] in keep["clients"]]
    for c in f["clients"]:
        c["apis"] = [x for x in c["apis"] if x["id"] in keep["apis"]]
        api_ids = {x["id"] for x in c["apis"]}
        for n in c["flow"]["nodes"]:
            n["calls"] = _only(n.get("calls", []), api_ids)
        nodes = [n for n in c["flow"]["nodes"] if n["calls"]]
        node_ids = {n["id"] for n in nodes}
        c["flow"] = {
            "nodes": nodes,
            "edges": [e for e in c["flow"]["edges"] if e["from"] in node_ids and e["to"] in node_ids],
        }
        for g in c.get("guides", []):
            g["rows"] = g["rows"][: keep["rows"]]
    f["error_codes"] = f["error_codes"][: keep["error_codes"]]
    known = {x["id"] for c in f["clients"] for x in c["apis"]} | {
        g["id"] for c in f["clients"] for g in c.get("guides", [])
    }
    f["changes"] = [c for c in f["changes"] if set(c["refs"]) <= known][: keep["changes"]]
    return f


def full_analysis() -> dict[str, Any]:
    """The untrimmed latest analysis the sample comes from (frontend checks need it)."""
    return _load(FULL_ANALYSIS)

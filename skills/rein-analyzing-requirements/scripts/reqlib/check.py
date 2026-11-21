"""Checks for analysis.json and frontend.json: format, IDs and references.

Two passes:
1. Shape: every object is compared with a field table (SPEC below):
   required fields, types, allowed values, unknown fields.
2. Meaning: ID patterns, duplicates, references between items, section
   numbers, and the few rules that depend on other fields.

The second pass reads the data defensively: anything of the wrong shape was
already reported by the first pass and is skipped here.
"""

from __future__ import annotations

import re
from typing import Any, Iterator

from .output import issue

# Field notation: "str", "int", "bool", "strs" (list of strings), "map" (object
# of scalars), "any", "rows" (list of lists of strings), "a|b|c" (one of these
# strings), "[name]" (list of objects of type name), "name" (object of type
# name). A trailing "!" means required; required lists must not be empty.
ANALYSIS_SPEC: dict[str, dict[str, str]] = {
    "root": {
        "format": "int!", "meta": "meta!", "brief": "brief!", "roles": "[role]!", "clients": "[client]",
        "flows": "[process]!", "terms": "[term]", "confusions": "[confusion]", "states": "[state]",
        "inputs": "[input]", "out_of_scope": "[scope]", "skipped_sections": "[skipped]",
        "prototypes": "prototypes", "features": "[feature]!", "backend": "backend", "release": "[release]",
        "questions": "[question]", "changes": "[change]", "confirmations": "[confirmation]",
    },
    "meta": {"title": "str!", "doc_version": "str", "code_commit": "str!", "source_v": "int!"},
    "brief": {"what": "str!", "value": "str"},
    "role": {"id": "str!", "name": "str!", "does": "str!"},
    "client": {"id": "str!", "name": "str!", "where": "str"},
    "process": {"id": "str!", "name": "str!", "summary": "str", "steps": "[step]!"},
    "step": {
        "id": "str!", "role": "str!", "kind": "decision|end", "text": "str!", "src": "str", "features": "strs",
        "q": "str", "next": "any",
    },
    "term": {"term": "str!", "means": "str!"},
    "confusion": {"a": "str!", "b": "str!", "diff": "str!"},
    "state": {"of": "str!", "from": "str!", "to": "str!", "when": "str!", "then": "str", "src": "str"},
    "input": {"where": "str!", "name": "str!", "rule": "str!", "src": "str"},
    "scope": {"text": "str!", "src": "str"},
    "skipped": {"src": "str!", "why": "str!"},
    "prototypes": {"links": "[link]", "images": "[image]"},
    "link": {"title": "str!", "url": "str!"},
    "image": {"file": "str!", "caption": "str!"},
    "feature": {
        "id": "str!", "side": "str!", "name": "str!", "summary": "str!", "rules": "[rule]!",
        "acceptance": "strs!", "impact": "strs", "apis": "strs", "removed": "str",
    },
    "rule": {"kind": "prd|code|ai|ask!", "text": "str!", "src": "str", "q": "str", "path": "str"},
    "backend": {"apis": "[api]", "tables": "[table]", "data": "[data]", "configs": "[config]", "risks": "[risk]"},
    "api": {
        "id": "str!", "side": "str!", "internal": "bool", "kind": "new|modify!", "name": "str!", "path": "str",
        "does": "str!", "now": "str", "where": "str!", "todo": "strs!", "online": "strs", "owner": "str",
        "status": "todo|doing|testing|done", "depends": "strs", "removed": "str",
    },
    "table": {
        "name": "str!", "kind": "new|alter!", "title": "str!", "does": "str!", "sql": "str!", "patches": "strs",
        "init": "strs", "rollback": "str", "db": "str", "removed": "str",
    },
    "data": {
        "table": "str!", "kind": "insert|update|delete!", "does": "str!", "sql": "str!", "rollback": "str",
        "check": "str!", "db": "str",
    },
    "config": {
        "key": "str!", "kind": "new|modify!", "values": "map!", "old": "str", "does": "str!", "src": "str",
        "removed": "str",
    },
    "risk": {"text": "str!", "apis": "strs"},
    "release": {
        "id": "str!", "stage": "before|deploy|after|rollback!", "type": "deploy|config|other!", "text": "str!",
        "detail": "str", "verify": "str", "src": "str", "removed": "str",
    },
    "question": {
        "id": "str!", "priority": "P0|P1|P2!", "status": "open|decided|applied|superseded!", "title": "str!",
        "quotes": "[quote]!", "why": "str!", "affects": "strs", "options": "[option]!", "owner": "str",
        "answer": "answer", "superseded_by": "str",
    },
    "quote": {"src": "str!", "text": "str!"},
    "option": {"key": "str!", "text": "str!", "reason": "str", "recommended": "bool"},
    "answer": {"choice": "str!", "note": "str", "at": "str!", "by": "str!"},
    "change": {"type": "add|modify|remove!", "text": "str!", "refs": "strs!", "src": "str"},
    "confirmation": {"code": "str!", "where": "str!", "note": "str!", "at": "str!"},
}

FRONTEND_SPEC: dict[str, dict[str, str]] = {
    "root": {"format": "int!", "conventions": "strs", "clients": "[fclient]!", "error_codes": "[errcode]",
             "changes": "[change]"},
    "fclient": {"id": "str!", "name": "str!", "status": "todo|doing|done!", "conventions": "strs",
                "flow": "flow!", "apis": "[fapi]!", "guides": "[guide]"},
    "flow": {"nodes": "[node]!", "edges": "[edge]"},
    "node": {"id": "str!", "name": "str!", "calls": "strs"},
    "edge": {"from": "str!", "to": "str!", "label": "str!", "back": "bool"},
    "fapi": {"id": "str!", "contract": "str", "change": "str", "facts": "[fact]", "frontend": "strs",
             "example": "any", "fields": "fields", "removed": "str"},
    "fact": {"k": "str!", "v": "str!"},
    "fields": {"params": "[field]", "response": "[field]"},
    "field": {"name": "str!", "type": "str!", "required": "bool", "desc": "str", "children": "[field]"},
    "guide": {"id": "str!", "title": "str!", "head": "strs!", "rows": "rows!", "notes": "strs"},
    "errcode": {"code": "str!", "msg": "str!", "handle": "str!"},
    "change": ANALYSIS_SPEC["change"],
}

FLOW_ID = re.compile(r"^P\d+$")
CLIENT_ID = re.compile(r"^[a-z]+$")
RESERVED_CLIENT_IDS = {"n", "q", "r", "s"}
NO_CLIENT = "s"
QUESTION_ID = re.compile(r"^Q\d{2}$")
RELEASE_ID = re.compile(r"^R\d+$")
GUIDE_ID = re.compile(r"^G\d+$")
SECTION_REF = re.compile(r"§\s*(\d+(?:\.\d+)*)")
WHERE_CLAUSE = re.compile(r"\bwhere\b", re.IGNORECASE)
# Technical words that should not reach the brief, which product, frontend
# and backend all read: routes ("POST /order/review", "/order/list") and
# snake_case table names. Paths inside URLs do not count.
ROUTE = re.compile(r"\b(?:GET|POST|PUT|PATCH|DELETE)\s+/\S*|(?<![\w.:/])/[A-Za-z][\w-]*(?:/[\w{}:-]+)+")
ACCEPTANCE_COLON = re.compile(r"^.+?[：:]\s*.+$")
TYPE_NAMES = {"str": "a string", "int": "a whole number", "bool": "true or false", "strs": "a list of strings",
              "map": "an object of plain values", "rows": "a list of rows (lists of strings)"}


class Issues:
    def __init__(self) -> None:
        self.items: list[dict[str, str]] = []

    def add(self, code: str, level: str, where: str, msg: str, hint: str = "") -> None:
        self.items.append(issue(code, level, msg, hint=hint, where=where))


# ---------------------------------------------------------------- shape pass


def _label(item: Any, index: int) -> str:
    if isinstance(item, dict):
        for key in ("id", "key", "name"):
            if isinstance(item.get(key), str) and item[key]:
                return item[key]
    return str(index)


def _is_type(value: Any, kind: str) -> bool:
    if kind == "str":
        return isinstance(value, str)
    if kind == "int":
        return isinstance(value, int) and not isinstance(value, bool)
    if kind == "bool":
        return isinstance(value, bool)
    if kind == "strs":
        return isinstance(value, list) and all(isinstance(v, str) for v in value)
    if kind == "map":
        return isinstance(value, dict) and all(isinstance(v, (str, int, float, bool)) for v in value.values())
    if kind == "rows":
        return isinstance(value, list) and all(
            isinstance(r, list) and all(isinstance(c, str) for c in r) for r in value
        )
    return True  # "any"


def _shape(spec: dict[str, dict[str, str]], obj: Any, type_name: str, where: str, out: Issues) -> None:
    fields = spec[type_name]
    if not isinstance(obj, dict):
        out.add("format.type", "error", where or "(file)", "Expected an object.")
        return
    prefix = where + "." if where else ""
    for key in obj:
        if key not in fields:
            out.add("format.unknown-field", "warn", prefix + key, "Unknown field %r." % key,
                    hint="Check the spelling; allowed here: %s." % ", ".join(fields))
    for key, notation in fields.items():
        required = notation.endswith("!")
        kind = notation.rstrip("!")
        here = prefix + key
        if key not in obj:
            if required:
                out.add("format.missing", "error", here, "Required field %r is missing." % key)
            continue
        value = obj[key]
        if kind.startswith("["):
            item_type = kind[1:-1]
            if not isinstance(value, list):
                out.add("format.type", "error", here, "Expected a list.")
                continue
            if required and not value:
                out.add("format.empty", "error", here, "This list must not be empty.")
            for i, item in enumerate(value):
                _shape(spec, item, item_type, "%s[%s]" % (here, _label(item, i)), out)
        elif kind in spec:
            _shape(spec, value, kind, here, out)
        elif "|" in kind:
            allowed = kind.split("|")
            if value not in allowed:
                out.add("format.enum", "error", here, "Value %r is not allowed." % (value,),
                        hint="Use one of: %s." % ", ".join(allowed))
        elif not _is_type(value, kind):
            out.add("format.type", "error", here, "Expected %s." % TYPE_NAMES.get(kind, kind))
        elif required and isinstance(value, (str, list)) and not (value.strip() if isinstance(value, str) else value):
            out.add("format.empty", "error", here, "Must not be empty.")


# -------------------------------------------------------------- helpers


def _dicts(value: Any) -> list[dict[str, Any]]:
    return [v for v in value if isinstance(v, dict)] if isinstance(value, list) else []


def _strs(value: Any) -> list[str]:
    return [v for v in value if isinstance(v, str)] if isinstance(value, list) else []


def _text(obj: dict[str, Any], key: str) -> str:
    value = obj.get(key)
    return value if isinstance(value, str) else ""


def _duplicates(out: Issues, label: str, where: str, ids: list[str]) -> None:
    seen: set[str] = set()
    for i in ids:
        if i in seen:
            out.add("id.duplicate", "error", where, "%s %s is used more than once." % (label, i),
                    hint="IDs must be unique; give the newer one a new ID.")
        seen.add(i)


def _walk_srcs(node: Any, where: str, removed: bool = False) -> Iterator[tuple[str, str, bool]]:
    """Yield (where, src value, inside a removed item) for every `src` field."""
    if isinstance(node, dict):
        removed = removed or "removed" in node
        for key, value in node.items():
            here = "%s.%s" % (where, key) if where else key
            if key == "src" and isinstance(value, str):
                yield here, value, removed
            else:
                yield from _walk_srcs(value, here, removed)
    elif isinstance(node, list):
        for i, item in enumerate(node):
            yield from _walk_srcs(item, "%s[%s]" % (where, _label(item, i)), removed)


def section_refs(src: str) -> list[str]:
    return SECTION_REF.findall(src)


# ------------------------------------------------------------ analysis


def check_analysis(a: Any, sections: set[str], envs: list[str]) -> list[dict[str, str]]:
    """Check an analysis; `sections` are the section IDs of the latest document."""
    out = Issues()
    _shape(ANALYSIS_SPEC, a, "root", "", out)
    if not isinstance(a, dict):
        return out.items
    if "format" in a and a["format"] != 1:
        out.add("format.version", "error", "format", "Format %r is not supported." % (a["format"],),
                hint="This version of req.py reads format 1.")

    backend = a.get("backend") if isinstance(a.get("backend"), dict) else {}
    roles = _dicts(a.get("roles"))
    clients = _dicts(a.get("clients"))
    features = _dicts(a.get("features"))
    apis = _dicts(backend.get("apis"))
    tables = _dicts(backend.get("tables"))
    data = _dicts(backend.get("data"))
    configs = _dicts(backend.get("configs"))
    release = _dicts(a.get("release"))
    questions = _dicts(a.get("questions"))

    role_ids = [_text(r, "id") for r in roles]
    client_ids = [_text(c, "id") for c in clients]
    feature_ids = [_text(f, "id") for f in features]
    api_ids = [_text(x, "id") for x in apis]
    question_ids = [_text(q, "id") for q in questions]
    release_ids = [_text(r, "id") for r in release]
    table_names = [_text(t, "name") for t in tables]
    config_keys = [_text(c, "key") for c in configs]
    flow_ids = [_text(fw, "id") for fw in _dicts(a.get("flows"))]
    known = set(feature_ids + api_ids + question_ids + release_ids + table_names + config_keys + flow_ids)

    for label, where, ids in (
        ("Role", "roles", role_ids), ("Client", "clients", client_ids), ("Feature", "features", feature_ids),
        ("API", "backend.apis", api_ids), ("Question", "questions", question_ids),
        ("Release item", "release", release_ids), ("Table", "backend.tables", table_names),
        ("Config", "backend.configs", config_keys),
    ):
        _duplicates(out, label, where, [i for i in ids if i])

    for cid in client_ids:
        if cid and (not CLIENT_ID.match(cid) or cid in RESERVED_CLIENT_IDS):
            out.add("id.client", "error", "clients[%s]" % cid, "Client ID %r is not allowed." % cid,
                    hint="Use lowercase letters only, and not n, q, r or s (they start other IDs).")

    def side_ok(side: str, where: str) -> str:
        """Check a side; return the ID prefix it implies ('' if unknown)."""
        if side == NO_CLIENT:
            return "S"
        if side and side not in client_ids:
            out.add("ref.side", "error", where, "Side %r is not a client." % side,
                    hint="Use an ID from clients, or %r when no client is involved." % NO_CLIENT)
            return ""
        return side.upper()

    _duplicates(out, "Flow", "flows", [i for i in flow_ids if i])
    for fw in _dicts(a.get("flows")):
        _check_flow(fw, role_ids, feature_ids, question_ids, out)

    asked: dict[str, list[str]] = {}
    for f in features:
        fid = _text(f, "id")
        where = "features[%s]" % fid
        prefix = side_ok(_text(f, "side"), where + ".side")
        if fid and prefix and not re.fullmatch(prefix + r"\d{2}", fid):
            out.add("id.pattern", "error", where, "Feature ID %r does not match its side." % fid,
                    hint="Use %s + two digits, e.g. %s01." % (prefix, prefix))
        for api in _strs(f.get("apis")):
            if api not in api_ids:
                out.add("ref.unknown", "error", where + ".apis", "API %s is not in backend.apis." % api)
        for i, rule in enumerate(_dicts(f.get("rules"))):
            rw = "%s.rules[%d]" % (where, i)
            kind, q = _text(rule, "kind"), _text(rule, "q")
            if kind == "prd" and not (_text(rule, "src") or q):
                out.add("rule.prd-no-src", "error", rw, "A prd rule needs src (document section) or q.",
                        hint="Add the section, e.g. \"src\": \"§3.4\"; if it came from an answered question, \"q\".")
            if kind == "ask":
                if not q:
                    out.add("rule.ask-no-q", "error", rw, "An ask rule needs q, the question it waits for.")
                else:
                    asked.setdefault(q, []).append(fid)
            if q and q not in question_ids:
                out.add("ref.unknown", "error", rw + ".q", "Question %s is not in questions." % q)
        for i, example in enumerate(_strs(f.get("acceptance"))):
            if not ACCEPTANCE_COLON.match(example):
                out.add("acceptance.no-colon", "warn", "%s.acceptance[%d]" % (where, i),
                        "Acceptance example is not written as situation：expected result.",
                        hint="The brief splits it at the first colon into two columns, "
                        "e.g. \"离开始 23 小时取消：按钮置灰，提示不能取消\".")

    _check_brief_words(a, [n for n in table_names if "_" in n], out)

    for x in apis:
        xid = _text(x, "id")
        where = "backend.apis[%s]" % xid
        prefix = side_ok(_text(x, "side"), where + ".side")
        if x.get("internal") is True:
            prefix = "N"
        if xid and prefix and not re.fullmatch(prefix + r"\d+", xid):
            out.add("id.pattern", "error", where, "API ID %r does not match its side." % xid,
                    hint="Use %s + a number, e.g. %s1%s." % (
                        prefix, prefix, "" if prefix == "N" else "; internal tasks use N1, N2, …"))
        if x.get("kind") == "modify":
            if not _text(x, "path"):
                out.add("api.modify-no-path", "error", where + ".path",
                        "A modified API needs path, its real route found in the code.",
                        hint="Search the code for the existing route; never guess it.")
            if not _text(x, "now"):
                out.add("api.modify-no-now", "error", where + ".now", "A modified API needs now: what it does today.")
        if (x.get("kind") == "modify" or x.get("internal") is True) and not _strs(x.get("online")):
            out.add("api.no-online", "error", where + ".online",
                    "Modified APIs and internal tasks need online: what they touch in production.",
                    hint="Who calls it today, what old clients do, which existing data it touches. "
                    "If nothing is affected, say why.")
        for dep in _strs(x.get("depends")):
            if dep not in api_ids:
                out.add("ref.unknown", "error", where + ".depends", "API %s is not in backend.apis." % dep)

    for t in tables:
        if t.get("kind") == "alter" and not _text(t, "rollback"):
            out.add("table.alter-no-rollback", "error", "backend.tables[%s].rollback" % _text(t, "name"),
                    "Changing an existing table needs rollback.")

    for i, d in enumerate(data):
        where = "backend.data[%d]" % i
        if d.get("kind") in ("update", "delete"):
            if _text(d, "sql") and not WHERE_CLAUSE.search(_text(d, "sql")):
                out.add("data.no-where", "error", where + ".sql", "An update or delete needs a WHERE clause.")
            if not _text(d, "rollback"):
                out.add("data.no-rollback", "error", where + ".rollback",
                        "An update or delete needs rollback SQL that puts the data back.")

    for c in configs:
        where = "backend.configs[%s]" % _text(c, "key")
        values = c.get("values") if isinstance(c.get("values"), dict) else {}
        missing = [e for e in envs if e not in values]
        if values and missing:
            out.add("config.env-missing", "error", where + ".values", "No value for: %s." % ", ".join(missing),
                    hint="Every environment in the project settings needs a value (%s)." % ", ".join(envs))
        unknown = [e for e in values if e not in envs]
        if unknown:
            out.add("config.env-unknown", "warn", where + ".values",
                    "Environments not in the project settings: %s." % ", ".join(unknown),
                    hint="Known environments: %s." % ", ".join(envs))
        if c.get("kind") == "modify" and not _text(c, "old"):
            out.add("config.modify-no-old", "error", where + ".old", "A changed config needs old, its current value.")

    for i, risk in enumerate(_dicts(backend.get("risks"))):
        for api in _strs(risk.get("apis")):
            if api not in api_ids:
                out.add("ref.unknown", "error", "backend.risks[%d].apis" % i, "API %s is not in backend.apis." % api)

    for rid in release_ids:
        if rid and not RELEASE_ID.match(rid):
            out.add("id.pattern", "error", "release[%s]" % rid, "Release item ID %r is not R + a number." % rid)

    for q in questions:
        _check_question(q, question_ids, feature_ids, api_ids, asked, out)

    for i, change in enumerate(_dicts(a.get("changes"))):
        for ref in _strs(change.get("refs")):
            if ref not in known:
                out.add("ref.unknown", "error", "changes[%d].refs" % i, "%s is not an ID, table or config key." % ref)

    for where, src, removed in _walk_srcs(a, ""):
        refs = section_refs(src)
        if not refs:
            out.add("src.bad", "error", where, "src %r names no section." % src,
                    hint="Write sections as listed by new/refresh, e.g. \"§3.4\" or \"§3.4, §3.6\".")
        for ref in refs:
            if ref not in sections and not removed:
                out.add("src.unknown-section", "error", where, "§%s is not a section of the latest document." % ref,
                        hint="Use the section IDs listed by new/refresh.")

    return _apply_confirmations(out.items, _dicts(a.get("confirmations")))


def _brief_texts(a: dict[str, Any]) -> Iterator[tuple[str, str]]:
    """(where, text) for the text the brief shows that people of every role read."""
    for fw in _dicts(a.get("flows")):
        for step in _dicts(fw.get("steps")):
            yield "flows[%s].steps[%s].text" % (_text(fw, "id"), _text(step, "id")), _text(step, "text")
    for f in _dicts(a.get("features")):
        where = "features[%s]" % _text(f, "id")
        yield where + ".summary", _text(f, "summary")
        for i, rule in enumerate(_dicts(f.get("rules"))):
            yield "%s.rules[%d].text" % (where, i), _text(rule, "text")
        for key in ("acceptance", "impact"):
            for i, line in enumerate(_strs(f.get(key))):
                yield "%s.%s[%d]" % (where, key, i), line
    for q in _dicts(a.get("questions")):
        yield "questions[%s].title" % _text(q, "id"), _text(q, "title")


def _check_brief_words(a: dict[str, Any], tables: list[str], out: Issues) -> None:
    table_word = re.compile(r"(?<![\w.])(%s)(?![\w])" % "|".join(map(re.escape, tables))) if tables else None
    for where, text in _brief_texts(a):
        found = ROUTE.findall(text) + (table_word.findall(text) if table_word else [])
        if found:
            out.add("text.tech-term", "warn", where, "Technical words in text the brief shows: %s." % ", ".join(found),
                    hint="Product, frontend and backend all read the brief: say it in business words "
                    "(the page and action, the thing it stores). Routes and tables belong in backend.")


def flow_edges(steps: list[dict[str, Any]]) -> list[tuple[str, str, str, int]]:
    """(from, to, when, index of the branch) for every arrow in a flow.

    A step goes on to the next step in the list unless it has `next`; an end
    step and the last step go nowhere. Entries of `next` are step IDs or
    {"to": ID, "when": condition}. Pages draw the same arrows.
    """
    edges = []
    for i, s in enumerate(steps):
        nxt = s.get("next")
        if nxt is None:
            nxt = [steps[i + 1].get("id")] if s.get("kind") != "end" and i + 1 < len(steps) else []
        for k, n in enumerate(nxt if isinstance(nxt, list) else []):
            if isinstance(n, str):
                edges.append((_text(s, "id"), n, "", k))
            elif isinstance(n, dict) and isinstance(n.get("to"), str):
                edges.append((_text(s, "id"), n["to"], _text(n, "when"), k))
    return edges


def _check_flow(fw: dict[str, Any], role_ids: list[str], feature_ids: list[str], question_ids: list[str],
                out: Issues) -> None:
    fid = _text(fw, "id")
    where = "flows[%s]" % fid
    if fid and not FLOW_ID.match(fid):
        out.add("id.pattern", "error", where, "Flow ID %r is not P + a number." % fid)
    steps = _dicts(fw.get("steps"))
    step_ids = [_text(s, "id") for s in steps]
    _duplicates(out, "Step", where + ".steps", [i for i in step_ids if i])

    for s in steps:
        sw = "%s.steps[%s]" % (where, _text(s, "id"))
        role = _text(s, "role")
        if role and role not in role_ids:
            out.add("ref.unknown", "error", sw + ".role", "Role %r is not in roles." % role)
        for feat in _strs(s.get("features")):
            if feat not in feature_ids:
                out.add("ref.unknown", "error", sw + ".features", "Feature %s is not in features." % feat)
        if _text(s, "q") and _text(s, "q") not in question_ids:
            out.add("ref.unknown", "error", sw + ".q", "Question %s is not in questions." % s["q"])
        nxt = s.get("next")
        if nxt is not None:
            bad = not isinstance(nxt, list) or any(
                not (isinstance(n, str) or (isinstance(n, dict) and isinstance(n.get("to"), str)
                                            and set(n) <= {"to", "when"}))
                for n in nxt)
            if bad:
                out.add("format.type", "error", sw + ".next",
                        "next must be a list of step IDs or {\"to\": ID, \"when\": condition}.")
        if s.get("kind") == "end" and nxt:
            out.add("flow.end-next", "error", sw + ".next", "An end step cannot go on to other steps.",
                    hint="Remove next, or make it a normal step.")
        if s.get("kind") == "decision":
            branches = nxt if isinstance(nxt, list) else []
            if len(branches) < 2:
                out.add("flow.decision-branches", "error", sw + ".next",
                        "A decision needs at least two branches in next.",
                        hint="Write each branch as {\"to\": step ID, \"when\": condition}.")
            elif any(not (isinstance(n, dict) and _text(n, "when")) for n in branches):
                out.add("flow.branch-no-when", "error", sw + ".next",
                        "Every branch of a decision needs when: the condition for taking it.")

    edges = flow_edges(steps)
    for frm, to, _, k in edges:
        if to not in step_ids:
            out.add("ref.unknown", "error", "%s.steps[%s].next[%d]" % (where, frm, k),
                    "Step %r is not in this flow." % to)
    outs: dict[str, list[str]] = {}
    for frm, to, _, _ in edges:
        outs.setdefault(frm, []).append(to)
    state: dict[str, int] = {}

    def loops(node: str) -> bool:
        state[node] = 1
        for nxt_id in outs.get(node, []):
            if state.get(nxt_id) == 1 or (nxt_id not in state and loops(nxt_id)):
                return True
        state[node] = 2
        return False

    if any(sid not in state and loops(sid) for sid in step_ids if sid):
        out.add("flow.cycle", "warn", where, "This flow loops back to an earlier step.",
                hint="Diagrams read top to bottom; describe a retry in the step text instead of an arrow back.")


def _check_question(q: dict[str, Any], question_ids: list[str], feature_ids: list[str], api_ids: list[str],
                    asked: dict[str, list[str]], out: Issues) -> None:
    qid = _text(q, "id")
    where = "questions[%s]" % qid
    status = q.get("status")
    if qid and not QUESTION_ID.match(qid):
        out.add("id.pattern", "error", where, "Question ID %r is not Q + two digits." % qid)
    affects = _strs(q.get("affects"))
    if q.get("priority") == "P0" and not affects:
        out.add("question.p0-no-affects", "error", where + ".affects",
                "A P0 question needs affects: the features or APIs it blocks.")
    for target in affects:
        if target not in feature_ids and target not in api_ids:
            out.add("ref.unknown", "error", where + ".affects", "%s is not a feature or API." % target)
    options = _dicts(q.get("options"))
    if isinstance(q.get("options"), list) and not 2 <= len(q["options"]) <= 3:
        out.add("question.options-count", "error", where + ".options", "Give 2 or 3 options.")
    if sum(1 for o in options if o.get("recommended") is True) > 1:
        out.add("question.multi-recommended", "error", where + ".options", "At most one option can be recommended.")
    keys = [_text(o, "key") for o in options]
    _duplicates(out, "Option", where + ".options", [k for k in keys if k])
    answer = q.get("answer") if isinstance(q.get("answer"), dict) else None
    if status == "open" and answer:
        out.add("question.open-has-answer", "error", where + ".status", "An open question has an answer.",
                hint="Set status to decided, then to applied once everything it affects is updated.")
    if status in ("decided", "applied", "superseded") and not answer:
        out.add("question.no-answer", "error", where + ".answer",
                "A %s question needs answer: choice, at, by." % status)
    if answer and _text(answer, "choice") and _text(answer, "choice") not in keys:
        out.add("question.bad-choice", "warn", where + ".answer.choice",
                "Choice %r is not one of the option keys." % answer["choice"],
                hint="Fine for a free-form answer; put the person's words in note.")
    if status == "superseded":
        successor = _text(q, "superseded_by")
        if not successor:
            out.add("question.no-successor", "error", where + ".superseded_by",
                    "A superseded question needs superseded_by, the question that replaces it.")
        elif successor not in question_ids:
            out.add("ref.unknown", "error", where + ".superseded_by", "Question %s does not exist." % successor)
    waiting = asked.get(qid, [])
    if status in ("applied", "superseded") and waiting:
        out.add("question.still-asked", "error", where + ".status",
                "Marked %s, but ask rules still point to it in: %s." % (status, ", ".join(waiting)),
                hint="Rewrite those rules as prd or ai (or point them to the new question).")
    if status == "decided" and waiting:
        out.add("question.decided-not-applied", "warn", where,
                "Answered, but ask rules still point to it in: %s." % ", ".join(waiting),
                hint="Update the rules, APIs and tables it affects, then set status to applied.")


def _apply_confirmations(items: list[dict[str, str]], confirmations: list[dict[str, Any]]) -> list[dict[str, str]]:
    done = {(_text(c, "code"), _text(c, "where")) for c in confirmations}
    return [i for i in items if not (i["level"] == "confirm" and (i["code"], i["where"]) in done)]


# ------------------------------------------------------------ frontend


def check_frontend(f: Any, a: Any) -> list[dict[str, str]]:
    """Check frontend.json against the analysis it belongs to."""
    out = Issues()
    _shape(FRONTEND_SPEC, f, "root", "", out)
    if not isinstance(f, dict):
        return out.items
    if "format" in f and f["format"] != 1:
        out.add("format.version", "error", "format", "Format %r is not supported." % (f["format"],),
                hint="This version of req.py reads format 1.")

    a = a if isinstance(a, dict) else {}
    backend = a.get("backend") if isinstance(a.get("backend"), dict) else {}
    a_clients = [_text(c, "id") for c in _dicts(a.get("clients"))]
    a_apis = {_text(x, "id"): x for x in _dicts(backend.get("apis"))}

    clients = _dicts(f.get("clients"))
    all_api_ids: list[str] = []
    guide_ids: list[str] = []
    _duplicates(out, "Client", "clients", [_text(c, "id") for c in clients if _text(c, "id")])

    for c in clients:
        cid = _text(c, "id")
        where = "clients[%s]" % cid
        if cid and cid not in a_clients:
            out.add("ref.unknown", "error", where, "Client %r is not in the analysis clients." % cid)
        listed = set()
        for x in _dicts(c.get("apis")):
            xid = _text(x, "id")
            xw = "%s.apis[%s]" % (where, xid)
            all_api_ids.append(xid)
            listed.add(xid)
            source = a_apis.get(xid)
            if source is None:
                out.add("ref.unknown", "error", xw, "API %s is not in the analysis backend.apis." % xid)
                continue
            if _text(source, "side") != cid:
                out.add("frontend.wrong-client", "error", xw,
                        "API %s belongs to client %r in the analysis." % (xid, _text(source, "side")),
                        hint="List it under that client; other pages that call it name it in their calls.")
            if ("removed" in x) != ("removed" in source):
                out.add("frontend.removed-mismatch", "warn", xw,
                        "API %s is removed in one file but not the other." % xid)
            if "removed" in x:
                continue
            if not (_text(x, "contract") or isinstance(x.get("fields"), dict)):
                out.add("frontend.no-contract", "error", xw + ".contract",
                        "Give contract (METHOD /path in the API description).",
                        hint="Only when the project has no API description, write fields by hand instead.")
            for key in ("facts", "frontend", "example"):
                if key not in x:
                    out.add("format.missing", "error", "%s.%s" % (xw, key), "Required field %r is missing." % key)
            if source.get("kind") == "modify" and not _text(x, "change"):
                out.add("frontend.modify-no-change", "error", xw + ".change",
                        "API %s is modified; say what changed for the frontend." % xid)
        for xid, source in a_apis.items():
            if (_text(source, "side") == cid and xid not in listed and source.get("internal") is not True
                    and "removed" not in source):
                out.add("frontend.api-missing", "warn", where + ".apis",
                        "API %s of this client is in the analysis but not here." % xid,
                        hint="Add it, or ignore this if the frontend really never calls it.")

        flow = c.get("flow") if isinstance(c.get("flow"), dict) else {}
        nodes = _dicts(flow.get("nodes"))
        node_ids = [_text(n, "id") for n in nodes]
        _duplicates(out, "Page", where + ".flow.nodes", [n for n in node_ids if n])
        for n in nodes:
            for call in _strs(n.get("calls")):
                if call not in a_apis:
                    out.add("ref.unknown", "error", "%s.flow.nodes[%s].calls" % (where, _text(n, "id")),
                            "API %s is not in the analysis." % call)
        for i, e in enumerate(_dicts(flow.get("edges"))):
            for end in ("from", "to"):
                if _text(e, end) and _text(e, end) not in node_ids:
                    out.add("ref.unknown", "error", "%s.flow.edges[%d].%s" % (where, i, end),
                            "Page %r is not in this client's flow.nodes." % _text(e, end))

        for g in _dicts(c.get("guides")):
            gid = _text(g, "id")
            gw = "%s.guides[%s]" % (where, gid)
            guide_ids.append(gid)
            if gid and not GUIDE_ID.match(gid):
                out.add("id.pattern", "error", gw, "Guide ID %r is not G + a number." % gid)
            width = len(_strs(g.get("head")))
            for i, row in enumerate(g.get("rows") if isinstance(g.get("rows"), list) else []):
                if isinstance(row, list) and len(row) != width:
                    out.add("guide.row-length", "error", "%s.rows[%d]" % (gw, i),
                            "Row has %d cells; head has %d." % (len(row), width))

    _duplicates(out, "API", "clients[].apis", [i for i in all_api_ids if i])
    _duplicates(out, "Guide", "clients[].guides", [i for i in guide_ids if i])
    known = set(all_api_ids + guide_ids)
    for i, change in enumerate(_dicts(f.get("changes"))):
        for ref in _strs(change.get("refs")):
            if ref not in known:
                out.add("ref.unknown", "error", "changes[%d].refs" % i, "%s is not an API or guide here." % ref)
    return out.items

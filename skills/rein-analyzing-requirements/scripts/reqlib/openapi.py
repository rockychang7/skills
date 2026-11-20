"""Reading an API description (OpenAPI 3, also called swagger) for the frontend guide.

The frontend guide never has fields written by hand when the project has an
API description: `contract` stores a copy of it per version, and render takes
each API's method, path, parameters and response fields from it through the
API's `contract` ("POST /activity/signup"). Two stored versions compared
field by field give the change marks and the lines on what breaks old code.

A field is {"name", "type", "required", "desc", "enum", "deprecated",
"nullable", "children"}. Responses wrapped as {code, msg, data} list only the
fields of `data`; the wrapper is a project convention, said once.
"""

from __future__ import annotations

import json
import urllib.request
from typing import Any

from .output import Stop, issue

FETCH_TIMEOUT = 20  # seconds


def load(source: str) -> Any:
    """The parsed description from a file path or an http(s) URL; problems stop the command."""
    try:
        if source.startswith(("http://", "https://")):
            req = urllib.request.Request(source, headers={"Accept": "application/json"})
            with urllib.request.urlopen(req, timeout=FETCH_TIMEOUT) as resp:  # noqa: S310 (the user's own URL)
                raw = resp.read()
        else:
            with open(source, "rb") as f:
                raw = f.read()
    except OSError as e:
        raise Stop(issue("contract.unreadable", "error", "Cannot read %s: %s." % (source, e),
                         hint="For a URL, the service must be running and reachable from here; otherwise ask the "
                         "user to save the description as a file.", where="--openapi"))
    try:
        spec = json.loads(raw.decode("utf-8-sig"))
    except (UnicodeDecodeError, json.JSONDecodeError):
        raise Stop(issue("contract.not-json", "error", "%s is not a JSON API description." % source,
                         hint="Pass the JSON form (Spring Boot with springdoc: /v3/api-docs; FastAPI: /openapi.json). "
                         "YAML is not read.", where="--openapi"))
    if not isinstance(spec, dict) or not isinstance(spec.get("paths"), dict):
        raise Stop(issue("contract.not-openapi", "error", "%s has no `paths`: it is not an OpenAPI description." % source,
                         where="--openapi"))
    return spec


def operations(spec: dict[str, Any]) -> list[str]:
    """Every operation as "METHOD /path"."""
    out = []
    for path, item in (spec.get("paths") or {}).items():
        for method in item or {}:
            if method.lower() in ("get", "post", "put", "patch", "delete", "head", "options"):
                out.append("%s %s" % (method.upper(), path))
    return out


def _resolve(spec: dict[str, Any], node: Any) -> dict[str, Any]:
    seen = 0
    while isinstance(node, dict) and "$ref" in node and seen < 32:
        name = str(node["$ref"]).rsplit("/", 1)[-1]
        target = ((spec.get("components") or {}).get("schemas") or {}).get(name) or {}
        node = dict(target, **{k: v for k, v in node.items() if k != "$ref"})
        seen += 1
    return node if isinstance(node, dict) else {}


def _type(spec: dict[str, Any], node: Any) -> str:
    node = _resolve(spec, node)
    t = node.get("type") or ("object" if node.get("properties") else "")
    if t == "array":
        return "array<%s>" % _type(spec, node.get("items") or {})
    return str(t or "?")


def _fields(spec: dict[str, Any], schema: Any, depth: int = 0) -> list[dict[str, Any]]:
    schema = _resolve(spec, schema)
    required = schema.get("required") or []
    out = []
    for name, prop in (schema.get("properties") or {}).items():
        p = _resolve(spec, prop)
        f: dict[str, Any] = {"name": name, "type": _type(spec, prop), "required": name in required,
                             "desc": p.get("description") or "", "enum": p.get("enum"),
                             "deprecated": bool(p.get("deprecated")), "nullable": bool(p.get("nullable"))}
        inner = _resolve(spec, p.get("items") or {}) if p.get("type") == "array" else p
        if inner.get("properties") and depth < 8:
            f["children"] = _fields(spec, inner, depth + 1)
        out.append(f)
    return out


def _json_schema(container: Any) -> Any:
    return (((container or {}).get("content") or {}).get("application/json") or {}).get("schema") or {}


def operation(spec: dict[str, Any], contract: str) -> dict[str, Any] | None:
    """Method, path, query/body parameters and response fields of one operation; None when it is not there."""
    method, _, path = str(contract).strip().partition(" ")
    op = ((spec.get("paths") or {}).get(path.strip()) or {}).get(method.lower())
    if not isinstance(op, dict):
        return None
    query = []
    for p in op.get("parameters") or []:
        p = _resolve(spec, p)
        if p.get("in") not in ("query", "path"):
            continue
        schema = _resolve(spec, p.get("schema") or {})
        query.append({"name": p.get("name"), "type": _type(spec, schema), "required": bool(p.get("required")),
                      "desc": p.get("description") or "", "enum": schema.get("enum"),
                      "deprecated": bool(p.get("deprecated")), "nullable": False})
    body = _fields(spec, _json_schema(_resolve(spec, op.get("requestBody"))))
    responses = op.get("responses") or {}
    ok = responses.get("200") or responses.get("201") or {}
    resp = _resolve(spec, _json_schema(_resolve(spec, ok)))
    props = resp.get("properties") or {}
    if "code" in props and ("data" in props or "msg" in props):  # the {code, msg, data} wrapper
        data = props.get("data")
        response = _fields(spec, data) if data else []
    else:
        response = _fields(spec, resp)
    return {"method": method.upper(), "path": path.strip(), "summary": op.get("summary") or "",
            "query": query, "body": body, "response": response}


def _flat(fields: Any, prefix: str = "") -> dict[str, dict[str, Any]]:
    out: dict[str, dict[str, Any]] = {}
    for f in fields or []:
        key = prefix + str(f.get("name"))
        out[key] = f
        out.update(_flat(f.get("children"), key + "."))
    return out


def compare(old: dict[str, Any] | None, new: dict[str, Any], t: dict[str, str]) -> dict[str, Any]:
    """Field marks between two versions of one operation, and plain-language lines.

    marks:      {"response:list.status": {"s": "modify", "was": {"enum": [1, 2]}}, …}
    removed:    {"response": [field with "path"], …}: fields no longer there
    breaking:   lines on what old frontend code must change for
    compatible: lines on what it may start using
    `t` holds the line texts (d_removed, d_type, …) in the page language.
    """
    marks: dict[str, dict[str, Any]] = {}
    removed: dict[str, list[dict[str, Any]]] = {}
    breaking: list[str] = []
    compatible: list[str] = []
    if old is None:
        return {"marks": marks, "removed": removed, "breaking": breaking, "compatible": compatible}

    def line(key: str, **values: Any) -> str:
        text = t[key]
        for k, v in values.items():
            text = text.replace("{%s}" % k, str(v))
        return text

    for part in ("query", "body", "response"):
        before_all, now_all = _flat(old.get(part)), _flat(new.get(part))
        for key, f in now_all.items():
            mk = part + ":" + key
            before = before_all.get(key)
            if before is None:
                marks[mk] = {"s": "add"}
                if part == "response":
                    compatible.append(line("d_added_resp", field=key))
                elif f.get("required"):
                    breaking.append(line("d_required", field=key))
                else:
                    compatible.append(line("d_added_req", field=key))
                continue
            was: dict[str, Any] = {}
            if f.get("type") != before.get("type"):
                breaking.append(line("d_type", field=key, old=before.get("type"), new=f.get("type")))
                was["type"] = before.get("type")
            if part != "response" and f.get("required") and not before.get("required"):
                breaking.append(line("d_required", field=key))
                was["required"] = False
            added = [v for v in f.get("enum") or [] if v not in (before.get("enum") or [])]
            if added and before.get("enum"):
                breaking.append(line("d_enum", field=key, vals=" ".join(str(v) for v in added)))
                was["enum"] = before.get("enum")
            if f.get("deprecated") and not before.get("deprecated"):
                breaking.append(line("d_deprecated", field=key) + (t["d_colon"] + f["desc"] if f.get("desc") else ""))
                was["deprecated"] = False
            if was:
                marks[mk] = {"s": "modify", "was": was}
        for key, f in before_all.items():
            if key not in now_all:
                marks[part + ":" + key] = {"s": "remove"}
                removed.setdefault(part, []).append(dict(f, children=None, path=key))
                breaking.append(line("d_removed", field=key))
    return {"marks": marks, "removed": removed, "breaking": breaking, "compatible": compatible}

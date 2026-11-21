"""The backend plan as an XMind mind map (the export xmind command).

The map is for whoever schedules the work: one branch per client with its APIs,
each showing who owns it and how far it is (labels and a progress marker), what
blocks it, what it needs first, and what to do; then tables and data, configs,
risks, and what was dropped.

An .xmind file is a zip: content.json, metadata.json and manifest.json for
XMind 2020 and later; content.xml, meta.xml and META-INF/manifest.xml hold the
same map for XMind 8. No theme is stored, so XMind shows its default one. IDs
and timestamps come from the content, so the same map gives the same file.
"""

from __future__ import annotations

import datetime
import hashlib
import io
import json
import zipfile
from typing import Any
from xml.sax.saxutils import escape, quoteattr

STATUS_MARKER = {"todo": "task-start", "doing": "task-half", "testing": "task-3quar", "done": "task-done"}


def _t(texts: dict[str, str], text_id: str, **values: Any) -> str:
    text = texts[text_id]
    for k, v in values.items():
        text = text.replace("{%s}" % k, str(v))
    return text


def topic(title: str, children: list[dict[str, Any]] | None = None, labels: list[str] | None = None,
          markers: list[str] | None = None, folded: bool = False) -> dict[str, Any]:
    node: dict[str, Any] = {"title": title, "children": [c for c in children or [] if c]}
    if labels:
        node["labels"] = labels
    if markers:
        node["markers"] = markers
    if folded and node["children"]:
        node["folded"] = True
    return node


def build(analysis: dict[str, Any], texts: dict[str, Any], marks: dict[str, str] | None = None) -> dict[str, Any]:
    """The map as nested topics. `marks` ({"api:C1": "add" | "modify"}, from the plan's diff against
    the copy last sent) label what changed since then."""
    p, x = texts["plan"], texts["xmind"]
    marks = marks or {}
    be = analysis.get("backend") or {}
    apis = [a for a in be.get("apis") or [] if isinstance(a, dict)]
    risks = [r for r in be.get("risks") or [] if isinstance(r, dict)]
    open_p0 = [q for q in analysis.get("questions") or []
               if isinstance(q, dict) and q.get("status") == "open" and q.get("priority") == "P0"]
    clients = [c for c in analysis.get("clients") or [] if isinstance(c, dict)]

    def change(key: str) -> list[str]:
        s = marks.get(key)
        return [x["chg_add"]] if s == "add" else [x["chg_modify"]] if s == "modify" else []

    def api_node(a: dict[str, Any]) -> dict[str, Any]:
        kind = p["k_internal"] if a.get("internal") else p["k_modify"] if a.get("kind") == "modify" else p["k_new"]
        title = _t(x, "api", id=a.get("id", ""), name=a.get("name", ""), kind=kind)
        status = a.get("status") or "todo"
        labels = [a.get("owner") or p["owner_none"], p.get("st_" + status, status)] + change("api:%s" % a.get("id"))
        kids = []
        for q in open_p0:
            if a.get("id") in (q.get("affects") or []):
                kids.append(topic(_t(x, "hold", q=q.get("id", ""), title=q.get("title", "")), markers=["flag-red"]))
        if a.get("depends"):
            kids.append(topic(_t(x, "depends", ids=p["sep_ids"].join(a["depends"]))))
        if a.get("where"):
            kids.append(topic((p["f_when"] if a.get("internal") else p["f_where"]) + x["colon"] + a["where"]))
        if a.get("kind") == "modify":
            if a.get("path"):
                kids.append(topic(p["f_path"] + x["colon"] + a["path"]))
            if a.get("now"):
                kids.append(topic(p["f_now"] + x["colon"] + a["now"]))
        does = (p["f_becomes"] if a.get("kind") == "modify" else x["does"]) + a.get("does", "")
        kids.append(topic(does, [topic(line) for line in a.get("todo") or []]))
        watch = [topic(line) for line in a.get("online") or []]
        watch += [topic(p["f_risk"] + x["colon"] + r.get("text", "")) for r in risks if a.get("id") in (r.get("apis") or [])]
        if watch:
            kids.append(topic(p["f_online"], watch))
        # Folded: the map opens on the APIs with owner and status; details are a click away.
        return topic(title, kids, labels, [STATUS_MARKER.get(status, "task-start")], folded=True)

    branches = []
    live = [a for a in apis if not a.get("removed")]
    names = {c.get("id"): c.get("name") for c in clients}
    sides = [c.get("id") for c in clients] + sorted({a.get("side") for a in live if a.get("side") not in names} - {None})
    for side in sides:
        mine = [a for a in live if a.get("side") == side]
        if mine:
            branches.append(topic(names.get(side) or x["no_client"], [api_node(a) for a in mine]))
    homeless = [a for a in live if not a.get("side")]
    if homeless:
        branches.append(topic(x["no_client"], [api_node(a) for a in homeless]))

    data_kids = []
    for t in be.get("tables") or []:
        if not t.get("removed"):
            key = "table_new" if t.get("kind") == "new" else "table_alter"
            data_kids.append(topic(_t(x, key, name=t.get("name", "")) + x["colon"] + t.get("does", ""),
                                   labels=change("table:%s" % t.get("name"))))
    for d in be.get("data") or []:
        data_kids.append(topic(_t(x, "data", table=d.get("table", "")) + x["colon"] + d.get("does", "")))
    if data_kids:
        branches.append(topic(x["tables_h"], data_kids))

    configs = [c for c in be.get("configs") or [] if not c.get("removed")]
    if configs:
        branches.append(topic(x["configs_h"], [
            topic(_t(x, "config_new" if c.get("kind") == "new" else "config_modify", key=c.get("key", "")) + x["colon"] +
                  c.get("does", ""), [topic("%s%s%s" % (env, x["colon"], v)) for env, v in (c.get("values") or {}).items()],
                  labels=change("config:%s" % c.get("key")))
            for c in configs]))

    loose = [r for r in risks if not any(a.get("id") in (r.get("apis") or []) for a in live)]
    if loose:
        branches.append(topic(p["nav_risks"], [topic(r.get("text", "")) for r in loose]))

    gone = [a for a in apis if a.get("removed")]
    if gone:
        branches.append(topic(x["gone_h"], [topic(_t(x, "gone", id=a.get("id", ""), name=a.get("name", ""),
                                                    why=a.get("removed", ""))) for a in gone]))

    title = (analysis.get("meta") or {}).get("title", "")
    return topic(_t(x, "root", title=title), branches)


def outline(node: dict[str, Any], depth: int = 0) -> str:
    """The map as indented text, for reading it without XMind."""
    extra = ""
    if node.get("labels"):
        extra += "  [" + " · ".join(node["labels"]) + "]"
    if node.get("markers"):
        extra += "  <" + ", ".join(node["markers"]) + ">"
    lines = ["%s%s%s" % ("    " * depth + ("- " if depth else ""), node["title"], extra)]
    for child in node.get("children") or []:
        lines.append(outline(child, depth + 1))
    return "\n".join(lines)


ROOT_STRUCTURE = "org.xmind.ui.logic.right"


def _ids(node: dict[str, Any], parent: str = "", index: int = 0) -> None:
    """Give every topic an ID derived from its place and title, so the same map gives the same file."""
    node["id"] = hashlib.sha1(("%s/%d/%s" % (parent, index, node["title"])).encode("utf-8")).hexdigest()[:26]
    for i, child in enumerate(node.get("children") or []):
        _ids(child, node["id"], i)


def _json_topic(node: dict[str, Any], root: bool = False) -> dict[str, Any]:
    out: dict[str, Any] = {"id": node["id"], "class": "topic", "title": node["title"]}
    if root:
        out["structureClass"] = ROOT_STRUCTURE
    if node.get("labels"):
        out["labels"] = node["labels"]
    if node.get("markers"):
        out["markers"] = [{"markerId": m} for m in node["markers"]]
    if node.get("folded"):
        out["branch"] = "folded"
    if node.get("children"):
        out["children"] = {"attached": [_json_topic(c) for c in node["children"]]}
    return out


def _xml_topic(node: dict[str, Any], root: bool = False) -> str:
    attrs = ' id=%s' % quoteattr(node["id"])
    if root:
        attrs += ' structure-class="%s"' % ROOT_STRUCTURE
    if node.get("folded"):
        attrs += ' branch="folded"'
    parts = ["<title>%s</title>" % escape(node["title"])]
    if node.get("markers"):
        parts.append("<marker-refs>%s</marker-refs>" % "".join('<marker-ref marker-id=%s/>' % quoteattr(m)
                                                               for m in node["markers"]))
    if node.get("labels"):
        parts.append("<labels>%s</labels>" % "".join("<label>%s</label>" % escape(l) for l in node["labels"]))
    if node.get("children"):
        parts.append('<children><topics type="attached">%s</topics></children>'
                     % "".join(_xml_topic(c) for c in node["children"]))
    return "<topic%s>%s</topic>" % (attrs, "".join(parts))


XML_HEAD = '<?xml version="1.0" encoding="UTF-8" standalone="no"?>'


def pack(root: dict[str, Any], sheet_title: str, at: str, creator: str, version: str) -> bytes:
    """The .xmind file for a map. `at` (ISO time of the version) dates the zip entries."""
    _ids(root)
    sheet_id = hashlib.sha1(("sheet/" + root["id"]).encode("utf-8")).hexdigest()[:26]
    content = [{"id": sheet_id, "class": "sheet", "title": sheet_title, "rootTopic": _json_topic(root, root=True)}]
    legacy = (XML_HEAD + '<xmap-content xmlns="urn:xmind:xmap:xmlns:content:2.0" xmlns:fo="http://www.w3.org/1999/XSL/Format" '
              'xmlns:svg="http://www.w3.org/2000/svg" xmlns:xhtml="http://www.w3.org/1999/xhtml" '
              'xmlns:xlink="http://www.w3.org/1999/xlink" version="2.0"><sheet id=%s>%s<title>%s</title></sheet></xmap-content>'
              % (quoteattr(sheet_id), _xml_topic(root, root=True), escape(sheet_title)))
    files = [
        ("content.json", json.dumps(content, ensure_ascii=False)),
        ("metadata.json", json.dumps({"dataStructureVersion": "2", "creator": {"name": creator, "version": version},
                                      "layoutEngineVersion": "3"})),
        ("manifest.json", json.dumps({"file-entries": {"content.json": {}, "metadata.json": {}}})),
        ("content.xml", legacy),
        ("meta.xml", XML_HEAD + '<meta xmlns="urn:xmind:xmap:xmlns:meta:2.0" version="2.0"/>'),
        ("META-INF/manifest.xml", XML_HEAD + '<manifest xmlns="urn:xmind:xmap:xmlns:manifest:1.0">'
         '<file-entry full-path="content.xml" media-type="text/xml"/><file-entry full-path="META-INF/" media-type=""/>'
         '<file-entry full-path="meta.xml" media-type="text/xml"/></manifest>'),
    ]
    when = datetime.datetime.fromisoformat(at).timetuple()[:6]
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
        for name, text in files:
            info = zipfile.ZipInfo(name, date_time=when)
            info.compress_type = zipfile.ZIP_DEFLATED
            z.writestr(info, text.encode("utf-8"))
    return buf.getvalue()

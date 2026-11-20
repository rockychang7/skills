"""Turning an analysis into the pages people read. Only the brief so far.

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
from .doc import section_texts
from .files import write_text
from .output import issue

ASSETS = Path(__file__).resolve().parents[2] / "assets"
PAGES = ("brief", "plan", "sql", "release", "frontend")
READY = ("brief",)  # pages this version can generate
SECTION_REF = re.compile(r"§\s*(\d+(?:\.\d+)*)")


def load_texts(lang: str) -> dict[str, Any]:
    return json.loads((ASSETS / "i18n" / ("%s.json" % lang)).read_text(encoding="utf-8"))


def fingerprint(data: Any) -> str:
    """Same content, same fingerprint, whatever the formatting."""
    text = json.dumps(data, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def file_hash(raw: bytes) -> str:
    return hashlib.sha256(raw).hexdigest()


def pages_needed(analysis: dict[str, Any], frontend: bool) -> list[str]:
    backend = analysis.get("backend") or {}
    needed = ["brief"]
    if backend.get("apis"):
        needed.append("plan")
    if backend.get("tables") or backend.get("data"):
        needed.append("sql")
    if backend.get("tables") or backend.get("data") or backend.get("configs") or analysis.get("release"):
        needed.append("release")
    if frontend:
        needed.append("frontend")
    return needed


def brief_html(
    analysis: dict[str, Any],
    state: dict[str, Any],
    version: int,
    generated: str,
    doc_text: str,
    texts: dict[str, Any],
    base: dict[str, Any] | None = None,
    base_analysis: dict[str, Any] | None = None,
) -> str:
    shown = {k: v for k, v in analysis.items() if k != "skipped_sections"}  # skipped sections are never shown
    cited = set(SECTION_REF.findall(json.dumps(shown, ensure_ascii=False)))
    data = {
        "lang": state["lang"],
        "t": texts["brief"],
        "meta": {
            "id": state["id"],
            "analysis_v": version,
            "doc_v": len(state["docs"]),
            "generated": generated,
            "send": None,
        },
        "analysis": analysis,
        "sections": section_texts(doc_text, cited),
        "diff": dict(diffs.compare(base_analysis, analysis), base=base) if base and base_analysis is not None else None,
    }
    title = texts["brief"]["page_title"].replace("{title}", str(analysis.get("meta", {}).get("title", "")))
    payload = json.dumps(data, ensure_ascii=False).replace("</", "<\\/")
    template = (ASSETS / "templates" / "brief.html").read_text(encoding="utf-8")
    return (template.replace("__LANG__", state["lang"])
            .replace("__TITLE__", html.escape(title))
            .replace("__NOSCRIPT__", html.escape(texts["brief"]["noscript"]))
            .replace("__REQ_DATA__", payload))


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

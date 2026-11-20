"""Reading a requirement document and finding its sections.

Section IDs (the `§3.4` in `src`) come from the headings:
- If any heading starts with a number ("3.4 取消报名"), only numbered headings
  are sections and they keep their own numbers.
- Otherwise headings are numbered in order (1, 1.1, 1.2, 2, ...). A single
  top heading that opens the document is its title, not a section.
- A document without headings is split into paragraphs: 1, 2, 3, ...
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

from .output import Stop, issue

BINARY_SUFFIXES = {".doc", ".docx", ".pdf", ".xls", ".xlsx", ".ppt", ".pptx", ".png", ".jpg", ".jpeg", ".gif", ".zip"}
HEADING = re.compile(r"^(#{1,6})\s+(.*?)\s*#*\s*$")
FENCE = re.compile(r"^\s*(```|~~~)")
NUMBERED = re.compile(r"^(\d+(?:\.\d+)*)(?:[.．、]\s*|\s+|$)(.*)$")
TITLE_LIMIT = 40


@dataclass
class Section:
    id: str  # "3.4" (shown as "§3.4")
    title: str
    line: int  # 1-based line where it starts


def read_doc(path: Path) -> tuple[str, list[dict[str, str]]]:
    """Return the document text (LF line endings) and any warnings."""
    if not path.is_file():
        raise Stop(issue("doc.not-found", "error", "Document %s does not exist." % path, where=str(path)))
    if path.suffix.lower() in BINARY_SUFFIXES:
        raise Stop(
            issue(
                "doc.not-text",
                "error",
                "%s is not a text document." % path.name,
                hint="Convert it to Markdown (or paste its text into a .md file) and pass that file.",
                where=str(path),
            )
        )
    raw = path.read_bytes()
    if b"\x00" in raw:
        raise Stop(issue("doc.not-text", "error", "%s looks like a binary file." % path.name,
                         hint="Convert it to Markdown and pass that file.", where=str(path)))
    warnings: list[dict[str, str]] = []
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("gb18030", errors="replace")
        warnings.append(
            issue(
                "doc.encoding",
                "warn",
                "%s is not UTF-8; it was read as GB18030 and stored as UTF-8." % path.name,
                hint="Open the stored copy and make sure the Chinese text reads correctly.",
                where=str(path),
            )
        )
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    if not text.strip():
        raise Stop(issue("doc.empty", "error", "%s is empty." % path.name, where=str(path)))
    return text, warnings


def _headings(lines: list[str]) -> list[tuple[int, int, str]]:
    """(line number, level, text) for every Markdown heading outside code fences."""
    found, fenced = [], False
    for n, line in enumerate(lines, 1):
        if FENCE.match(line):
            fenced = not fenced
            continue
        if fenced:
            continue
        m = HEADING.match(line)
        if m and m.group(2):
            found.append((n, len(m.group(1)), m.group(2)))
    return found


def _short(text: str) -> str:
    text = " ".join(text.split())
    return text if len(text) <= TITLE_LIMIT else text[: TITLE_LIMIT - 1] + "…"


def parse_sections(text: str) -> list[Section]:
    lines = text.split("\n")
    heads = _headings(lines)

    if not heads:
        sections, start, para = [], 0, []
        for n, line in enumerate(lines + [""], 1):
            if line.strip():
                if not para:
                    start = n
                para.append(line.strip())
            elif para:
                sections.append(Section(str(len(sections) + 1), _short(" ".join(para)), start))
                para = []
        return sections

    numbered = [(n, NUMBERED.match(t)) for n, _, t in heads]
    if any(m for _, m in numbered):
        return [Section(m.group(1), _short(m.group(2)) or m.group(1), n) for n, m in numbered if m]

    top = min(level for _, level, _ in heads)
    if heads[0][1] == top and sum(1 for _, level, _ in heads if level == top) == 1 and len(heads) > 1:
        heads = heads[1:]  # the document title

    sections, stack, counters = [], [], []
    for n, level, title in heads:
        while stack and stack[-1] >= level:
            stack.pop()
        depth = len(stack)
        stack.append(level)
        counters = counters[: depth + 1]
        while len(counters) <= depth:
            counters.append(0)
        counters[depth] += 1
        sections.append(Section(".".join(str(c) for c in counters), _short(title), n))
    return sections


def section_texts(text: str, ids: set[str]) -> dict[str, dict[str, str]]:
    """Title and body of the sections in `ids`, for showing cited text on pages."""
    lines = text.split("\n")
    sections = parse_sections(text)
    found: dict[str, dict[str, str]] = {}
    headed = bool(_headings(lines))
    for k, s in enumerate(sections):
        if s.id not in ids or s.id in found:
            continue
        if headed:
            end = sections[k + 1].line - 1 if k + 1 < len(sections) else len(lines)
            body = [ln.strip() for ln in lines[s.line:end] if ln.strip()]
        else:  # paragraphs: the section is the paragraph itself
            body = []
            for ln in lines[s.line - 1:]:
                if not ln.strip():
                    break
                body.append(ln.strip())
        found[s.id] = {"title": s.title, "text": "\n".join(body)}
    return found


def duplicate_ids(sections: list[Section]) -> list[str]:
    seen, dupes = set(), []
    for s in sections:
        if s.id in seen and s.id not in dupes:
            dupes.append(s.id)
        seen.add(s.id)
    return dupes

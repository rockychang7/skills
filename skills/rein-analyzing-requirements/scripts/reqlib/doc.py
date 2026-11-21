"""Reading a requirement document and finding its sections.

Section IDs (the `§3.4` in `src`) come from the headings:
- If any heading starts with a number ("3.4 取消报名"), only numbered headings
  are sections and they keep their own numbers. A heading where a sentence
  runs into the number ("……即可删除。4.1 点位") counts as numbered too.
- Several documents put together (PC, APP, C), each numbering from 1: when
  numbers repeat, every top-level heading that has no number starts a part,
  and the sections in it take the part's name in front: "§APP-2.1". The name
  is the English word the heading starts with ("APP 端" -> APP), else P and
  the part's place ("11月14日（初版）" as the seventh top heading -> P7). The
  part heading is itself a section ("§APP").
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
# A sentence that runs into a dotted number: "……即可删除。4.1 点位".
GLUED = re.compile(r"^.*?[。；;：:]\s*(\d+(?:\.\d+)+)\s+(\S.*)$")
PART_KEY = re.compile(r"^\s*([A-Za-z][A-Za-z0-9]*)")
# A section reference in src: "§3.4", "§APP-2.1", or a whole part "§APP".
SECTION_REF = re.compile(r"§\s*([A-Za-z][A-Za-z0-9]*(?:-\d+(?:\.\d+)*)?|\d+(?:\.\d+)*)")
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


def section_refs(src: str) -> list[str]:
    """The section IDs a src names: "§3.4, §APP-2.1" -> ["3.4", "APP-2.1"]."""
    return SECTION_REF.findall(src)


def under(ref: str, section_id: str) -> bool:
    """Whether a section is `ref` itself or inside it (a subsection, or a section of the part `ref`)."""
    return section_id == ref or section_id.startswith(ref + ".") or section_id.startswith(ref + "-")


def number_of(heading: str) -> tuple[str, str] | None:
    """(number, title) of a numbered heading, None when it has no number."""
    m = NUMBERED.match(heading)
    if m:
        return m.group(1), m.group(2)
    g = GLUED.match(heading)
    return (g.group(1), g.group(2)) if g else None


def _in_parts(heads: list[tuple[int, int, str]]) -> list[Section] | None:
    """Numbered sections prefixed by their part; None when the top level has no unnumbered headings."""
    top = min(level for _, level, _ in heads)
    if not any(level == top and number_of(title) is None for _, level, title in heads):
        return None
    sections: list[Section] = []
    used: set[str] = set()
    key, place = "", 0
    for n, level, title in heads:
        num = number_of(title)
        if level == top and num is None:
            place += 1
            m = PART_KEY.match(title)
            key = m.group(1) if m and m.group(1) not in used and not re.fullmatch(r"P\d+", m.group(1)) else "P%d" % place
            used.add(key)
            sections.append(Section(key, _short(title), n))
        elif num:
            sections.append(Section("%s-%s" % (key, num[0]) if key else num[0], _short(num[1]) or num[0], n))
    return sections


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

    numbered = [(n, number_of(t)) for n, _, t in heads]
    if any(num for _, num in numbered):
        plain = [Section(num[0], _short(num[1]) or num[0], n) for n, num in numbered if num]
        if not duplicate_ids(plain):
            return plain
        return _in_parts(heads) or plain

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


@dataclass
class Part:
    """One section with its own text: the lines up to the next section, blank lines dropped."""

    section: Section
    heading: str  # the full heading text ("3.4 取消报名"); "" for a paragraph
    body: list[str]


def split_sections(text: str) -> tuple[list[str], list[Part]]:
    """(lines before the first section, every section with its own text), for comparing versions."""
    lines = text.split("\n")
    sections = parse_sections(text)
    headed = bool(_headings(lines))
    parts: list[Part] = []
    for k, s in enumerate(sections):
        if headed:
            end = sections[k + 1].line - 1 if k + 1 < len(sections) else len(lines)
            m = HEADING.match(lines[s.line - 1])
            heading = " ".join(m.group(2).split()) if m else s.title
            body = [ln.strip() for ln in lines[s.line:end] if ln.strip()]
        else:  # paragraphs: the section is the paragraph itself
            heading, body = "", []
            for ln in lines[s.line - 1:]:
                if not ln.strip():
                    break
                body.append(ln.strip())
        parts.append(Part(s, heading, body))
    first = sections[0].line - 1 if sections else len(lines)
    return [ln.strip() for ln in lines[:first] if ln.strip()], parts


def section_texts(text: str, ids: set[str]) -> dict[str, dict[str, str]]:
    """Title and body of the sections in `ids`, for showing cited text on pages."""
    found: dict[str, dict[str, str]] = {}
    for p in split_sections(text)[1]:
        if p.section.id in ids and p.section.id not in found:
            found[p.section.id] = {"title": p.section.title, "text": "\n".join(p.body)}
    return found


def duplicate_ids(sections: list[Section]) -> list[str]:
    seen, dupes = set(), []
    for s in sections:
        if s.id in seen and s.id not in dupes:
            dupes.append(s.id)
        seen.add(s.id)
    return dupes

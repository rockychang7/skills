"""Requirement folders inside the requirements folder (the workspace).

    <workspace>/REQ-20261118-activity-signup/
      state.json         language, document versions (more as commands grow)
      source/doc-v1.md   each version of the document, as read
      analysis.json      written by the agent
      frontend.json      written by the agent
"""

from __future__ import annotations

import re
from pathlib import Path
from typing import Any

from .files import JsonProblem, read_json, write_json
from .output import Stop, issue

STATE_FILE = "state.json"
NAME = re.compile(r"^[a-z0-9]+(?:-[a-z0-9]+)*$")
NAME_LIMIT = 40
REQ_DIR = re.compile(r"^REQ-(\d{8})-([a-z0-9]+(?:-[a-z0-9]+)*)$")


def check_name(name: str) -> None:
    if not NAME.match(name) or len(name) > NAME_LIMIT:
        raise Stop(
            issue(
                "new.bad-name",
                "error",
                "Short name %r is not allowed." % name,
                hint="Use lowercase letters, digits and single hyphens, at most %d characters, "
                "e.g. activity-signup." % NAME_LIMIT,
                where="--name",
            )
        )


def requirements(workspace: Path) -> list[Path]:
    if not workspace.is_dir():
        return []
    return sorted(p for p in workspace.iterdir() if p.is_dir() and REQ_DIR.match(p.name) and (p / STATE_FILE).is_file())


def by_name(workspace: Path, name: str) -> list[Path]:
    return [p for p in requirements(workspace) if REQ_DIR.match(p.name).group(2) == name]


def find(workspace: Path | None, req: str) -> Path:
    """Resolve --req: a requirement folder path, a folder name, or a short name."""
    as_path = Path(req).expanduser()
    if (as_path / STATE_FILE).is_file():
        return as_path.resolve()
    if workspace is None:
        raise Stop(
            issue(
                "workspace.not-set",
                "error",
                "No requirements folder is set, so %r cannot be found." % req,
                hint="Pass --dir <folder>, or the requirement folder's path as --req.",
                where="--req",
            )
        )
    if REQ_DIR.match(req):
        found = [workspace / req] if (workspace / req / STATE_FILE).is_file() else []
    else:
        found = by_name(workspace, req)
    if len(found) == 1:
        return found[0]
    names = [p.name for p in requirements(workspace)]
    if not found:
        raise Stop(
            issue(
                "req.not-found",
                "error",
                "No requirement %r in %s." % (req, workspace),
                hint=("Existing: %s." % ", ".join(names[-10:])) if names else "Create one with new.",
                where="--req",
            )
        )
    raise Stop(
        issue(
            "req.ambiguous",
            "error",
            "Several requirements are called %r." % req,
            hint="Pass the full folder name: %s." % ", ".join(p.name for p in found),
            where="--req",
        )
    )


def load_state(folder: Path) -> dict[str, Any]:
    try:
        state = read_json(folder / STATE_FILE, "state")
    except JsonProblem as e:
        raise Stop(e.issue)
    if not isinstance(state, dict) or not isinstance(state.get("docs"), list) or not state["docs"]:
        raise Stop(issue("state.invalid", "error", "%s is damaged." % (folder / STATE_FILE),
                         hint="It is written by req.py; restore it from version control if possible."))
    return state


def save_state(folder: Path, state: dict[str, Any]) -> None:
    write_json(folder / STATE_FILE, state)


def latest_doc(folder: Path, state: dict[str, Any]) -> Path:
    return folder / state["docs"][-1]["file"]

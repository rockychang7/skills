"""Small file helpers: JSON in and out, written atomically as UTF-8."""

from __future__ import annotations

import json
import os
import tempfile
from pathlib import Path
from typing import Any

from .output import issue


class JsonProblem(Exception):
    """A JSON file is missing or cannot be parsed; carries a ready-made issue."""

    def __init__(self, found: dict[str, str]):
        super().__init__(found["msg"])
        self.issue = found


def read_json(path: Path, code_prefix: str = "json") -> Any:
    if not path.is_file():
        raise JsonProblem(issue(code_prefix + ".missing", "error", "%s does not exist." % path, where=str(path)))
    try:
        return json.loads(path.read_text(encoding="utf-8-sig"))
    except UnicodeDecodeError:
        raise JsonProblem(issue(code_prefix + ".encoding", "error", "%s is not UTF-8 text." % path, where=str(path)))
    except json.JSONDecodeError as e:
        raise JsonProblem(
            issue(
                code_prefix + ".invalid",
                "error",
                "%s is not valid JSON: %s." % (path.name, e.msg),
                hint="Fix the JSON at line %d, column %d. Comments are not allowed." % (e.lineno, e.colno),
                where="%s:%d:%d" % (path.name, e.lineno, e.colno),
            )
        )


def write_bytes(path: Path, data: bytes) -> None:
    """Write bytes, replacing the file in one step."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "wb") as f:
            f.write(data)
        os.replace(tmp, str(path))
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def write_text(path: Path, text: str) -> None:
    """Write UTF-8 text with LF line endings, replacing the file in one step."""
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, tmp = tempfile.mkstemp(dir=str(path.parent), prefix=".tmp-", suffix=path.suffix)
    try:
        with os.fdopen(fd, "w", encoding="utf-8", newline="\n") as f:
            f.write(text)
        os.replace(tmp, str(path))
    except BaseException:
        if os.path.exists(tmp):
            os.remove(tmp)
        raise


def write_json(path: Path, data: Any) -> None:
    write_text(path, json.dumps(data, ensure_ascii=False, indent=2) + "\n")

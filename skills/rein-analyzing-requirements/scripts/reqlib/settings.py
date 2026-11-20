"""Where settings come from: command line, project, user, defaults.

Project settings: `.req-profile.json` in the project root. The project root is
the nearest folder (from the current directory up) that has that file, else the
nearest one with `.git`, else the current directory.

User settings: `<config home>/rein-analyzing-requirements/config.json`, where
config home is $XDG_CONFIG_HOME or ~/.config. Only `workspace` and `lang`.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from . import SKILL_NAME
from .files import JsonProblem, read_json, write_json
from .output import Stop, issue

PROFILE_NAME = ".req-profile.json"
LANGS = ("zh-CN", "en")
DEFAULT_LANG = "zh-CN"
DEFAULT_ENVS = ["dev", "test", "prod"]
SKILL_DIR = Path(__file__).resolve().parents[2]


def user_config_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or str(Path.home() / ".config")
    return Path(base) / SKILL_NAME / "config.json"


def find_project_root(start: Path) -> Path:
    for folder in [start, *start.parents]:
        if (folder / PROFILE_NAME).is_file():
            return folder
    for folder in [start, *start.parents]:
        if (folder / ".git").exists():
            return folder
    return start


def guard_not_in_skill_folder(cwd: Path) -> None:
    if cwd == SKILL_DIR or SKILL_DIR in cwd.parents:
        raise Stop(
            issue(
                "cwd.skill-folder",
                "error",
                "req.py was run from inside the skill folder, so it cannot tell which project this is.",
                hint="Run it from the project directory and call the script by its full path.",
            )
        )


def _load(path: Path, what: str) -> dict[str, Any]:
    if not path.is_file():
        return {}
    try:
        data = read_json(path, "settings")
    except JsonProblem as e:
        e.issue["msg"] = "%s settings file %s" % (what, e.issue["msg"])
        raise Stop(e.issue)
    if not isinstance(data, dict):
        raise Stop(issue("settings.invalid", "error", "%s must hold a JSON object." % path, where=str(path)))
    return data


class Settings:
    """Settings for one run, read once from the current directory."""

    def __init__(self, cwd: Path):
        self.cwd = cwd
        self.root = find_project_root(cwd)
        self.profile_path = self.root / PROFILE_NAME
        self.user_path = user_config_path()
        self.profile = _load(self.profile_path, "Project")
        self.user = _load(self.user_path, "User")

    def workspace(self, override: str | None) -> tuple[Path | None, str]:
        """Return (requirements folder, which setting chose it)."""
        if override:
            return (self.cwd / Path(override).expanduser()).resolve(), "--dir"
        if self.profile.get("workspace"):
            return (self.root / Path(str(self.profile["workspace"])).expanduser()).resolve(), "project"
        if self.user.get("workspace"):
            return Path(str(self.user["workspace"])).expanduser().resolve(), "user"
        return None, ""

    def lang(self, override: str | None) -> tuple[str, str]:
        for value, source in ((override, "--lang"), (self.profile.get("lang"), "project"), (self.user.get("lang"), "user")):
            if value:
                if value not in LANGS:
                    raise Stop(
                        issue(
                            "settings.bad-lang",
                            "error",
                            "Language %r from the %s settings is not supported." % (value, source),
                            hint="Use one of: %s." % ", ".join(LANGS),
                        )
                    )
                return value, source
        return DEFAULT_LANG, "default"

    def envs(self) -> list[str]:
        envs = self.profile.get("envs")
        if isinstance(envs, list) and envs and all(isinstance(e, str) and e for e in envs):
            return envs
        return list(DEFAULT_ENVS)

    def resolve(self, value: str) -> Path:
        return (self.cwd / Path(value).expanduser()).resolve()

    def inside_project(self, path: Path) -> bool:
        return path == self.root or self.root in path.parents

    def set_value(self, key: str, value: str, scope: str) -> tuple[Path, str]:
        """Store one setting; return (file written, value as stored).

        A workspace in the project settings is stored relative to the project
        root, so it works on every machine and after the project moves.
        """
        if scope == "project":
            path, data = self.profile_path, dict(self.profile)
        else:
            path, data = self.user_path, dict(self.user)
        stored = value
        if key == "workspace":
            full = self.resolve(value)
            stored = (full.relative_to(self.root).as_posix() or ".") if scope == "project" else str(full)
        data[key] = stored
        write_json(path, data)
        return path, stored


def workspace_suggestions(settings: Settings) -> list[dict[str, str]]:
    return [
        {
            "scope": "project",
            "path": "docs/requirements",
            "full_path": str(settings.root / "docs" / "requirements"),
            "why": "inside the project, next to the code; can be committed with it",
        },
        {
            "scope": "user",
            "path": str(Path.home() / "Documents" / "requirements"),
            "why": "outside the repository; never committed; shared by all projects",
        },
        {
            "scope": "decided by the path",
            "path": "(a folder the user names)",
            "why": "inside the project: saved for this project; outside: saved for all projects",
        },
    ]

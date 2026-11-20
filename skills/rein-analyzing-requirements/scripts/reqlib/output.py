"""How every command reports back: one JSON object on stdout, notes on stderr.

Result shape (every command):

    {
      "ok": true,                # false while any issue is "error" or "confirm"
      "command": "check",
      ...command-specific fields...,
      "issues": [
        {"code": "rule.prd-no-src", "level": "error", "where": "features[C02].rules[3]",
         "msg": "what is wrong", "hint": "how to fix it"}
      ]
    }

Issue levels:
    error    must be fixed before going on
    confirm  stop and ask the user; record the answer, then run again
    warn     worth a look, does not block

Issue text (msg / hint) is for the agent, so it is always English and is
recognised by its stable `code`, not by wording.
"""

from __future__ import annotations

import json
import sys
from typing import Any

EXIT_OK = 0  # finished; no error or confirm issues
EXIT_ISSUES = 1  # finished, but there are error or confirm issues
EXIT_USAGE = 2  # bad arguments, missing files, or an unusable environment

LEVELS = ("error", "confirm", "warn")  # also the order issues are listed in
BLOCKING = ("error", "confirm")


class Stop(Exception):
    """Abort the current command with one issue (usage-type problems)."""

    def __init__(self, issue: dict[str, str], exit_code: int = EXIT_USAGE, **fields: Any):
        super().__init__(issue["msg"])
        self.issue = issue
        self.exit_code = exit_code
        self.fields = fields


def use_utf8_streams() -> None:
    """Force UTF-8 on stdout/stderr.

    On Windows a piped stdout defaults to the ANSI code page (for example GBK),
    which garbles Chinese text for any reader expecting UTF-8.
    """
    for stream in (sys.stdout, sys.stderr):
        try:
            stream.reconfigure(encoding="utf-8")
        except (AttributeError, ValueError):
            pass


def issue(code: str, level: str, msg: str, hint: str = "", where: str = "") -> dict[str, str]:
    if level not in LEVELS:
        raise ValueError("unknown issue level: %s" % level)
    return {"code": code, "level": level, "where": where, "msg": msg, "hint": hint}


def summarize(issues: list[dict[str, str]]) -> dict[str, int]:
    return {level: sum(1 for i in issues if i["level"] == level) for level in LEVELS}


def finish(
    command: str,
    issues: list[dict[str, str]] | None = None,
    *,
    exit_code: int | None = None,
    limit: int | None = None,
    **fields: Any,
) -> int:
    """Print the result JSON and return the exit code.

    `limit` caps how many issues are printed (most severe first); the result
    then carries `total` and `shown` so the reader knows more exist.
    """
    issues = sorted(issues or [], key=lambda i: LEVELS.index(i["level"]))
    blocking = any(i["level"] in BLOCKING for i in issues)
    result: dict[str, Any] = {"ok": not blocking and exit_code in (None, EXIT_OK), "command": command}
    result.update(fields)
    if limit is not None and len(issues) > limit:
        result["total"] = len(issues)
        result["shown"] = limit
        note("%d issues found; showing the first %d. Add --all to see every one." % (len(issues), limit))
        issues = issues[:limit]
    result["issues"] = issues
    json.dump(result, sys.stdout, ensure_ascii=False, indent=2)
    sys.stdout.write("\n")
    if exit_code is not None:
        return exit_code
    return EXIT_ISSUES if blocking else EXIT_OK


def note(msg: str) -> None:
    """Progress or reminder text; goes to stderr so stdout stays pure JSON."""
    print(msg, file=sys.stderr)

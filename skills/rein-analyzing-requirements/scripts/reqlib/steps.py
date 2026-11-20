"""What one environment needs for a requirement, as data (the steps command).

The skill says what must be true in an environment and how to check it; how
to get there belongs to whatever tool the session has (a skill that submits
SQL, changes configs or deploys) or to a person. These steps are what that
tool works from. They come from the last rendered version, the same one the
release checklist and the SQL file show, in the same order:

    before    table and data changes, config values, then the analysis' own items
    deploy    the analysis' items
    after     the analysis' items (what to watch)
    rollback  the analysis' items (fastest first), configs back, table changes undone
"""

from __future__ import annotations

from pathlib import Path
from typing import Any, Callable

from . import render, sql


def for_env(
    analysis: dict[str, Any],
    state: dict[str, Any],
    env: str,
    version: int,
    load_version: Callable[[int], dict[str, Any]],
    texts: dict[str, Any],
    out: Path,
) -> dict[str, Any]:
    files = sql.file_names(analysis, texts["files"]["sql"])
    rows = sql.release_rows(analysis, state, [env], version, load_version, texts, files)[env]
    configs = [c for c in (analysis.get("backend") or {}).get("configs") or [] if not c.get("removed")]
    items = [x for x in analysis.get("release") or [] if not x.get("removed")]
    steps: list[dict[str, Any]] = []

    for r in rows:
        st: dict[str, Any] = {"stage": "before", "kind": "sql", "id": "sql:" + r["db"], "db": r["db"] or None,
                              "file": str(out / r["file"]), "state": r["mode"],
                              "needed": r["mode"] in ("fresh", "catch")}
        if st["needed"]:
            st.update(statements=r["text"], count=r["n"], checks=r["checks"],
                      record={"command": "applied", "env": env, "v": version})
        if "from" in r:
            st["from"] = r["from"]
        steps.append(st)
    for c in configs:
        st = {"stage": "before", "kind": "config", "id": "cfg:" + str(c.get("key")), "key": c.get("key"),
              "value": (c.get("values") or {}).get(env), "change": c.get("kind"), "does": c.get("does")}
        if c.get("kind") == "modify":
            st["old"] = c.get("old")
        steps.append(st)
    for stage in ("before", "deploy", "after", "rollback"):
        for x in items:
            if x.get("stage") == stage:
                steps.append({"stage": stage, "kind": x.get("type") or "other", "id": x.get("id"), "text": x.get("text"),
                              "detail": x.get("detail"), "verify": x.get("verify")})
    for c in configs:
        if c.get("kind") == "modify" and c.get("old") is not None:
            steps.append({"stage": "rollback", "kind": "config", "id": "cfgback:" + str(c.get("key")),
                          "key": c.get("key"), "value": c.get("old")})
    for r in rows:
        steps.append({"stage": "rollback", "kind": "sql", "id": "sqlback:" + r["db"], "db": r["db"] or None,
                      "file": str(out / r["file"]), "statements": r["rollback"]})

    held = [{"question": q.get("id"), "title": q.get("title"), "holds": q.get("blocks")}
            for q in render.open_questions(analysis) if q.get("priority") == "P0"]
    return {"version": version, "held": held, "steps": steps}

"""The table SQL file: statements in the order they run, one file per database.

Six sections: 1 new tables, 2 changes to existing tables, 3 initial rows of
new tables, 4 changes to existing rows, 5 catch-up statements for
environments that ran an earlier version, 6 rollback (inside a comment).

Section 5 comes from the `applied` records in state.json ({"test": {"v": 3}}):
an environment that ran version N gets what changed after N. A table that is
new since N gets its full statement; a table that existed gets the patches
appended since N. That is why `sql` must be the full latest statement and
`patches` only ever grow (references/analysis.md, backend.tables).
"""

from __future__ import annotations

import json
from typing import Any, Callable

from .output import issue

DEFAULT_DB = ""


def _dump(x: Any) -> str:
    return json.dumps(x, ensure_ascii=False, sort_keys=True)


def _norm(sql: Any) -> str:
    return " ".join(str(sql or "").split()).rstrip(";").rstrip()


def statement(sql: Any) -> str:
    """One statement, ending in exactly one semicolon."""
    return str(sql or "").strip().rstrip(";").rstrip() + ";"


def _one_line(text: Any) -> str:
    return " ".join(str(text or "").split())


def _db(x: dict[str, Any]) -> str:
    return str(x.get("db") or DEFAULT_DB)


def _live(items: Any) -> list[dict[str, Any]]:
    return [x for x in items or [] if isinstance(x, dict) and not x.get("removed")]


def databases(analysis: dict[str, Any]) -> list[str]:
    """Databases with something to run, in the order they first appear."""
    be = analysis.get("backend") or {}
    out: list[str] = []
    for x in _live(be.get("tables")) + [d for d in be.get("data") or [] if isinstance(d, dict)]:
        if _db(x) not in out:
            out.append(_db(x))
    return out


def file_names(analysis: dict[str, Any], base: str) -> dict[str, str]:
    """`base` (3.建表.sql) for one database; with several, the others carry their name."""
    dbs = databases(analysis)
    if len(dbs) <= 1:
        return {db: base for db in dbs}
    stem, dot, ext = base.rpartition(".")
    return {db: base if db == DEFAULT_DB else "%s-%s%s%s" % (stem, db, dot, ext) for db in dbs}


def catch_up(old: dict[str, Any], new: dict[str, Any], db: str) -> dict[str, Any]:
    """What an environment that ran version `old` needs to reach `new`, in one database.

    tables:  [(table, "whole" | "patch", [statements])]
    data:    data changes added since `old`
    gone:    tables `old` had that `new` no longer has (never dropped for you)
    missing: tables whose `sql` changed with no new patch: the environment
             cannot catch up, so this is an error (see `problems`)
    edited:  data changes from `old` that are no longer there word for word
    """
    ob, nb = old.get("backend") or {}, new.get("backend") or {}
    before = {t.get("name"): t for t in _live(ob.get("tables")) if _db(t) == db}
    now = [t for t in _live(nb.get("tables")) if _db(t) == db]
    tables, missing = [], []
    for t in now:
        o = before.get(t.get("name"))
        if o is None:
            tables.append((t, "whole", [t.get("sql")] + list(t.get("init") or [])))
            continue
        patches = list(t.get("patches") or [])[len(o.get("patches") or []):]
        init = list(t.get("init") or [])[len(o.get("init") or []):]
        if patches or init:
            tables.append((t, "patch", patches + init))
        if _norm(t.get("sql")) != _norm(o.get("sql")) and not patches:
            missing.append(t.get("name"))
    names = {t.get("name") for t in now}
    gone = [o for name, o in before.items() if name not in names]
    old_data = [d for d in ob.get("data") or [] if isinstance(d, dict) and _db(d) == db]
    new_data = [d for d in nb.get("data") or [] if isinstance(d, dict) and _db(d) == db]
    seen = {_dump(d) for d in old_data}
    kept = {_dump(d) for d in new_data}
    return {
        "tables": tables,
        "data": [d for d in new_data if _dump(d) not in seen],
        "gone": gone,
        "missing": missing,
        "edited": [d for d in old_data if _dump(d) not in kept],
    }


def env_rows(state: dict[str, Any], envs: list[str]) -> list[tuple[str, int | None]]:
    """Every environment with the version it ran (None: no record), settings order first."""
    applied = state.get("applied") or {}
    names = list(envs) + [e for e in applied if e not in envs]
    return [(e, (applied.get(e) or {}).get("v")) for e in names]


def problems(analysis: dict[str, Any], state: dict[str, Any],
             load_version: Callable[[int], dict[str, Any]]) -> list[dict[str, str]]:
    """Issues that would leave an environment that already ran the SQL behind."""
    out = []
    by_version: dict[int, list[str]] = {}
    for env, v in env_rows(state, []):
        if v is not None:
            by_version.setdefault(v, []).append(env)
    for v in sorted(by_version):
        old = load_version(v)
        envs = ", ".join(by_version[v])
        for db in databases(analysis) or [DEFAULT_DB]:
            c = catch_up(old, analysis, db)
            for name in c["missing"]:
                out.append(issue(
                    "sql.patch-missing", "error",
                    "Table %s changed since version %d, which %s ran, but no patch was added." % (name, v, envs),
                    hint="Keep `sql` as the full latest statement and append to `patches` the statement that "
                    "turns the version-%d table into the current one. Never edit or remove an existing patch." % v,
                    where="backend.tables[%s].patches" % name))
            for d in c["edited"]:
                out.append(issue(
                    "sql.data-edited", "warn",
                    "A data change on %s that %s already ran (version %d) was edited or removed." % (
                        d.get("table"), envs, v),
                    hint="%s will get the edited statement as a new one. If that would apply it twice, keep the "
                    "old entry as it was and add a new entry for the difference." % envs,
                    where="backend.data[%s]" % d.get("table")))
    return out


def build(
    analysis: dict[str, Any],
    db: str,
    version: int,
    generated: str,
    req_id: str,
    state: dict[str, Any],
    envs: list[str],
    load_version: Callable[[int], dict[str, Any]],
    texts: dict[str, Any],
) -> str:
    """The SQL file for one database."""
    t = texts["sql"]

    def tx(key: str, **values: Any) -> str:
        text = t[key]
        for k, v in values.items():
            text = text.replace("{%s}" % k, str(v))
        return text

    be = analysis.get("backend") or {}
    tables = [x for x in _live(be.get("tables")) if _db(x) == db]
    new_tables = [x for x in tables if x.get("kind") == "new"]
    alter_tables = [x for x in tables if x.get("kind") == "alter"]
    data = [d for d in be.get("data") or [] if isinstance(d, dict) and _db(d) == db]
    title = (analysis.get("meta") or {}).get("title", "")
    lines: list[str] = []

    def comment(text: str) -> None:
        lines.append("-- " + text if text else "--")

    def blank(n: int = 1) -> None:
        lines.extend([""] * n)

    def head(text: str) -> None:
        blank(2)
        comment("-" * 61)
        comment(text)
        comment("-" * 61)
        blank()

    def table_label(x: dict[str, Any]) -> str:
        return tx("table_line", name=x.get("name"), title=_one_line(x.get("title")))

    def data_label(d: dict[str, Any], note: str = "") -> str:
        return tx("data_line", table=d.get("table"), kind=t["d_" + str(d.get("kind"))] + note,
                  does=_one_line(d.get("does")))

    def data_block(d: dict[str, Any], note: str = "") -> None:
        comment(data_label(d, note))
        lines.append(statement(d.get("sql")))
        if d.get("check"):
            comment(t["check"])
            comment("  " + statement(d.get("check")))

    # Header: what each environment runs.
    comment(tx("title", title=title, v=version))
    comment(tx("sub", id=req_id, generated=generated, db=db or t["db_default"]))
    comment("")
    comment(t["envs_h"])
    rows = env_rows(state, envs)
    width = max([len(e) for e, _ in rows] + [0])
    unknown = False
    groups: dict[int, list[str]] = {}
    catch: dict[int, dict[str, Any]] = {}
    for env, v in rows:
        name = env.ljust(width)
        if v is None:
            unknown = True
            comment("  " + tx("env_none", env=name))
        elif v >= version:
            comment("  " + tx("env_done", env=name, n=v))
        else:
            if v not in catch:
                catch[v] = catch_up(load_version(v), analysis, db)
            c = catch[v]
            if c["tables"] or c["data"] or c["gone"]:
                groups.setdefault(v, []).append(env)
                comment("  " + tx("env_at", env=name, n=v, v=version))
            else:
                comment("  " + tx("env_same", env=name, n=v))
    if unknown and version > 1:
        comment(t["env_none_note"])
    comment(tx("after_run", v=version))
    comment(t["rollback_note"])

    # 1 new tables, 2 changes to existing tables.
    for key, items in (("s1", new_tables), ("s2", alter_tables)):
        head(t[key])
        if not items:
            comment(t["none"])
        for i, x in enumerate(items):
            if i:
                blank()
            comment(table_label(x) + tx("colon_does", does=_one_line(x.get("does"))))
            lines.append(statement(x.get("sql")))

    # 3 initial rows of new tables.
    head(t["s3"])
    with_init = [x for x in new_tables if x.get("init")]
    if not with_init:
        comment(t["none"])
    for i, x in enumerate(with_init):
        if i:
            blank()
        comment(table_label(x))
        lines.extend(statement(s) for s in x["init"])

    # 4 changes to existing rows.
    head(t["s4"])
    if not data:
        comment(t["none"])
    for i, d in enumerate(data):
        if i:
            blank()
        data_block(d)

    # 5 catch-up statements, one group per version some environment ran.
    head(t["s5"])
    if not groups:
        comment(t["s5_none"])
    for gi, v in enumerate(sorted(groups)):
        if gi:
            blank()
        c = catch[v]
        comment(tx("group", n=v, v=version, envs=t["sep"].join(groups[v])))
        for x, how, stmts in c["tables"]:
            blank()
            comment(table_label(x) + tx("since_whole" if how == "whole" else "since_patch", n=v))
            lines.extend(statement(s) for s in stmts)
        for d in c["data"]:
            blank()
            data_block(d, t["same_as_s4"])
        for o in c["gone"]:
            blank()
            comment(tx("gone", name=o.get("name"), title=_one_line(o.get("title")), n=v))

    # 6 rollback, newest change first: data, then altered tables, then new tables.
    head(t["s6"])
    steps: list[tuple[str, list[str]]] = []
    for d in reversed(data):
        label = tx("rb_data", kind=t["d_" + str(d.get("kind"))], table=d.get("table"))
        steps.append((label, [statement(d["rollback"])] if d.get("rollback") else []))
    for x in reversed(alter_tables):
        steps.append((tx("rb_alter", name=x.get("name")), [statement(x["rollback"])] if x.get("rollback") else []))
    for x in reversed(new_tables):
        steps.append((tx("rb_drop", name=x.get("name")), ["DROP TABLE IF EXISTS %s;" % x.get("name")]))
    if not steps:
        comment(t["none"])
    else:
        comment(t["rb_how"])
        comment(t["rb_order"])
        body: list[str] = []
        for i, (label, stmts) in enumerate(steps, 1):
            if i > 1:
                body.append("")
            body.append("-- %d. %s" % (i, label))
            body.extend(stmts or ["-- " + t["rb_manual"]])
        if any("*/" in line for line in body):  # a block comment cannot hold */: comment line by line
            lines.extend(("-- " + line if line and not line.startswith("--") else line) for line in body)
        else:
            lines.append("/*")
            lines.extend(body)
            lines.append("*/")
    return "\n".join(lines) + "\n"

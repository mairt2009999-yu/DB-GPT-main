"""Step 3 of RLSAwareSQLExecutor: inject RLS predicates into the SQL AST."""
from __future__ import annotations

import sqlglot
import sqlglot.expressions as exp

from dbgpt_app.security.rls_client import RLSRule, RLSTableRef
from dbgpt_app.security.exceptions import RLSSQLParseError


def inject(
    tree: exp.Expression,
    refs: list[RLSTableRef],
    rules: list[RLSRule],
    dialect: str,
) -> tuple[str, dict[str, str]]:
    """
    Inject per-table RLS predicates into the AST.
    Returns (rewritten_sql, snapshot).
    LEFT JOIN right-table predicates go into ON; all others go into WHERE.
    """
    snapshot: dict[str, str] = {}
    left_join_aliases = _collect_left_join_right_aliases(tree)

    for ref, rule in zip(refs, rules):
        if not rule.predicate:
            continue
        snapshot[ref.table] = rule.predicate
        pred_expr = sqlglot.parse_one(rule.predicate, dialect=dialect)
        if ref.alias.lower() in left_join_aliases:
            _inject_into_on(tree, ref.alias, pred_expr)
        else:
            _inject_into_where(tree, pred_expr)

    rewritten = tree.sql(dialect=dialect)
    try:
        sqlglot.parse_one(rewritten, dialect=dialect)
    except Exception as e:
        raise RLSSQLParseError(f"Post-rewrite validation failed: {e}") from e

    return rewritten, snapshot


def _collect_left_join_right_aliases(tree: exp.Expression) -> set[str]:
    """Return aliases of tables on the right side of a LEFT JOIN."""
    aliases: set[str] = set()
    for join in tree.find_all(exp.Join):
        side = getattr(join, "side", None)
        if side and side.upper() in ("LEFT", "LEFT OUTER"):
            tbl = join.this
            if isinstance(tbl, exp.Table):
                alias = tbl.alias or tbl.name
                aliases.add(alias.lower())
    return aliases


def _inject_into_where(tree: exp.Expression, pred_expr: exp.Expression) -> None:
    """AND pred_expr into the WHERE clause of the outermost SELECT."""
    select = tree if isinstance(tree, exp.Select) else tree.find(exp.Select)
    if select is None:
        return
    existing_where = select.args.get("where")
    if existing_where:
        new_where = exp.Where(this=exp.And(
            this=existing_where.this,
            expression=pred_expr,
        ))
    else:
        new_where = exp.Where(this=pred_expr)
    select.set("where", new_where)


def _inject_into_on(tree: exp.Expression, alias: str, pred_expr: exp.Expression) -> None:
    """AND pred_expr into the ON clause of the LEFT JOIN matching alias."""
    for join in tree.find_all(exp.Join):
        side = getattr(join, "side", None)
        if not (side and side.upper() in ("LEFT", "LEFT OUTER")):
            continue
        tbl = join.this
        if not isinstance(tbl, exp.Table):
            continue
        tbl_alias = (tbl.alias or tbl.name).lower()
        if tbl_alias != alias.lower():
            continue
        existing_on = join.args.get("on")
        if existing_on:
            new_on = exp.And(this=existing_on, expression=pred_expr)
        else:
            new_on = pred_expr
        join.set("on", new_on)
        return

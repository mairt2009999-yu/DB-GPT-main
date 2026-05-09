"""Step 3 of RLSAwareSQLExecutor: inject RLS predicates into the SQL AST."""

from __future__ import annotations

import logging

import sqlglot
import sqlglot.expressions as exp

from dbgpt_app.security.exceptions import RLSSQLParseError
from dbgpt_app.security.rls_client import RLSRule, RLSTableRef

logger = logging.getLogger(__name__)
RLS_LOG_PREFIX = ">>>>>>>>>>> [SQL拦截/RLS]"


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

    for ref, rule in zip(refs, rules):
        if not rule.predicate:
            continue
        pred_expr = _parse_predicate(rule, dialect)
        if not _predicate_applies_to_ref_columns(pred_expr, ref):
            logger.warning(
                "%s 跳过不适用于目标表的RLS谓词 | table=%s alias=%s "
                "columns=%s predicate=%s",
                RLS_LOG_PREFIX,
                ref.table,
                ref.alias,
                list(ref.columns),
                rule.predicate,
            )
            continue
        _qualify_predicate_columns(pred_expr, ref)
        snapshot[ref.table] = rule.predicate
        table_node = _find_table_node(tree, ref)
        if table_node is None:
            raise RLSSQLParseError(f"Table not found while injecting RLS: {ref.table}")
        join_node = _find_parent_join(table_node)
        if join_node is not None and _is_left_join(join_node):
            _inject_into_join_on(join_node, pred_expr)
        else:
            select = _find_parent_select(table_node)
            if select is None:
                raise RLSSQLParseError(
                    f"SELECT not found while injecting RLS: {ref.table}"
                )
            _inject_into_where(select, pred_expr)

    rewritten = tree.sql(dialect=dialect)
    try:
        sqlglot.parse_one(rewritten, dialect=dialect)
    except Exception as e:
        raise RLSSQLParseError(f"Post-rewrite validation failed: {e}") from e

    return rewritten, snapshot


def _parse_predicate(rule: RLSRule, target_dialect: str) -> exp.Expression:
    predicate_dialect = (rule.predicate_dialect or "").lower()
    if not predicate_dialect or predicate_dialect == "ansi":
        predicate_dialect = target_dialect
    try:
        predicate = sqlglot.parse_one(rule.predicate, dialect=predicate_dialect)
    except Exception as exc:
        raise RLSSQLParseError(
            "RLS predicate parse failed: "
            f"table={rule.table} dialect={predicate_dialect} "
            f"targetDialect={target_dialect} err={exc}"
        ) from exc
    if predicate_dialect == target_dialect:
        _normalize_legacy_quoted_string_values(predicate)
    return predicate


def _predicate_applies_to_ref_columns(
    predicate: exp.Expression, ref: RLSTableRef
) -> bool:
    if not ref.columns:
        return True

    referenced_columns = _predicate_column_names(predicate)
    if not referenced_columns:
        return True

    table_columns = {column.lower() for column in ref.columns}
    return referenced_columns.issubset(table_columns)


def _predicate_column_names(predicate: exp.Expression) -> set[str]:
    names: set[str] = set()
    for column in predicate.find_all(exp.Column):
        if _is_predicate_value_position(column):
            continue
        if column.name:
            names.add(column.name.lower())
    return names


def _qualify_predicate_columns(predicate: exp.Expression, ref: RLSTableRef) -> None:
    table_alias = ref.alias or ref.table
    if not table_alias:
        return
    for column in predicate.find_all(exp.Column):
        if _is_predicate_value_position(column):
            continue
        if column.table or column.db or column.catalog:
            continue
        column.set("table", exp.to_identifier(table_alias))


def _normalize_legacy_quoted_string_values(predicate: exp.Expression) -> None:
    """Convert legacy double-quoted predicate values to SQL string literals."""
    for column in list(predicate.find_all(exp.Column)):
        if not _is_unqualified_quoted_column(column):
            continue
        if _is_predicate_value_position(column):
            column.replace(exp.Literal.string(column.name))


def _is_unqualified_quoted_column(column: exp.Column) -> bool:
    identifier = column.this
    return (
        isinstance(identifier, exp.Identifier)
        and bool(identifier.args.get("quoted"))
        and not column.table
        and not column.db
        and not column.catalog
    )


def _is_predicate_value_position(node: exp.Expression) -> bool:
    parent = node.parent
    return bool(
        isinstance(parent, exp.Predicate)
        and not isinstance(parent, exp.SubqueryPredicate)
        and node.arg_key in {"expression", "expressions", "low", "high"}
    )


def _find_table_node(tree: exp.Expression, ref: RLSTableRef) -> exp.Table | None:
    for table in tree.find_all(exp.Table):
        name = table.name
        alias = table.alias or name
        schema = table.db or ""
        if (
            name.lower() == ref.table.lower()
            and alias.lower() == ref.alias.lower()
            and _schema_matches(schema, ref.schema or "")
        ):
            return table
    return None


def _schema_matches(table_schema: str, ref_schema: str) -> bool:
    if not table_schema:
        return True
    return table_schema.lower() == ref_schema.lower()


def _find_parent_join(node: exp.Expression) -> exp.Join | None:
    parent = node.parent
    return parent if isinstance(parent, exp.Join) else None


def _find_parent_select(node: exp.Expression) -> exp.Select | None:
    parent = node.parent
    while parent is not None:
        if isinstance(parent, exp.Select):
            return parent
        parent = parent.parent
    return None


def _is_left_join(join: exp.Join) -> bool:
    side = getattr(join, "side", None)
    return bool(side and side.upper() in ("LEFT", "LEFT OUTER"))


def _inject_into_where(select: exp.Select, pred_expr: exp.Expression) -> None:
    """AND pred_expr into the WHERE clause of the owning SELECT."""
    existing_where = select.args.get("where")
    if existing_where:
        new_where = exp.Where(
            this=exp.And(
                this=existing_where.this,
                expression=pred_expr,
            )
        )
    else:
        new_where = exp.Where(this=pred_expr)
    select.set("where", new_where)


def _inject_into_join_on(join: exp.Join, pred_expr: exp.Expression) -> None:
    """AND pred_expr into the ON clause of a LEFT JOIN."""
    existing_on = join.args.get("on")
    if existing_on:
        new_on = exp.And(this=existing_on, expression=pred_expr)
    else:
        new_on = pred_expr
    join.set("on", new_on)

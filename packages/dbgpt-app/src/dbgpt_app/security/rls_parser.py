"""rls_parser.py —— RLSAwareSQLExecutor 的 Step 1：解析 SQL 并收集表清单。

将 LLM 生成的 SQL 字符串解析为 sqlglot AST，并把其中所有真实表
（排除 CTE 名）收集为 ``RLSTableRef`` 列表，供后续
``rls_client.batch_fetch`` 与 ``rls_injector.inject`` 使用。

注意
----
``RLSTableRef`` 的权威定义在 ``rls_client.py``，这里直接 import，不重复定义。
"""

from __future__ import annotations

from typing import List, Set, Tuple

import sqlglot
import sqlglot.expressions as exp

from dbgpt_app.security.exceptions import RLSSQLParseError, RLSUnsupportedSQLError
from dbgpt_app.security.rls_client import RLSTableRef

# v1 仅支持这三种方言；其他方言一律 fail-close
_SUPPORTED_DIALECTS = {"mysql", "postgres", "sqlite"}


def is_supported_dialect(dialect: str) -> bool:
    """判断给定方言名称是否在 v1 支持范围内。"""
    return (dialect or "").lower() in _SUPPORTED_DIALECTS


def _is_read_only_query_expression(tree: exp.Expression) -> bool:
    """Return True for SELECT trees and set operations composed only of SELECTs."""
    if isinstance(tree, exp.Select):
        return True
    if isinstance(tree, (exp.Union, exp.Intersect, exp.Except)):
        left = tree.args.get("this")
        right = tree.args.get("expression")
        return (
            isinstance(left, exp.Expression)
            and isinstance(right, exp.Expression)
            and _is_read_only_query_expression(left)
            and _is_read_only_query_expression(right)
        )
    return False


def parse_and_collect(
    sql: str,
    dialect: str,
    datasource: str = "",
    default_schema: str = "",
) -> Tuple[exp.Expression, List[RLSTableRef]]:
    """解析 SQL 并返回 ``(AST, table refs)``。

    Args:
        sql:           原始 SQL 字符串
        dialect:       SQL 方言名称（mysql / postgres / sqlite）
        datasource:    DB-GPT 数据源名称，写入每个 RLSTableRef.datasource
        default_schema: 缺省 schema 名（无 schema 前缀时使用）

    Returns:
        - tree: sqlglot AST 表达式
        - refs: ``RLSTableRef`` 列表，已经做了：
            - 排除 CTE 名（``WITH t AS ...`` 里的 t 不算真表）
            - 保留自连接的多个 alias
            - 每个 ref 有 alias（无 alias 时填表名）

    Raises:
        RLSUnsupportedSQLError: 非 SELECT 语句、不支持的方言
        RLSSQLParseError: sqlglot 解析失败
    """
    if not is_supported_dialect(dialect):
        raise RLSUnsupportedSQLError(f"Dialect '{dialect}' is not supported in v1")

    try:
        tree = sqlglot.parse_one(sql, dialect=dialect)
    except Exception as exc:  # pragma: no cover - sqlglot raises various types
        raise RLSSQLParseError(f"sqlglot parse failed: {exc}") from exc

    if tree is None or not _is_read_only_query_expression(tree):
        raise RLSUnsupportedSQLError(
            "Only read-only SELECT query expressions are supported in v1"
        )

    # 1. 收集 CTE 名（排除）
    cte_names: Set[str] = set()
    for cte in tree.find_all(exp.CTE):
        alias_name = cte.alias_or_name
        if alias_name:
            cte_names.add(alias_name.lower())

    # 2. 遍历所有 Table 节点，按 (table, schema, alias) 三元组去重
    seen: Set[Tuple[str, str, str]] = set()
    refs: List[RLSTableRef] = []
    for table_node in tree.find_all(exp.Table):
        name = table_node.name
        if not name:
            continue
        if name.lower() in cte_names:
            # CTE 名不视为真表
            continue
        schema = table_node.db or default_schema or ""
        alias = table_node.alias or name
        key = (name.lower(), schema.lower(), alias.lower())
        if key in seen:
            continue
        seen.add(key)
        refs.append(
            RLSTableRef(
                datasource=datasource,
                schema=schema,
                table=name,
                alias=alias,
            )
        )

    return tree, refs

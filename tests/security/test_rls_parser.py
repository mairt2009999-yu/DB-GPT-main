"""Tests for dbgpt_app.security.rls_parser."""

from __future__ import annotations

import pytest

from dbgpt_app.security.exceptions import RLSSQLParseError, RLSUnsupportedSQLError
from dbgpt_app.security.rls_parser import is_supported_dialect, parse_and_collect


def test_simple_select_mysql():
    _, refs = parse_and_collect("SELECT id FROM orders", "mysql", datasource="ds1")
    assert len(refs) == 1
    assert refs[0].table == "orders"
    assert refs[0].datasource == "ds1"


def test_inner_join_collects_both_tables():
    _, refs = parse_and_collect(
        "SELECT o.id FROM orders o JOIN customers c ON o.cid = c.id",
        "mysql",
        datasource="ds1",
    )
    tables = {r.table for r in refs}
    assert tables == {"orders", "customers"}


def test_left_join_collects_right_table():
    _, refs = parse_and_collect(
        "SELECT o.id FROM orders o LEFT JOIN items i ON o.id = i.oid",
        "mysql",
        datasource="ds1",
    )
    tables = {r.table for r in refs}
    assert tables == {"orders", "items"}


def test_subquery_collects_inner_table():
    _, refs = parse_and_collect(
        "SELECT * FROM (SELECT id FROM orders) sub",
        "sqlite",
        datasource="ds1",
    )
    tables = {r.table for r in refs}
    assert "orders" in tables


def test_cte_inner_table_collected_not_cte_name():
    sql = "WITH recent AS (SELECT id FROM orders) SELECT id FROM recent"
    _, refs = parse_and_collect(sql, "mysql", datasource="ds1")
    tables = {r.table for r in refs}
    # "recent" is a CTE name, not a real table
    assert "orders" in tables
    assert "recent" not in tables


def test_self_join_two_aliases():
    sql = "SELECT a.id, b.id FROM orders a JOIN orders b ON a.id = b.parent_id"
    _, refs = parse_and_collect(sql, "mysql", datasource="ds1")
    order_refs = [r for r in refs if r.table == "orders"]
    assert len(order_refs) == 2
    aliases = {r.alias for r in order_refs}
    assert aliases == {"a", "b"}


def test_non_select_raises():
    with pytest.raises(RLSUnsupportedSQLError):
        parse_and_collect("INSERT INTO orders VALUES (1)", "mysql", datasource="ds1")


def test_unsupported_dialect_raises():
    with pytest.raises(RLSUnsupportedSQLError):
        parse_and_collect("SELECT 1", "clickhouse", datasource="ds1")


def test_parse_failure_raises():
    with pytest.raises(RLSSQLParseError):
        parse_and_collect("SELECT FROM WHERE", "mysql", datasource="ds1")


def test_is_supported_dialect():
    assert is_supported_dialect("mysql")
    assert is_supported_dialect("postgres")
    assert is_supported_dialect("sqlite")
    assert is_supported_dialect("MYSQL")
    assert not is_supported_dialect("clickhouse")
    assert not is_supported_dialect("oracle")


def test_postgres_schema_prefix():
    _, refs = parse_and_collect(
        "SELECT id FROM sales.orders",
        "postgres",
        datasource="ds1",
    )
    assert refs[0].table == "orders"
    assert refs[0].schema == "sales"


def test_alias_defaults_to_table_name_when_absent():
    _, refs = parse_and_collect("SELECT id FROM orders", "mysql", datasource="ds")
    assert refs[0].alias == "orders"


def test_table_with_explicit_alias():
    _, refs = parse_and_collect("SELECT id FROM orders AS o", "mysql", datasource="ds")
    assert refs[0].alias == "o"


def test_default_schema_used_when_no_db_in_table():
    _, refs = parse_and_collect(
        "SELECT id FROM orders", "mysql", datasource="ds", default_schema="sales"
    )
    assert refs[0].schema == "sales"
